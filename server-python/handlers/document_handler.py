import os
import shutil
import logging
import uuid
import jwt
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, BackgroundTasks, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO
import asyncio

from database import get_db_connection
from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import encrypt_data, decrypt_data
from core.security_scan import validate_magic_bytes, scan_malicious_content
from utils import background_ingestion, get_user_limits
from schemas import URLRequest, ConnectorRequest
from handlers.document_processor import async_background_ingestion
from handlers.websocket_handlers import upload_status_manager

logger = logging.getLogger(__name__)

CHUNKS_TEMP_DIR = Path("temp_uploads") / "chunks"
CHUNKS_TEMP_DIR.mkdir(parents=True, exist_ok=True)

async def handle_initiate_upload(agent_id: str, file_size_bytes: int):
    """
    What it does: Starts the process of uploading a new document. It checks if the agent exists and if the user has enough storage space on their plan.
    Args:
        agent_id (str): The ID of the agent receiving the file.
        file_size_bytes (int): The size of the file being uploaded in bytes.
    Returns: A dictionary with a new unique upload_id and the recommended chunk size.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM agents WHERE id = %s", (agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")
        user_id = agent_row[0]

        # Enforce storage limits
        limits = get_user_limits(user_id, cursor)
        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        # Check total storage limit
        if current_storage + file_size_bytes > (limits["storage_mb"] * 1024 * 1024):
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        # Enforce max upload file size (50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024
        if file_size_bytes > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds the maximum limit of 50MB.",
            )

        upload_id = str(uuid.uuid4())
        upload_dir = CHUNKS_TEMP_DIR / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        return {
            "upload_id": upload_id,
            "chunk_size_bytes": 5 * 1024 * 1024,  # Standard 5MB chunk recommendation
        }
    finally:
        cursor.close()
        conn.close()


async def handle_upload_chunk(upload_id: str, chunk_index: int, chunk: UploadFile):
    """
    What it does: Saves a piece (chunk) of a large file being uploaded. This helps in uploading large files without timing out.
    Args:
        upload_id (str): The unique ID of the ongoing upload session.
        chunk_index (int): The number sequence of this piece.
        chunk (UploadFile): The actual file data piece.
    Returns: A success message.
    """
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="Upload session not found")

    chunk_path = upload_dir / f"chunk_{chunk_index}"
    try:
        def save_file():
            with open(chunk_path, "wb") as buffer:
                shutil.copyfileobj(chunk.file, buffer)
        await asyncio.to_thread(save_file)
        return {"message": f"Chunk {chunk_index} uploaded successfully."}
    except Exception as e:
        logger.exception("Failed to save chunk")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_complete_upload(upload_id: str, agent_id: str, filename: str, background_tasks: BackgroundTasks):
    """
    What it does: Joins all the uploaded pieces together, checks the file for viruses, encrypts it for safety, and starts processing it in the background.
    Args:
        upload_id (str): The unique ID of the ongoing upload session.
        agent_id (str): The ID of the agent receiving the file.
        filename (str): The original name of the uploaded file.
        background_tasks (BackgroundTasks): FastAPIs background task runner.
    Returns: A message confirming the file is verified and processing has started.
    """
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    if not upload_dir.exists():
        logger.warning(f"Upload session dir {upload_dir} does not exist.")
        raise HTTPException(status_code=404, detail="Upload session not found or already completed")

    # Sort chunks by index
    chunk_files = sorted(
        [f for f in upload_dir.iterdir() if f.name.startswith("chunk_")],
        key=lambda x: int(x.name.split("_")[1])
    )

    if not chunk_files:
        logger.warning(f"No chunk files found in {upload_dir}.")
        raise HTTPException(status_code=400, detail="No chunks found for this upload session")

    # Merge chunks in memory
    file_bytes = b""
    for chunk_file in chunk_files:
        with open(chunk_file, "rb") as f:
            file_bytes += f.read()

    # Clean up chunks
    shutil.rmtree(upload_dir)

    # 1. Magic bytes validation
    is_valid_magic, magic_err = validate_magic_bytes(file_bytes, filename)
    if not is_valid_magic:
        logger.warning(f"Magic bytes verification failed for {filename}: {magic_err}")
        raise HTTPException(status_code=400, detail=magic_err)

    # 2. Security scan
    is_secure, scan_err = scan_malicious_content(file_bytes, filename)
    if not is_secure:
        logger.warning(f"Security scan failed for {filename}: {scan_err}")
        raise HTTPException(status_code=400, detail=scan_err)

    safe_filename = os.path.basename(filename)
    file_path = UPLOAD_DIR / safe_filename
    temp_path = str(file_path) + ".tmp"
    
    # Write temp unencrypted file for ingestion
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Encrypt and save file permanently
    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch Agent Configuration
        cursor.execute(
            "SELECT user_id, embedding_model, chunk_strategy, workspace_id FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            if os.path.exists(temp_path): os.remove(temp_path)
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"
        workspace_id = agent_row[3]

        # Check plan storage limits
        file_size = len(file_bytes)
        limits = get_user_limits(user_id, cursor)
        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            if os.path.exists(temp_path): os.remove(temp_path)
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        # Insert pending document row
        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (agent_id, safe_filename, file_size),
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        # Broadcast start status
        await upload_status_manager.send_status(agent_id, "processing", safe_filename, "Starting background document ingestion...", 0.1)

        # Ingest in background asynchronously
        asyncio.create_task(
            async_background_ingestion(
                document_id=document_id,
                agent_id=agent_id,
                filename=safe_filename,
                temp_path=temp_path,
                strategy=strategy,
                embed_model=embed_model,
                workspace_id=str(workspace_id),
                file_path=str(file_path),
            )
        )

        return {"message": "File uploaded and verified successfully. Ingestion scheduled in background."}
    except Exception as exc:
        logger.exception("Failed to process complete upload")
        if conn: conn.rollback()
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


async def handle_view_document(doc_id: str, jwt_token: str):
    """
    What it does: Decrypts a stored file on the fly and sends it directly to the user's browser so they can view it.
    Args:
        doc_id (str): The ID of the document to view.
        jwt_token (str): The security token verifying the user's access.
    Returns: A stream of the file content in the correct format (like PDF or Image).
    """
    from core.auth import JWT_SECRET, ALGORITHM
    try:
        jwt.decode(jwt_token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT filename FROM documents WHERE id = %s", (doc_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        filename = doc_row[0]
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Encrypted file not found on disk")

        # Decrypt content on the fly
        with open(file_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = decrypt_data(encrypted_data)

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        media_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "csv": "text/csv",
            "txt": "text/plain",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        media_type = media_types.get(ext, "application/octet-stream")

        return StreamingResponse(
            BytesIO(decrypted_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )
    finally:
        cursor.close()
        conn.close()


async def handle_process_file(agent_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    """
    What it does: Processes a single file upload directly (without chunks), validates it, encrypts it, and starts ingestion.
    Args:
        agent_id (str): The agent ID receiving the file.
        file (UploadFile): The file being uploaded.
        background_tasks (BackgroundTasks): FastAPIs background task runner.
    Returns: A success message that it is processing.
    """
    allowed_exts = {"pdf", "txt", "docx", "csv", "png", "jpg", "jpeg"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Basic file extension validation
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.",
        )

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename

    file_bytes = file.file.read()
    
    temp_path = str(file_path) + ".tmp"
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        limits = get_user_limits(user_id, cursor)
        file_size = os.path.getsize(file_path)

        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            os.remove(file_path)
            os.remove(temp_path)
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, safe_filename)

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (agent_id, safe_filename, file_size),
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(
            background_ingestion,
            document_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {
            "message": f"{ext.upper()} uploaded successfully! Processing in background..."
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process uploaded file")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


async def handle_process_url(agent_id: str, url: str, background_tasks: BackgroundTasks):
    """
    What it does: Downloads the text from a given web address (URL) and saves it as a document.
    Args:
        agent_id (str): The agent ID connecting to the URL.
        url (str): The web link to read from.
        background_tasks (BackgroundTasks): FastAPIs background task runner.
    Returns: A success message stating processing has begun.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        raw_text = rag_engine.extract_text_from_url(url)
        file_size = len(raw_text.encode("utf-8"))

        limits = get_user_limits(user_id, cursor)
        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (agent_id, url, file_size),
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(
            background_ingestion,
            document_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            None,
        )
        return {"message": "URL scraped. Processing in background..."}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process URL")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if conn: conn.close()


