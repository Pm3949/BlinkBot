import logging
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from core.auth import get_current_user

from handlers.connector_handler import (
    handle_google_authorize,
    handle_google_callback,
    handle_google_token,
    handle_google_files,
    handle_google_import
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

class SyncRequest(BaseModel):
    agent_id: str

class GDriveImportRequest(BaseModel):
    agent_id: str
    files: list

@router.get("/google/authorize")
async def google_authorize(user_id: str):
    """
    What it does: HTTP endpoint to redirect the user to Google's OAuth 2.0 server.
    Args:
        user_id (str): The user ID.
    Returns: A redirect response to Google.
    """
    url = await handle_google_authorize(user_id)
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str, state: str):
    """
    What it does: HTTP endpoint where Google redirects back with an authorization code.
    Args:
        code (str): The OAuth code.
        state (str): The user ID state.
    Returns: A redirect to the frontend.
    """
    url = await handle_google_callback(code, state)
    return RedirectResponse(url)

@router.get("/google/token")
async def google_token(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to return the stored Google OAuth access token.
    Args:
        user_id (str): The user ID.
    Returns: The token information.
    """
    user_id = current_user["sub"]
    return await handle_google_token(user_id)

@router.get("/google/files")
async def google_files(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch the list of files in the user's Google Drive.
    Args:
        user_id (str): The user ID.
    Returns: A list of file metadata.
    """
    user_id = current_user["sub"]
    return await handle_google_files(user_id)

@router.post("/google/import")
async def google_import(req: GDriveImportRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create document entries and trigger background import.
    Args:
        req (GDriveImportRequest): The import payload.
        background_tasks (BackgroundTasks): The FastAPI background tasks instance.
    Returns: A success message.
    """
    data = req.dict()
    data["user_id"] = current_user["sub"]
    return await handle_google_import(data, background_tasks)
