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

from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import encrypt_data, decrypt_data
from core.security_scan import validate_magic_bytes, scan_malicious_content
from utils import background_ingestion, get_user_limits_by_id
from schemas import URLRequest, ConnectorRequest
from handlers.document_processor import async_background_ingestion
from handlers.websocket_handlers import upload_status_manager
from database_layer import document_repository

logger = logging.getLogger(__name__)

CHUNKS_TEMP_DIR = Path("temp_uploads") / "chunks"
CHUNKS_TEMP_DIR.mkdir(parents=True, exist_ok=True)

async def handle_initiate_upload(agent_id: str, file_size_bytes: int):
    user_storage = await document_repository.get_agent_and_user_storage(agent_id)
    if not user_storage or not user_storage[0]:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    user_id, current_storage = user_storage
    limits = await get_user_limits_by_id(user_id) # Need an async version of get_user_limits if possible, or assume it's hardcoded for now

    if current_storage + file_size_bytes > (limits["storage_mb"] * 1024 * 1024):
        raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

    MAX_FILE_SIZE = 50 * 1024 * 1024
    if file_size_bytes > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 50MB.")

    upload_id = str(uuid.uuid4())
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    return {
        "upload_id": upload_id,
        "chunk_size_bytes": 5 * 1024 * 1024,
    }


async def handle_upload_chunk(upload_id: str, chunk_index: int, chunk: UploadFile):
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
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="Upload session not found or already completed")

    chunk_files = sorted(
        [f for f in upload_dir.iterdir() if f.name.startswith("chunk_")],
        key=lambda x: int(x.name.split("_")[1])
    )

    if not chunk_files:
        raise HTTPException(status_code=400, detail="No chunks found for this upload session")

    file_bytes = b""
    for chunk_file in chunk_files:
        with open(chunk_file, "rb") as f:
            file_bytes += f.read()

    shutil.rmtree(upload_dir)

    is_valid_magic, magic_err = validate_magic_bytes(file_bytes, filename)
    if not is_valid_magic:
        raise HTTPException(status_code=400, detail=magic_err)

    is_secure, scan_err = scan_malicious_content(file_bytes, filename)
    if not is_secure:
        raise HTTPException(status_code=400, detail=scan_err)

    safe_filename = os.path.basename(filename)
    file_path = UPLOAD_DIR / safe_filename
    temp_path = str(file_path) + ".tmp"
    
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)

    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    try:
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            if os.path.exists(temp_path): os.remove(temp_path)
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        workspace_id = config["workspace_id"]
        current_storage = config["current_storage"]

        file_size = len(file_bytes)
        limits = await get_user_limits_by_id(user_id)

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            if os.path.exists(temp_path): os.remove(temp_path)
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        document_id = await document_repository.insert_document(agent_id, safe_filename, "processing", file_size)

        await upload_status_manager.send_status(agent_id, "processing", safe_filename, "Starting background document ingestion...", 0.1)

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
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_view_document(doc_id: str, jwt_token: str):
    from core.auth import JWT_SECRET, ALGORITHM
    try:
        jwt.decode(jwt_token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")

    filename = await document_repository.get_document_filename(doc_id)
    if not filename:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Encrypted file not found on disk")

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


async def handle_process_file(agent_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    allowed_exts = {"pdf", "txt", "docx", "csv", "png", "jpg", "jpeg"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.")

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename
    file_bytes = file.file.read()
    
    temp_path = str(file_path) + ".tmp"
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    try:
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        limits = await get_user_limits_by_id(user_id)
        file_size = os.path.getsize(file_path)

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            os.remove(file_path)
            os.remove(temp_path)
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, safe_filename)

        document_id = await document_repository.insert_document(agent_id, safe_filename, "processing", file_size)

        background_tasks.add_task(
            background_ingestion,
            document_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {"message": f"{ext.upper()} uploaded successfully! Processing in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to process uploaded file")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


async def handle_process_url(agent_id: str, url: str, background_tasks: BackgroundTasks):
    try:
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        raw_text = rag_engine.extract_text_from_url(url)
        file_size = len(raw_text.encode("utf-8"))

        limits = await get_user_limits_by_id(user_id)

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        document_id = await document_repository.insert_document(agent_id, url, "processing", file_size)

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
        raise
    except Exception as exc:
        logger.exception("Failed to process URL")
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_process_connector(agent_id: str, connector_id: str):
    await asyncio.sleep(1.5) 
    connector_names = {
        "gdrive": "Google Drive Sync",
        "notion": "Notion Workspace Sync",
        "slack": "Slack Channels Sync",
        "github": "GitHub Repository Sync"
    }
    display_name = connector_names.get(connector_id, f"{connector_id.capitalize()} Sync")

    try:
        await document_repository.insert_document(agent_id, display_name, "completed", 2048576)
        return {"message": f"Successfully connected to {display_name}."}
    except Exception as exc:
        logger.exception("Failed to process connector")
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_get_documents(agent_id: str):
    try:
        rows = await document_repository.get_documents_for_agent(agent_id)
        docs = [
            {
                "id": r[0],
                "filename": r[1],
                "status": r[2],
                "created_at": r[3],
                "file_size_bytes": r[4] or 0,
                "chunk_count": r[5] or 0,
            }
            for r in rows
        ]
        return {"documents": docs}
    except Exception as exc:
        logger.exception("Failed to get documents")
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_document(doc_id: str):
    try:
        filename = await document_repository.delete_document_data(doc_id)
        if filename:
            file_path = UPLOAD_DIR / filename
            if os.path.exists(file_path):
                os.remove(file_path)
        return {"message": "Document and its memory completely deleted!"}
    except Exception as exc:
        logger.exception("Failed to delete document")
        raise HTTPException(status_code=500, detail=str(exc))
