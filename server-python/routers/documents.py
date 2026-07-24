"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Knowledge Base Document
management actions in the RAGMate backend. It maps inbound HTTP REST requests and
WebSocket connections directly to the underlying business logic executors defined
inside the document handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard typing libraries, FastAPI APIRouter routing components,
   File/Form structures, WebSocket protocols and disconnect exceptions, validation schemas,
   rate limiters, handlers, and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter for 'documents' tag groupings.
3. Input Payload Validation Schemas:
   - `InitiateUploadRequest`: Validates body parameters when initiating chunked uploads.
   - `CompleteUploadRequest`: Validates body parameters when finalizing chunked uploads.
4. HTTP and WebSocket Routes:
   - WS `/ws/documents/upload/status/{session_key}`: Real-time progress updates channel.
   - POST `/api/documents/upload/initiate`: Allocates upload session credentials.
   - PUT `/api/documents/upload/chunk`: Saves individual file chunks.
   - POST `/api/documents/upload/complete`: Reassembles chunks and starts background processing.
   - GET `/api/documents/{doc_id}/view`: Streams decrypted document content.
   - POST `/process-file`: Ingests smaller, single-upload documents.
   - POST `/process-url`: Web scrapes raw text off URL targets.
   - POST `/process-connector`: Connects external data integrations.
   - GET `/agents/{agent_id}/documents`: Lists documents linked to agents.
   - DELETE `/documents/{doc_id}`: Deletes documents and text chunks.
"""

import logging  # Import python logging library
from typing import Optional  # Import typing Optional for parameter validations
# Import FastAPI parameters for routing, files, forms, dependencies, headers, and WebSockets
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, Depends, Header, Request, WebSocket, WebSocketDisconnect

# Import local data validation schemas
from schemas import URLRequest, ConnectorRequest
# Rate limiter instance
from routers.auth import limiter
# Real-time WebSockets upload progress manager
from handlers.websocket_handlers import upload_status_manager

# Import document logic handlers
from handlers.document_handler import (
    handle_initiate_upload,
    handle_upload_chunk,
    handle_complete_upload,
    handle_view_document,
    handle_process_file,
    handle_process_url,
    handle_process_connector,
    handle_get_documents,
    handle_delete_document
)
from pydantic import BaseModel  # Pydantic BaseModels for payload validations
from core.auth import get_current_user  # JWT helper to authenticate requests

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for document endpoints
router = APIRouter(tags=["documents"])

class InitiateUploadRequest(BaseModel):
    """
    Validates payload options when starting a chunked upload transaction.
    """
    agent_id: str                              # Target AI Agent UUID
    filename: str                              # Name of the file being uploaded
    file_size_bytes: int                       # Total size of the file in bytes

class CompleteUploadRequest(BaseModel):
    """
    Validates payload options when finalizing chunked uploads.
    """
    upload_id: str                             # The unique upload session ID
    agent_id: str                              # Target AI Agent UUID
    filename: str                              # Name of the file being reassembled


@router.websocket("/ws/documents/upload/status/{session_key}")
async def upload_status_ws(websocket: WebSocket, session_key: str):
    """
    HTTP WebSocket endpoint opening a real-time connection to stream
    document vectorization progress updates to the user.

    Parameters:
        websocket (websocket): The raw FastAPI WebSocket connection context.
        session_key (str): Unique upload tracking session key.

    Returns:
        None: Pipes raw sockets status updates to the manager.

    Exceptions Raised:
        WebSocketDisconnect: Safely handled when clients sever socket connections.
    """
    logger.info(f"🔌 WebSocket connection requested for upload status agent: {session_key}")
    # Establish WebSocket protocol handshake and register listener
    await upload_status_manager.connect(websocket, session_key)
    logger.info(f"✅ WebSocket connected for upload status agent: {session_key}")
    try:
        # Maintain socket connection alive, listening to inputs
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Deregister listener on connection sever
        upload_status_manager.disconnect(websocket, session_key)
        logger.info(f"❌ WebSocket disconnected for upload status agent: {session_key}")


@router.post("/api/documents/upload/initiate")
@limiter.limit("10/minute")  # Limit submissions to 10 attempts per minute per IP address
async def initiate_upload(req: InitiateUploadRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint starting a chunked upload. Checks storage quotas.

    Parameters:
        req (InitiateUploadRequest): The pydantic-validated request payload.
        request (Request): The raw FastAPI HTTP request payload context.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing the upload ID and recommended chunk size.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(403): Raised if workspace storage limits are exceeded.
        HTTPException(500): Raised if upload initiation crashes.
    """
    # Route execution to handlers layer
    return await handle_initiate_upload(req.agent_id, req.file_size_bytes)


