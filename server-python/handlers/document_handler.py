"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core manager for Knowledge Base Document Operations in RAGMate.
It processes, uploads, parses, retrieves, updates, and deletes documents that users
add to their AI Agents.

From top to bottom, the file executes as follows:
1. Imports: Standard filesystem/utility tools, FastAPI endpoints schemas, security scans
   (magic bytes & malware checking), cryptography functions (file encrypt/decrypt),
   and background processing pipelines.
2. Constants: Defines `CHUNKS_TEMP_DIR` to coordinate large chunked file uploads.
3. Chunked Upload Orchestration:
   - `handle_initiate_upload`: Initiates an upload session, checking storage limits beforehand.
   - `handle_upload_chunk`: Writes individual chunk files to temporary disk folders.
   - `handle_complete_upload`: Reassembles chunks, verifies file safety, encrypts contents,
     creates DB stubs, and spawns the embedding parser.
4. File Viewing/Decryption (`handle_view_document`): Checks JWT authorization headers, reads
   encrypted file bytes off disk, decrypts them, and streams files back to clients.
5. Ingestion Processors:
   - `handle_process_file`: Ingests smaller, single-upload files.
   - `handle_process_url`: Web scrapes raw text off URL targets.
   - `handle_process_connector`: Simulated interface integrations.
   - `handle_process_text`: Ingests custom raw text blocks entered in client fields.
6. Indices and Maintenance Operations:
   - `handle_get_documents` & `handle_delete_document`: Fetches index directories or wipes data.
   - `handle_update_url`, `handle_update_text`, `handle_update_file`: Modifies existing indices
     by deleting original text nodes and executing background re-indexing.
   - `handle_sync_connector`: Triggers simulated background connector sync operations.
