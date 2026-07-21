import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, Depends, Header, Request, WebSocket, WebSocketDisconnect

from schemas import URLRequest, ConnectorRequest
from api.auth import limiter
from handlers.websocket_handlers import upload_status_manager
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
from pydantic import BaseModel
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])

class InitiateUploadRequest(BaseModel):
    agent_id: str
    filename: str
    file_size_bytes: int

class CompleteUploadRequest(BaseModel):
    upload_id: str
    agent_id: str
    filename: str


@router.websocket("/ws/documents/upload/status/{session_key}")
async def upload_status_ws(websocket: WebSocket, session_key: str):
    """
    What it does: Opens a real-time connection so the frontend can receive progress updates as a document is processed.
    Args:
        websocket (WebSocket): The connection provided by the user's browser.
        session_key (str): The unique ID of the ongoing upload session.
    Returns: None.
    """
    logger.info(f"🔌 WebSocket connection requested for upload status agent: {session_key}")
    await upload_status_manager.connect(websocket, session_key)
    logger.info(f"✅ WebSocket connected for upload status agent: {session_key}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        upload_status_manager.disconnect(websocket, session_key)
        logger.info(f"❌ WebSocket disconnected for upload status agent: {session_key}")


@router.post("/api/documents/upload/initiate")
@limiter.limit("10/minute")
async def initiate_upload(req: InitiateUploadRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """
    What it does: Receives a request from the user to start uploading a file, checking their storage limits first.
    Args:
        req (InitiateUploadRequest): The user's request details including agent ID, file name, and file size.
        request (Request): The incoming HTTP request.
    Returns: An upload ID and recommended chunk size.
    """
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
    What it does: Receives a piece (chunk) of a large file from the user and saves it.
    Args:
        upload_id (str): The upload session ID.
        chunk_index (int): The order of this piece.
        request (Request): The HTTP request.
        chunk (UploadFile): The file chunk data.
    Returns: A success message.
    """
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
    What it does: Finalizes a chunked file upload by joining it together and telling the system to process it.
    Args:
        req (CompleteUploadRequest): The request containing upload ID and filename.
        request (Request): The HTTP request.
        background_tasks (BackgroundTasks): FastAPIs tool for running slow tasks in the background.
    Returns: A confirmation message.
    """
    return await handle_complete_upload(req.upload_id, req.agent_id, req.filename, background_tasks)


@router.get("/api/documents/{doc_id}/view")
async def view_document(
    doc_id: str,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    What it does: Allows a user to view a document they uploaded by streaming it back to their browser.
    Args:
        doc_id (str): The ID of the document they want to look at.
        token (str, optional): An access token provided in the URL.
        authorization (str, optional): An access token provided in the headers.
    Returns: A streaming response of the file.
    """
    return await handle_view_document(doc_id, token if token else authorization)


@router.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    What it does: Uploads a single file (not in pieces) and starts processing it immediately.
    Args:
        background_tasks (BackgroundTasks): FastAPIs tool to run things later.
        file (UploadFile): The actual file being uploaded.
        agent_id (str): The ID of the agent learning from this file.
    Returns: A confirmation message.
    """
    return await handle_process_file(agent_id, file, background_tasks)


@router.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    What it does: Takes a website URL from the user and tells the system to scrape and process it.
    Args:
        req (URLRequest): The user's request with the URL.
        background_tasks (BackgroundTasks): FastAPIs tool to run things later.
    Returns: A confirmation message.
    """
    return await handle_process_url(req.agent_id, req.url, background_tasks)


@router.post("/process-connector")
async def process_connector(req: ConnectorRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: Fakes a connection to a third party tool like Slack or Google Drive for demo purposes.
    Args:
        req (ConnectorRequest): Details about which app to connect to.
    Returns: A success message showing connection established.
    """
    return await handle_process_connector(req.agent_id, req.connector_id)


@router.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: Asks the database for all documents uploaded to a specific agent.
    Args:
        agent_id (str): The ID of the agent we want to see files for.
    Returns: A list of documents.
    """
    return await handle_get_documents(agent_id)


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: Receives a request from the user to permanently delete a document.
    Args:
        doc_id (str): The ID of the document to throw away.
    Returns: A confirmation message.
    """
    return await handle_delete_document(doc_id)