async def handle_process_connector(agent_id: str, connector_id: str):
    """
    What it does: Creates a mock connection to external apps (like Slack, Google Drive) and fakes a file upload for demonstration.
    Args:
        agent_id (str): The agent ID getting the connector.
        connector_id (str): The ID code of the tool (e.g. 'gdrive', 'slack').
    Returns: A success message for the connection.
    """
    await asyncio.sleep(1.5) 

    connector_names = {
        "gdrive": "Google Drive Sync",
        "notion": "Notion Workspace Sync",
        "slack": "Slack Channels Sync",
        "github": "GitHub Repository Sync"
    }
    display_name = connector_names.get(connector_id, f"{connector_id.capitalize()} Sync")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'completed', %s) RETURNING id;",
            (agent_id, display_name, 2048576) 
        )
        
        conn.commit()
        return {"message": f"Successfully connected to {display_name}."}
    except Exception as exc:
        logger.exception("Failed to process connector")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_documents(agent_id: str):
    """
    What it does: Retrieves a list of all documents an agent has learned from, including their status and size.
    Args:
        agent_id (str): The ID of the agent we want the documents for.
    Returns: A list containing details of each document.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT d.id, d.filename, d.status, d.created_at, d.file_size_bytes, COUNT(e.id) as chunk_count
            FROM documents d
            LEFT JOIN document_embeddings e ON d.id = e.document_id
            WHERE d.agent_id = %s 
            GROUP BY d.id
            ORDER BY d.created_at DESC
        """,
            (agent_id,),
        )
        docs = [
            {
                "id": r[0],
                "filename": r[1],
                "status": r[2],
                "created_at": r[3],
                "file_size_bytes": r[4] or 0,
                "chunk_count": r[5] or 0,
            }
            for r in cursor.fetchall()
        ]
        return {"documents": docs}
    finally:
        cursor.close()
        conn.close()


async def handle_delete_document(doc_id: str):
    """
    What it does: Permanently removes a document, its data, and its AI embeddings from the server and database.
    Args:
        doc_id (str): The unique ID of the document to erase.
    Returns: A message confirming deletion.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT filename FROM documents WHERE id = %s", (doc_id,))
        doc = cursor.fetchone()
        if doc and doc[0]:
            file_path = UPLOAD_DIR / doc[0]
            if os.path.exists(file_path):
                os.remove(file_path)

        cursor.execute("DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        return {"message": "Document and its memory completely deleted!"}
    finally:
        cursor.close()
        conn.close()
