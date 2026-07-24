"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all External Connectors (specifically
Google Drive integration) in the RAGMate backend. It maps incoming HTTP REST requests
directly to the underlying business logic executors defined inside the connector handler
modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard logging controllers, FastAPI routing modules and responses,
   Pydantic schemas, and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter with prefix '/api/v1/connectors' 
   and grouping tags.
3. Input Payload Validation Schemas:
   - `SyncRequest`: Validates payload for manual connector sync queries.
   - `GDriveImportRequest`: Validates payload when initiating document imports from Google Drive.
4. HTTP Routes:
   - GET `/google/authorize`: Initiates Google OAuth consent screen redirects.
   - GET `/google/callback`: Receives authentication codes from Google.
   - GET `/google/token`: Fetches stored access tokens.
   - GET `/google/files`: Queries lists of files in Google Drive.
   - POST `/google/import`: Triggers background import tasks.
"""

import logging  # Import python logging library
from fastapi import APIRouter, BackgroundTasks, Depends  # FastAPI APIRouter, background task schedulers, and Depends injection
from fastapi.responses import RedirectResponse  # HTTP Redirection responses
from pydantic import BaseModel  # Pydantic BaseModels for payload validations
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import connector logic handlers
from handlers.connector_handler import (
    handle_google_authorize,
    handle_google_callback,
    handle_google_token,
    handle_google_files,
    handle_google_import
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for connector endpoints, prefixing all routes with '/api/v1/connectors'
router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

class SyncRequest(BaseModel):
    """
    Validates payload options for triggering manual syncs.
    """
    agent_id: str                              # AI Agent UUID to sync

class GDriveImportRequest(BaseModel):
    """
    Validates payload options for importing Google Drive files.
    """
    agent_id: str                              # Target AI Agent UUID
    files: list                                # List of file objects containing 'id' and 'name' parameters


@router.get("/google/authorize")
async def google_authorize(user_id: str):
    """
    HTTP GET endpoint initiating Google OAuth 2.0 redirection.
    Publicly accessible to trigger authorizations.

    Parameters:
        user_id (str): The unique database user UUID.

    Returns:
        RedirectResponse: Directs browser to Google's OAuth consent screen.

    Exceptions Raised:
        HTTPException(500): Raised if OAuth clients are missing in backend configuration.
    """
    # Fetch redirect URL mapping user ID state parameters
    url = await handle_google_authorize(user_id)
    return RedirectResponse(url)  # Return Redirect Response (HTTP 307 Temporary Redirect)


@router.get("/google/callback")
async def google_callback(code: str, state: str):
    """
    HTTP GET endpoint that Google redirects back to after user consent.

    Parameters:
        code (str): Google's authorization code.
        state (str): User ID verification state.

    Returns:
        RedirectResponse: Directs client browser back to frontend settings.

    Exceptions Raised:
        HTTPException(500): Raised if token exchange transactions crash.
    """
    # Exchange code for access tokens
    url = await handle_google_callback(code, state)
    return RedirectResponse(url)  # Redirect user to frontend connection status callbacks page


@router.get("/google/token")
async def google_token(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint retrieving stored access tokens.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Stored credentials details (API keys, client IDs, access tokens).

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(400): Raised if not connected.
        HTTPException(500): Raised if queries crash.
    """
    user_id = current_user["sub"]  # Extract User ID from JWT
    return await handle_google_token(user_id)  # Route task execution to handlers layer


@router.get("/google/files")
async def google_files(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch files list in Google Drive.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing lists of file details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(400): Raised if not connected.
        HTTPException(500): Raised if queries fail.
    """
    user_id = current_user["sub"]  # Extract User ID from JWT
    return await handle_google_files(user_id)  # Route task execution to handlers layer


@router.post("/google/import")
async def google_import(req: GDriveImportRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint starting Google Drive files import.
    Queues task execution in background thread pools.

    Parameters:
        req (GDriveImportRequest): The pydantic-validated request payload.
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Confirmation message containing the queued files list.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if ingestion processes crash.
    """
    data = req.dict()  # Convert Pydantic request structure to dictionary
    data["user_id"] = current_user["sub"]  # Inject user ID subject from JWT
    # Route execution to handlers layer, passing background task queues
    return await handle_google_import(data, background_tasks)
