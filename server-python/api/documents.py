"""
================================================================================
DOCUMENT INGESTION & PIPELINE CONTROLLER LAYER (documents.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the entrypoint for the document ingestion pipeline. It allows
users and agents to upload files, raw text, URLs, and external connectors to feed
the RAG (Retrieval-Augmented Generation) vector index. It manages:
1. Chunked File Uploads: Resolves client-side large file uploads via sequential chunking to prevent memory bloat.
2. Direct Uploads: Processes single-file uploads using standard multipart forms.
3. Web Scraping & URL ingestion: Scrapes content from target URLs.
4. Raw Text additions: Allows manual text entry directly in the dashboard UI.
5. Ingestion State & WebSocket Progress tracking: Updates clients in real time about file
   processing status (uploading, chunking, embedding, index ready).
6. File/URL Syncing: Allows users to update or resync documents.

CONCURRENCY & ASYNCHRONOUS PROCESSING:
- Parsing large files, extracting content, generating vector embeddings, and inserting data
  into pgvector can be slow.
- To prevent thread blocking, the endpoints delegate the heavy work to FastAPI's `BackgroundTasks` queue.
- Clients can open a WebSocket connection at `/ws/documents/upload/status/{session_key}` to receive
  real-time progress updates sent by `upload_status_manager`.
"""

import logging
from utils.logger import get_department_logger
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, Depends, Header, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from schemas import URLRequest, ConnectorRequest
from api.auth import limiter
from handlers.websocket_handlers import upload_status_manager
from core.auth import get_current_user

# Import the document management handlers.
from handlers.document_handler import (
    handle_initiate_upload,
    handle_upload_chunk,
    handle_complete_upload,
    handle_view_document,
    handle_process_file,
    handle_process_url,
    handle_process_connector,
    handle_get_documents,
    handle_delete_document,
    handle_update_url,
    handle_process_text,
    handle_update_text,
    handle_update_file,
    handle_sync_connector
)