"""

import os  # Read/edit filesystem entries and check file presence
import shutil  # File operations like copy operations and tree deletions
import uuid  # Generate unique session upload tracking IDs
import jwt  # Decrypt and validate JSON Web Tokens for authentication
from pathlib import Path  # Object-oriented path navigation
from typing import Optional  # Strict type annotations
from fastapi import HTTPException, BackgroundTasks, UploadFile  # FastAPI HTTP routing structures
from fastapi.responses import StreamingResponse  # Streaming output blocks to clients
from io import BytesIO  # Buffer stream tools for binary inputs
import asyncio  # Manage asynchronous thread transitions

# RAG Engines and uploading configurations
from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import encrypt_data, decrypt_data
from core.security_scan import validate_magic_bytes, scan_malicious_content
from utils import background_ingestion, get_user_limits_by_id
from schemas import URLRequest, ConnectorRequest
from handlers.document_processor import async_background_ingestion
from handlers.websocket_handlers import upload_status_manager
from db import document_repository

# Logger module
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "knowledge_base" activities
logger = get_department_logger("knowledge_base")

# Temporary folder structure to reassemble chunked file uploads (configured inside workspace directory)
CHUNKS_TEMP_DIR = Path("temp_uploads") / "chunks"
CHUNKS_TEMP_DIR.mkdir(parents=True, exist_ok=True)

async def handle_initiate_upload(agent_id: str, file_size_bytes: int):
    """
    Initializes a chunked upload transaction session for uploading large documents.
    Validates user storage quotas and limits file size to a maximum of 100MB.

    Parameters:
        agent_id (str): The unique database UUID identifying the target AI Agent.
        file_size_bytes (int): Total size in bytes of the incoming document file.

    Returns:
        dict: A dictionary containing the generated 'upload_id' and the chunk size limits.

    Exceptions Raised:
        HTTPException(404): Raised if agent not found.
        HTTPException(403): Raised if workspace storage limits are exceeded.
        HTTPException(400): Raised if the file size exceeds 100MB.
        HTTPException(500): Raised if database queries fail.
    """
    # Log information indicating initiation is triggered
    logger.info(f"Initiating chunked upload for agent: {agent_id} (size: {file_size_bytes} bytes)")
    try:
        # Retrieve agent details and current storage usage
        logger.debug("Retrieving agent storage usage info from document_repository...")
        user_storage = await document_repository.get_agent_and_user_storage(agent_id)
        if not user_storage or not user_storage[0]:
            logger.warning(f"Upload initiation aborted: Agent ID {agent_id} not found.")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        user_id, current_storage = user_storage
        logger.debug(f"User ID: {user_id}, Current Storage Used: {current_storage} bytes")
        
        # Load user limits parameters from DB
        limits = await get_user_limits_by_id(user_id)
        logger.debug(f"User limits retrieved: Storage Limit: {limits['storage_mb']}MB")

        # Check if the upload will exceed limits
        if current_storage + file_size_bytes > (limits["storage_mb"] * 1024 * 1024):
            logger.warning(f"Upload initiation aborted: User {user_id} would exceed storage limit.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Check if file size exceeds maximum limits
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 Megabytes limit
        if file_size_bytes > MAX_FILE_SIZE:
            logger.warning(f"Upload initiation aborted: File size {file_size_bytes} exceeds maximum of 100MB.")
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 100MB.")

        # Generate a unique tracking UUID for this upload session
        upload_id = str(uuid.uuid4())
        # Create a directory to store chunks
        upload_dir = CHUNKS_TEMP_DIR / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Upload session successfully initiated. Session ID: {upload_id}")
        return {
            "upload_id": upload_id,
            "chunk_size_bytes": 5 * 1024 * 1024,  # Standard size recommendation: 5MB per chunk
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate chunked upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_upload_chunk(upload_id: str, chunk_index: int, chunk: UploadFile):
    """
    Saves an uploaded chunk to disk under the corresponding upload session folder.

    Parameters:
        upload_id (str): The unique transaction ID of the upload session.
        chunk_index (int): Index number of the chunk (0-indexed).
        chunk (UploadFile): Binary stream of the chunk.

    Returns:
        dict: A confirmation dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if the session ID directory is not found on disk.
        HTTPException(500): Raised if saving the chunk file fails.
    """
    logger.debug(f"Uploading chunk index {chunk_index} for upload session: {upload_id}")
    # Locate upload directory
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    if not upload_dir.exists():
        logger.warning(f"Chunk upload failed: Session ID {upload_id} not found or expired.")
        raise HTTPException(status_code=404, detail="Upload session not found")

    chunk_path = upload_dir / f"chunk_{chunk_index}"
    try:
        # Define a helper function to execute file writes
        def save_file():
            with open(chunk_path, "wb") as buffer:
                shutil.copyfileobj(chunk.file, buffer)
        # Execute the helper in a threadpool to prevent blocking the async event loop
        await asyncio.to_thread(save_file)
        logger.debug(f"Chunk index {chunk_index} saved successfully to disk.")
        return {"message": f"Chunk {chunk_index} uploaded successfully."}
    except Exception as e:
        logger.error(f"Failed to save chunk index {chunk_index} for session {upload_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_complete_upload(upload_id: str, agent_id: str, filename: str, background_tasks: BackgroundTasks):
    """
    Finalizes the chunked upload session:
    - Reassembles chunks in chronological order.
    - Purges the temporary chunk directory.
    - Executes magic bytes validation and security scans.
    - Encrypts and saves the reassembled file to disk.
    - Inserts a document stub in the database.
    - Spawns background processing to chunk and vectorize text content.

    Parameters:
        upload_id (str): The unique upload session ID.
        agent_id (str): Target AI Agent UUID.
        filename (str): Original uploaded file name.
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400/404/403): Raised for validation, limit, or reassembly errors.
        HTTPException(500): Raised for storage or script failures.
    """
    logger.info(f"Completing upload session: {upload_id} for file: '{filename}'")
    upload_dir = CHUNKS_TEMP_DIR / upload_id
    if not upload_dir.exists():
        logger.warning(f"Upload completion failed: Session ID {upload_id} not found.")
        raise HTTPException(status_code=404, detail="Upload session not found or already completed")

    # Filter and sort chunk files chronologically
    chunk_files = sorted(
        [f for f in upload_dir.iterdir() if f.name.startswith("chunk_")],
        key=lambda x: int(x.name.split("_")[1])
    )

    if not chunk_files:
        logger.warning(f"Upload completion failed: No chunks found in session directory {upload_dir}")
        raise HTTPException(status_code=400, detail="No chunks found for this upload session")

    logger.debug(f"Reassembling {len(chunk_files)} file chunks in session: {upload_id}")
    file_bytes = b""
    # Read and merge binary chunks
    for chunk_file in chunk_files:
        with open(chunk_file, "rb") as f:
            file_bytes += f.read()

    # Clean up temporary directory
    logger.debug(f"Purging temporary chunk directory: {upload_dir}")
    shutil.rmtree(upload_dir)

    # Validate file integrity
    logger.debug("Validating magic bytes/file integrity...")
    is_valid_magic, magic_err = validate_magic_bytes(file_bytes, filename)
    if not is_valid_magic:
        logger.warning(f"Upload rejected: Magic byte validation failed for '{filename}': {magic_err}")
        raise HTTPException(status_code=400, detail=magic_err)

    # Perform security scan on the reassembled bytes
    logger.debug("Scanning file for malicious content...")
    is_secure, scan_err = scan_malicious_content(file_bytes, filename)
    if not is_secure:
        logger.warning(f"Upload rejected: Security scan flagged file '{filename}': {scan_err}")
        raise HTTPException(status_code=400, detail=scan_err)

    safe_filename = os.path.basename(filename)
    file_path = UPLOAD_DIR / safe_filename
    temp_path = str(file_path) + ".tmp"
    
    # Save unencrypted content to a temporary file (needed for parsing tools)
    logger.debug(f"Writing unencrypted file to temporary path: {temp_path}")
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Save encrypted copy to permanent storage directory
    logger.debug(f"Writing encrypted permanent file copy to: {file_path}")
    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    try:
        # Query agent configuration details
        logger.debug("Querying agent configuration in database...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error(f"Agent ID {agent_id} not found during upload finalization. Cleaning up disk files.")
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

        # Check limits one last time post-reassembly
        logger.debug(f"Verifying final limits post-reassembly. Current storage: {current_storage}, file size: {file_size}")
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning(f"Storage limit exceeded. Deleting files.")
            if os.path.exists(temp_path): os.remove(temp_path)
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Insert placeholder document in database
        logger.debug("Inserting document entry stub in database...")
        document_id = await document_repository.insert_document(agent_id, safe_filename, "processing", file_size)

        # Broadcast status via WebSockets
        logger.info(f"Scheduling asynchronous background ingestion task for document ID: {document_id}")
        await upload_status_manager.send_status(agent_id, "processing", safe_filename, "Starting background document ingestion...", 0.1)

        # Spawn background processing to chunk and index the document
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

        logger.info(f"Reassembly complete. Background ingestion running for document ID: {document_id}")
        return {"message": "File uploaded and verified successfully. Ingestion scheduled in background."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to finalize complete upload: {str(exc)}", exc_info=True)
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_view_document(doc_id: str, jwt_token: str):
    """
    Decrypted and streams document content back to users. Validates requests using JWT signatures.

    Parameters:
        doc_id (str): The unique database UUID of the document.
        jwt_token (str): JWT authentication token string.

    Returns:
        StreamingResponse: Stream containing the decrypted data.

    Exceptions Raised:
        HTTPException(401): Raised if JWT verification fails.
        HTTPException(404): Raised if document or file is missing.
    """
    logger.info(f"Retrieving and decrypting document ID: {doc_id} for viewing")
    from core.auth import JWT_SECRET, ALGORITHM
    try:
        # Validate JWT token and audience parameters
        jwt.decode(jwt_token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
        logger.debug("JWT validation check successful.")
    except Exception as e:
        logger.warning(f"Unauthorized access request for document ID {doc_id}: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: {str(e)}")

    logger.debug("Fetching filename from database...")
    filename = await document_repository.get_document_filename(doc_id)
    if not filename:
        logger.warning(f"Document ID {doc_id} not found in database.")
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        logger.error(f"Encrypted document file missing on disk: {file_path}")
        raise HTTPException(status_code=404, detail="Encrypted file not found on disk")

    logger.debug(f"Reading encrypted file data from {file_path}")
    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    # Decrypt binary payload
    logger.debug("Decrypting document payload...")
    decrypted_data = decrypt_data(encrypted_data)

    # Set response mime-type depending on extension
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

    logger.info(f"Streaming decrypted file '{filename}' (Type: {media_type})")
    return StreamingResponse(
        BytesIO(decrypted_data),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )


async def handle_process_file(agent_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    """
    Ingests smaller single-upload documents.
    Verifies extension white-lists, checks user storage space, encrypts content to disk,
    adds a document placeholder in database, and triggers background indexing.

    Parameters:
        agent_id (str): Target AI Agent UUID.
        file (UploadFile): FastAPI binary payload mapping.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400/404/403): Raised for validation, storage, or config failures.
        HTTPException(500): Raised for backend crashes.
    """
    logger.info(f"Processing uploaded file: '{file.filename}' for agent ID: {agent_id}")
    allowed_exts = {"pdf", "txt", "docx", "csv", "png", "jpg", "jpeg"}
    if not file.filename:
        logger.warning("File upload rejected: Missing filename")
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        logger.warning(f"File upload rejected: Extension '{ext}' is not permitted.")
        raise HTTPException(status_code=400, detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.")

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename
    file_bytes = file.file.read()
    
    temp_path = str(file_path) + ".tmp"
    logger.debug(f"Writing unencrypted uploaded content to temporary path: {temp_path}")
    with open(temp_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    logger.debug(f"Encrypting and writing uploaded file to permanent path: {file_path}")
    with open(file_path, "wb") as buffer:
        buffer.write(encrypt_data(file_bytes))

    try:
        logger.debug("Querying agent workspace configuration from database...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error(f"Agent ID {agent_id} not found during file upload processing.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        logger.debug("Retrieving user storage limits...")
        limits = await get_user_limits_by_id(user_id)
        file_size = os.path.getsize(file_path)

        # Validate storage limits
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning(f"File upload rejected: User storage limit reached. Cleaning up disk.")
            os.remove(file_path)
            os.remove(temp_path)
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Extract text content from the document
        logger.debug("Executing threadpool block to extract plain text content from file...")
        raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, safe_filename)

        # Register document status in database
        logger.debug("Inserting document entry stub in database...")
        document_id = await document_repository.insert_document(agent_id, safe_filename, "processing", file_size)

        # Queue parsing task in background
        logger.info(f"Scheduling background ingestion task for document ID: {document_id}")
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
        logger.error(f"Failed to process uploaded file: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Delete temporary unencrypted file
        if os.path.exists(temp_path):
            logger.debug(f"Cleaning up temporary file {temp_path}")
            os.remove(temp_path)


async def handle_process_url(agent_id: str, url: str, background_tasks: BackgroundTasks):
    """
    Scrapes and vectorizes content from a target URL.
    Checks workspace storage limits, scrapes HTML text, creates document stubs,
    and schedules background vector generation.

    Parameters:
        agent_id (str): Target AI Agent UUID.
        url (str): Target URL string.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403/404): Raised for storage or configuration failures.
        HTTPException(500): Raised for network or server errors.
    """
    logger.info(f"Processing URL ingestion target: '{url}' for agent ID: {agent_id}")
    try:
        logger.debug("Querying agent configuration in database...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.warning(f"URL process aborted: Agent ID {agent_id} not found.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        # Scrape and extract text content from the URL
        logger.debug("Executing URL scraping / content extraction...")
        raw_text = rag_engine.extract_text_from_url(url)
        file_size = len(raw_text.encode("utf-8"))

        logger.debug("Retrieving user storage limits...")
        limits = await get_user_limits_by_id(user_id)

        # Check storage space limits
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning("URL process aborted: Storage limits exceeded.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Save document placeholder in database
        logger.debug("Inserting document record stub in database...")
        document_id = await document_repository.insert_document(agent_id, url, "processing", file_size)

        # Queue text chunking and vector indexing task in background
        logger.info(f"Scheduling background URL ingestion task for document ID: {document_id}")
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
        logger.error(f"Failed to process URL: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_process_connector(agent_id: str, connector_id: str):
    """
    Integrates external data sources.

    Parameters:
        agent_id (str): Target AI Agent UUID.
        connector_id (str): Identity name (e.g. gdrive, notion, slack, github).

    Returns:
        dict: Integration confirmation message.

    Exceptions Raised:
        HTTPException(500): Raised if database writes crash.
    """
    logger.info(f"Connecting data source connector ID: {connector_id} for agent: {agent_id}")
    await asyncio.sleep(1.5)  # Simulate network latency
    connector_names = {
        "gdrive": "Google Drive Sync",
        "notion": "Notion Workspace Sync",
        "slack": "Slack Channels Sync",
        "github": "GitHub Repository Sync"
    }
    display_name = connector_names.get(connector_id, f"{connector_id.capitalize()} Sync")

    try:
        logger.debug("Inserting connector document entry stub in database...")
        await document_repository.insert_document(agent_id, display_name, "completed", 2048576)
        logger.info(f"Successfully integrated connector: '{display_name}'")
        return {"message": f"Successfully connected to {display_name}."}
    except Exception as exc:
        logger.error(f"Failed to process connector {connector_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_get_documents(agent_id: str):
    """
    Lists all documents uploaded for an agent.

    Parameters:
        agent_id (str): Unique database AI Agent UUID.

    Returns:
        dict: A dictionary mapping documents details in a list.

    Exceptions Raised:
        HTTPException(500): Raised if query fails.
    """
    logger.info(f"Retrieving document index for agent ID: {agent_id}")
    try:
        logger.debug("Fetching documents from database...")
        rows = await document_repository.get_documents_for_agent(agent_id)
        logger.debug(f"Retrieved {len(rows)} documents from database.")
        
        # Construct output dictionary
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
        logger.info(f"Successfully returned {len(docs)} documents.")
        return {"documents": docs}
    except Exception as exc:
        logger.error(f"Failed to fetch documents for agent {agent_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_document(doc_id: str):
    """
    Deletes a document from the database and disk.
    Wipes both text chunk vectors and physical disk files.

    Parameters:
        doc_id (str): The unique document UUID.

    Returns:
        dict: Deletion status confirmation message.

    Exceptions Raised:
        HTTPException(500): Raised if deletions fail.
    """
    logger.info(f"Requesting deletion of document ID: {doc_id}")
    try:
        logger.debug("Executing document deletion in database...")
        filename = await document_repository.delete_document_data(doc_id)
        if filename:
            file_path = UPLOAD_DIR / filename
            logger.debug(f"Associated file found on disk: {file_path}. Removing file...")
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Disk file '{filename}' removed successfully.")
        logger.info(f"Document ID {doc_id} successfully deleted from database.")
        return {"message": "Document and its memory completely deleted!"}
    except Exception as exc:
        logger.error(f"Failed to delete document ID {doc_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_update_url(doc_id: str, url: str, background_tasks: BackgroundTasks):
    """
    Updates the target URL of a scraped document and schedules re-scraping in the background.

    Parameters:
        doc_id (str): The document UUID.
        url (str): The new URL target.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403/404): Raised for storage or document configuration errors.
        HTTPException(500): Raised for server failures.
    """
    logger.info(f"Updating URL target to '{url}' for document ID: {doc_id}")
    try:
        # Check original document metadata parameters
        logger.debug("Fetching existing document metadata...")
        doc = await document_repository.get_document_by_id(doc_id)
        if not doc:
            logger.warning(f"URL update aborted: Document ID {doc_id} not found.")
            raise HTTPException(status_code=404, detail="Document not found")
        agent_id = doc[1]
        old_size = doc[4] or 0

        # Query config details
        logger.debug("Fetching agent configurations...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error("Agent details not found.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        # Scrape and extract text content from the new URL
        logger.debug("Extracting updated target URL content...")
        raw_text = rag_engine.extract_text_from_url(url)
        file_size = len(raw_text.encode("utf-8"))

        limits = await get_user_limits_by_id(user_id)

        # Check workspace limits
        if (current_storage - old_size) + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning("URL update aborted: Storage limit exceeded.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Purge existing text embeddings and reset status in database
        logger.debug("Purging old document indices and preparing database for re-indexing...")
        await document_repository.prepare_document_for_reindexing(doc_id, url, file_size)

        # Queue re-ingestion task in background
        logger.info(f"Scheduling URL re-ingestion task for doc ID: {doc_id}")
        background_tasks.add_task(
            background_ingestion,
            doc_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            None,
        )
        return {"message": "URL edited. Processing in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update URL document {doc_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_process_text(agent_id: str, filename: str, text: str, background_tasks: BackgroundTasks):
    """
    Ingests custom text input snippets entered in the client console.
    Saves and encrypts the snippet on disk, inserts placeholders in the database, and indexes in background.

    Parameters:
        agent_id (str): Target AI Agent UUID.
        filename (str): Desired text document label name.
        text (str): Raw text string payload.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: Ingestion status dictionary.

    Exceptions Raised:
        HTTPException(403/404): Raised for storage or database configuration errors.
        HTTPException(500): Raised if saving or indexing fails.
    """
    logger.info(f"Processing custom text snippet: '{filename}' for agent ID: {agent_id}")
    try:
        # Enforce file format ending in .txt
        if not filename.endswith(".txt"):
            filename += ".txt"
            
        logger.debug("Fetching agent configurations...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error("Agent details not found.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        file_bytes = text.encode("utf-8")
        file_size = len(file_bytes)

        limits = await get_user_limits_by_id(user_id)

        # Check storage space limits
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning("Text snippet upload rejected: Storage limit exceeded.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        safe_filename = os.path.basename(filename)
        file_path = UPLOAD_DIR / safe_filename
        
        # Save encrypted copy to disk
        logger.debug(f"Encrypting and saving custom text payload to disk: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(encrypt_data(file_bytes))

        # Save document placeholder in database
        logger.debug("Inserting document entry stub in database...")
        document_id = await document_repository.insert_document(agent_id, safe_filename, "processing", file_size)

        # Queue text chunking and vector indexing in background
        logger.info(f"Scheduling custom text ingestion in background. Document ID: {document_id}")
        background_tasks.add_task(
            background_ingestion,
            document_id,
            agent_id,
            text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {"message": "Custom text snippet created. Processing in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to process custom text payload: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_update_text(doc_id: str, filename: str, text: str, background_tasks: BackgroundTasks):
    """
    Updates the content or name of an existing custom text snippet.
    Safely purges the old file, saves the updated payload, and triggers background re-indexing.

    Parameters:
        doc_id (str): The document UUID.
        filename (str): Updated filename snippet.
        text (str): Updated raw text snippet.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403/404): Raised for storage or document configuration errors.
        HTTPException(500): Raised if re-indexing crashes.
    """
    logger.info(f"Updating custom text snippet document ID: {doc_id} (New Filename: '{filename}')")
    try:
        # Fetch target document details
        doc = await document_repository.get_document_by_id(doc_id)
        if not doc:
            logger.warning("Update text aborted: Document ID not found.")
            raise HTTPException(status_code=404, detail="Document not found")
        agent_id = doc[1]
        old_filename = doc[2]
        old_size = doc[4] or 0

        # Query agent configurations
        logger.debug("Fetching agent config parameters...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error("Agent not found.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        file_bytes = text.encode("utf-8")
        file_size = len(file_bytes)

        limits = await get_user_limits_by_id(user_id)

        # Check storage space limits
        if (current_storage - old_size) + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning("Update text aborted: Storage limits exceeded.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Clean up old file if name has changed
        if old_filename != filename:
            old_path = UPLOAD_DIR / old_filename
            logger.debug(f"Deleting outdated disk file: {old_path}")
            if old_path.exists():
                os.remove(old_path)

        safe_filename = os.path.basename(filename)
        file_path = UPLOAD_DIR / safe_filename
        
        # Save encrypted copy to disk
        logger.debug(f"Encrypting and saving new text payload to disk: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(encrypt_data(file_bytes))

        # Purge existing text embeddings and reset status in database
        logger.debug("Purging database document indices and resetting stub info...")
        await document_repository.prepare_document_for_reindexing(doc_id, safe_filename, file_size)

        # Queue re-ingestion task in background
        logger.info(f"Scheduling text re-ingestion task for doc ID: {doc_id}")
        background_tasks.add_task(
            background_ingestion,
            doc_id,
            agent_id,
            text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {"message": "Custom text snippet updated. Processing in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update custom text document ID {doc_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_update_file(doc_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    """
    Replaces an existing document with a newly uploaded file.
    Validates file extension, checks storage limits, cleans up old files,
    encrypts the new content, and triggers background re-indexing.

    Parameters:
        doc_id (str): The document UUID.
        file (UploadFile): The newly uploaded file stream.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400/403/404): Raised for validation, storage, or configuration failures.
        HTTPException(500): Raised if replacement crashes.
    """
    logger.info(f"Replacing file data for document ID: {doc_id} with new file: '{file.filename}'")
    try:
        doc = await document_repository.get_document_by_id(doc_id)
        if not doc:
            logger.warning("Replace file aborted: Target document ID not found.")
            raise HTTPException(status_code=404, detail="Document not found")
        agent_id = doc[1]
        old_filename = doc[2]
        old_size = doc[4] or 0

        # Validate file extensions
        allowed_exts = {"pdf", "txt", "docx", "csv", "png", "jpg", "jpeg"}
        if not file.filename:
            logger.warning("Replace file aborted: Missing filename.")
            raise HTTPException(status_code=400, detail="Filename is required")

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in allowed_exts:
            logger.warning(f"Replace file aborted: Extension '{ext}' is not permitted.")
            raise HTTPException(status_code=400, detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.")

        safe_filename = os.path.basename(file.filename)
        file_bytes = file.file.read()
        file_size = len(file_bytes)

        # Query agent configurations
        logger.debug("Fetching agent config parameters...")
        config = await document_repository.get_agent_config_and_storage(agent_id)
        if not config:
            logger.error("Agent not found.")
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = config["user_id"]
        embed_model = config["embed_model"] or "text-embedding-3-small"
        strategy = config["strategy"] or "sentence"
        current_storage = config["current_storage"]

        limits = await get_user_limits_by_id(user_id)

        # Check storage space limits
        if (current_storage - old_size) + file_size > (limits["storage_mb"] * 1024 * 1024):
            logger.warning("Replace file aborted: Storage limit exceeded.")
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        # Clean up old file from storage
        old_path = UPLOAD_DIR / old_filename
        logger.debug(f"Deleting old disk file: {old_path}")
        if old_path.exists():
            os.remove(old_path)

        file_path = UPLOAD_DIR / safe_filename
        temp_path = str(file_path) + ".tmp"
        
        # Save temporary unencrypted file
        logger.debug(f"Writing temporary unencrypted file: {temp_path}")
        with open(temp_path, "wb") as buffer:
            buffer.write(file_bytes)
            
        # Save encrypted copy permanently to disk
        logger.debug(f"Writing encrypted permanent file: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(encrypt_data(file_bytes))

        # Extract text content from the document
        logger.debug("Executing threadpool text extraction from the new file...")
        raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, safe_filename)

        # Purge existing text embeddings and update status in database
        logger.debug("Purging old document indices and preparing database for new indexing...")
        await document_repository.prepare_document_for_reindexing(doc_id, safe_filename, file_size)

        # Queue re-ingestion task in background
        logger.info(f"Scheduling file re-ingestion task for doc ID: {doc_id}")
        background_tasks.add_task(
            background_ingestion,
            doc_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {"message": "Document replaced successfully. Processing in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to replace document ID {doc_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Delete temporary unencrypted file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            logger.debug(f"Cleaning up temporary file {temp_path}")
            os.remove(temp_path)


async def handle_sync_connector(doc_id: str, background_tasks: BackgroundTasks):
    """
    Triggers sync operations for connector-linked documents in the background.

    Parameters:
        doc_id (str): The document UUID.
        background_tasks (BackgroundTasks): Background tasks coordinator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if document not found.
        HTTPException(500): Raised if sync process fails.
    """
    logger.info(f"Triggering sync request for connector document ID: {doc_id}")
    try:
        doc = await document_repository.get_document_by_id(doc_id)
        if not doc:
            logger.warning("Connector sync aborted: Document ID not found.")
            raise HTTPException(status_code=404, detail="Document not found")
        agent_id = doc[1]
        display_name = doc[2]

        # Reset document status in database
        logger.debug("Preparing database indices for connector reindexing...")
        await document_repository.prepare_document_for_reindexing(doc_id, display_name, 2048576)

        # Define simulated sync helper task
        async def simulated_sync_task():
            logger.debug(f"Simulating connector sync for document ID {doc_id} ({display_name})...")
            await upload_status_manager.send_status(agent_id, "processing", display_name, "Syncing from connector source...", 0.3)
            await asyncio.sleep(1.5)  # Simulate network latency
            await upload_status_manager.send_status(agent_id, "completed", display_name, "Sync completed successfully.", 1.0)
            
            # Update status flag to 'completed' in database
            logger.debug("Updating sync status to completed in database...")
            async with get_db_cursor_async(commit=True) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "UPDATE documents SET status = 'completed' WHERE id = %s",
                    (doc_id,)
                )
            logger.info(f"Connector sync completed successfully for doc ID: {doc_id}")

        background_tasks.add_task(simulated_sync_task)
        logger.info(f"Connector sync queued in background for doc ID: {doc_id}")
        return {"message": "Sync started in background..."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to sync connector document {doc_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