@router.put("/api/documents/upload/chunk")
@limiter.limit("60/minute")  # Limit chunk uploads to 60 attempts per minute per IP address
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    request: Request,
    chunk: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    HTTP PUT endpoint to upload individual chunks of a large file.

    Parameters:
        upload_id (str): Unique upload tracking ID path parameter.
        chunk_index (int): Index number of the chunk (0-indexed).
        request (Request): The raw FastAPI HTTP request payload context.
        chunk (UploadFile): Binary stream of the chunk.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if upload session ID not found.
        HTTPException(500): Raised if saving the chunk file fails.
    """
    # Route execution to handlers layer
    return await handle_upload_chunk(upload_id, chunk_index, chunk)


@router.post("/api/documents/upload/complete")
@limiter.limit("10/minute")  # Limit completions to 10 attempts per minute per IP address
async def complete_upload(
    req: CompleteUploadRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    HTTP POST endpoint to finalize a chunked upload. Reassembles chunks, verifies integrity,
    and schedules background processing.

    Parameters:
        req (CompleteUploadRequest): The pydantic-validated request payload.
        request (Request): The raw FastAPI HTTP request payload context.
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(400): Raised if magic bytes check fails or reassembly crashes.
        HTTPException(500): Raised if ingestion processes crash.
    """
    # Route execution to handlers layer
    return await handle_complete_upload(req.upload_id, req.agent_id, req.filename, background_tasks)


@router.get("/api/documents/{doc_id}/view")
async def view_document(
    doc_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    HTTP GET endpoint to retrieve and stream decrypted document content.
    Accepts access tokens from query parameters or HTTP authorization headers.

    Parameters:
        doc_id (str): Target Document UUID path parameter.
        token (str, optional): Token provided in the URL query parameter.
        authorization (str, optional): Token provided in the HTTP authorization headers.

    Returns:
        StreamingResponse: Stream containing the decrypted data.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if file not found.
        HTTPException(500): Raised if decryption crashes.
    """
    # Route execution to handlers layer, passing either query parameter or Header token
    return await handle_view_document(doc_id, token if token else authorization)


@router.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    HTTP POST endpoint to ingest smaller single-upload documents.

    Parameters:
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.
        file (UploadFile): FastAPI binary upload body parameters mapping.
        agent_id (str): Target AI Agent UUID (Form Parameter).
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(400): Raised if file extension is invalid.
        HTTPException(500): Raised if ingestion crashes.
    """
    # Route execution to handlers layer
    return await handle_process_file(agent_id, file, background_tasks)


@router.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint scraping and vectorizing content from a target URL.

    Parameters:
        req (URLRequest): The pydantic-validated request payload.
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Ingestion status dictionary.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if scraping or ingestion crashes.
    """
    # Route execution to handlers layer
    return await handle_process_url(req.agent_id, req.url, background_tasks)


@router.post("/process-connector")
async def process_connector(req: ConnectorRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint integrating external data sources.

    Parameters:
        req (ConnectorRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Integration confirmation message.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database writes crash.
    """
    # Route execution to handlers layer
    return await handle_process_connector(req.agent_id, req.connector_id)


@router.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list all documents uploaded for an agent.

    Parameters:
        agent_id (str): Unique database AI Agent UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary mapping documents details in a list.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if queries fail.
    """
    # Route execution to handlers layer
    return await handle_get_documents(agent_id)


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP DELETE endpoint to delete a document and its memory.

    Parameters:
        doc_id (str): Target Document UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Deletion status confirmation message.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if deletions crash.
    """
    # Route execution to handlers layer
    return await handle_delete_document(doc_id)