# Initialize standard module-level logger.
logger = get_department_logger("knowledge_base")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["documents"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class InitiateUploadRequest(BaseModel):
    """
    Validation schema for initiating a chunked file upload.
    """
    agent_id: str # Target AI agent UUID
    filename: str # Name of the file being uploaded
    file_size_bytes: int # Size of the file in bytes


class CompleteUploadRequest(BaseModel):
    """
    Validation schema for finalising a chunked file upload.
    """
    upload_id: str # Upload session UUID
    agent_id: str # Target AI agent UUID
    filename: str # Output filename


class TextRequest(BaseModel):
    """
    Validation schema for manual raw text ingestion.
    """
    agent_id: str # Target AI agent UUID
    filename: str # Name/label assigned to the text snippet
    text: str # Raw text content


class TextUpdateRequest(BaseModel):
    """
    Validation schema for updating ingested raw text.
    """
    filename: str
    text: str


class URLUpdateRequest(BaseModel):
    """
    Validation schema for updating/replacing an ingested URL.
    """
    url: str


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.websocket("/ws/documents/upload/status/{session_key}")
async def upload_status_ws(websocket: WebSocket, session_key: str):
    """
    Establishes a WebSocket connection for tracking document upload progress.

    Purpose:
        Streams processing status updates (e.g. 'parsing', 'generating embeddings', 'ready')
        to the client during document ingestion.

    Parameters:
        websocket (WebSocket): The connection object.
        session_key (str): A unique ID identifier tracking the upload session.

    Returns:
        None.

    Side Effects / State Changes:
        - Upgrades the HTTP connection to WebSocket.
        - Adds connection to the `upload_status_manager` pool.

    Errors / Exceptions:
        - Handles `WebSocketDisconnect` gracefully, cleaning up the connection pool.
    """
    logger.info(f"🔌 WebSocket connection requested for upload status agent: {session_key}")
    # Register the connection.
    await upload_status_manager.connect(websocket, session_key)
    logger.info(f"✅ WebSocket connected for upload status agent: {session_key}")
    try:
        # Keep the connection alive by waiting for client messages.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Disconnect and clean up from the connection pool.
        upload_status_manager.disconnect(websocket, session_key)
        logger.info(f"❌ WebSocket disconnected for upload status agent: {session_key}")


@router.post("/api/documents/upload/initiate")
@limiter.limit("10/minute")
async def initiate_upload(req: InitiateUploadRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    Initiates a chunked file upload.

    Purpose:
        Validates file metadata, checks user storage quotas, and generates
        a session upload ID.
        This endpoint is rate-limited to 10 requests per minute.

    Parameters:
        req (InitiateUploadRequest): Contains the agent ID, filename, and file size.
        request (Request): The incoming request. Required by the rate limiter.
        current_user (dict): JWT details.

    Returns:
        dict: Session upload ID and recommended chunk sizes.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
        - Raises 400 Bad Request if user storage quotas are exceeded.
    """
    # Delegate verification and session initialization to the handler.
    return await handle_initiate_upload(req.agent_id, req.file_size_bytes)


@router.put("/api/documents/upload/chunk")
@limiter.limit("60/minute")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    request: Request,
    chunk: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Saves an uploaded file chunk.

    Purpose:
        Saves a chunk of a large file to a temporary directory on disk.
        This endpoint is rate-limited to 60 requests per minute.

    Parameters:
        upload_id (str): The unique UUID of the upload session.
        chunk_index (int): The index of this chunk.
        request (Request): The incoming request. Required by the rate limiter.
        chunk (UploadFile): The binary data of this chunk.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Writes binary data chunks to temporary files on disk.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
        - Raises 400 if the upload ID is invalid.
    """
    # Save the chunk.
    return await handle_upload_chunk(upload_id, chunk_index, chunk)


@router.post("/api/documents/upload/complete")
@limiter.limit("10/minute")
async def complete_upload(
    req: CompleteUploadRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Completes a chunked file upload.

    Purpose:
        Merges all temporary chunks, validates file security, saves metadata,
        and schedules background tasks to parse and embed the file.
        This endpoint is rate-limited to 10 requests per minute.

    Parameters:
        req (CompleteUploadRequest): Contains the upload ID, target agent ID, and filename.
        request (Request): The incoming request. Required by the rate limiter.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message and file metadata.

    Side Effects / State Changes:
        - Merges file chunks and writes the output file.
        - Writes metadata to the `documents` table.
        - Schedules background file parsing.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if chunks are missing or verification fails.
    """
    # Process the completed upload.
    return await handle_complete_upload(req.upload_id, req.agent_id, req.filename, background_tasks)


@router.get("/api/documents/{doc_id}/view")
async def view_document(
    doc_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Serves an uploaded document for viewing.

    Purpose:
        Streams the file content to the browser for rendering or previewing.

    Parameters:
        doc_id (str): UUID of the document.
        token (str, optional): Authentication token passed via query parameters.
        authorization (str, optional): Authentication token passed via the Authorization header.

    Returns:
        StreamingResponse: Stream of the file content.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401/403 if authorization fails.
        - Raises 404 Not Found if the document does not exist.
    """
    # Fetch and stream the document.
    return await handle_view_document(doc_id, token if token else authorization)


@router.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Uploads and processes a single file directly.

    Purpose:
        Processes smaller uploads that don't need chunking in a single request.
        Saves metadata and triggers background parsing.

    Parameters:
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        file (UploadFile): The uploaded file.
        agent_id (str): UUID of the target agent to link the document to.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message and file metadata.

    Side Effects / State Changes:
        - Saves the file to disk.
        - Writes metadata to the `documents` table.
        - Schedules background file parsing.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if validation fails.
    """
    # Process the file upload.
    return await handle_process_file(agent_id, file, background_tasks)


@router.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Imports and processes content from a target URL.

    Purpose:
        Saves the URL details and schedules background scraping and parsing.

    Parameters:
        req (URLRequest): Contains the agent ID and target URL.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message and document metadata.

    Side Effects / State Changes:
        - Writes metadata to the `documents` table.
        - Schedules background web scraping.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if the URL format is invalid.
    """
    # Process the URL.
    return await handle_process_url(req.agent_id, req.url, background_tasks)


@router.post("/process-connector")
async def process_connector(req: ConnectorRequest, current_user: dict = Depends(get_current_user)):
    """
    Triggers a mock sync task for external integrations (for demo purposes).

    Parameters:
        req (ConnectorRequest): Contains target agent ID and connector details.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.
    """
    return await handle_process_connector(req.agent_id, req.connector_id)


@router.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    Lists all documents linked to an agent.

    Parameters:
        agent_id (str): UUID of the target agent.
        current_user (dict): JWT details.

    Returns:
        list of dict: Documents metadata records.

    Side Effects / State Changes:
        - None. Read-only query.
    """
    # Fetch documents linked to the agent.
    return await handle_get_documents(agent_id)


@router.get("/agents/batch-documents")
async def get_batch_documents(agent_ids: str, current_user: dict = Depends(get_current_user)):
    """
    Fetches documents for multiple agents in a single parallel request.

    Purpose:
        Replaces N sequential calls to /agents/{id}/documents with a single batch endpoint.
        All agent document queries are fired simultaneously using asyncio.gather(), reducing
        total latency from N × query_time to max(query_time).

    Parameters:
        agent_ids (str): Comma-separated list of agent UUIDs.
                         Example: ?agent_ids=uuid1,uuid2,uuid3
        current_user (dict): JWT details.

    Returns:
        dict: Mapping of agent_id → list of document records.
              Example: { "uuid1": [...], "uuid2": [...], "uuid3": [] }

    Side Effects / State Changes:
        - None. Read-only queries.
    """
    import asyncio

    # Parse and validate the comma-separated agent IDs.
    ids = [aid.strip() for aid in agent_ids.split(",") if aid.strip()]
    if not ids:
        return {}

    # Fire all document fetches in parallel.
    results = await asyncio.gather(*[handle_get_documents(aid) for aid in ids])

    # Return as a map: agent_id → documents list.
    return {agent_id: docs for agent_id, docs in zip(ids, results)}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    """
    Permanently deletes a document.

    Purpose:
        Removes file metadata, vector embeddings, and physical files from storage.

    Parameters:
        doc_id (str): UUID of the document to delete.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes rows in `documents` and `document_chunks` tables.
        - Deletes the physical file from disk.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the document is not found.
    """
    # Delete the document.
    return await handle_delete_document(doc_id)


@router.post("/api/documents/{doc_id}/update-url")
async def update_url(doc_id: str, req: URLUpdateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Updates the target URL of a document.

    Purpose:
        Updates the URL of a document and triggers a background scraping task.

    Parameters:
        doc_id (str): UUID of the document.
        req (URLUpdateRequest): Contains the new URL.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the URL in the database.
        - Schedules background scraping tasks.
    """
    # Update and process the new URL.
    return await handle_update_url(doc_id, req.url, background_tasks)


@router.post("/api/documents/process-text")
async def process_text(req: TextRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Imports manual raw text.

    Purpose:
        Saves the text and schedules background task processing.

    Parameters:
        req (TextRequest): Contains target agent ID, filename, and raw text.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Writes the raw text to the database.
        - Schedules background text parsing.
    """
    # Save and process the text.
    return await handle_process_text(req.agent_id, req.filename, req.text, background_tasks)


@router.post("/api/documents/{doc_id}/update-text")
async def update_text(doc_id: str, req: TextUpdateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Updates the text content of a document.

    Purpose:
        Modifies manual text and triggers background processing.

    Parameters:
        doc_id (str): UUID of the document.
        req (TextUpdateRequest): Contains the updated filename and text.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the raw text in the database.
        - Schedules background text parsing.
    """
    # Update and process the text.
    return await handle_update_text(doc_id, req.filename, req.text, background_tasks)


@router.put("/api/documents/{doc_id}/update-file")
async def update_file(doc_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Replaces a document file.

    Purpose:
        Overwrites an existing file and schedules background parsing tasks.

    Parameters:
        doc_id (str): UUID of the document to replace.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        file (UploadFile): The replacement file.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Overwrites the file on disk.
        - Updates rows in the `documents` table.
        - Schedules background file parsing.
    """
    # Replace the file.
    return await handle_update_file(doc_id, file, background_tasks)


@router.post("/api/documents/{doc_id}/sync")
async def sync_connector(doc_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Syncs a document connector.

    Purpose:
        Triggers a sync update from the source connector in a background task.

    Parameters:
        doc_id (str): UUID of the document.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Schedules background sync tasks.
    """
    # Sync the connector.
    return await handle_sync_connector(doc_id, background_tasks)

