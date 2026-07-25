"""
================================================================================
THIRD-PARTY CONNECTORS ROUTER LAYER (connectors.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for external storage connectors
(specifically Google Drive integrations). It manages:
1. Google OAuth 2.0 authorization redirects: Directs users to Google's consent screen.
2. Callback processing: Receives OAuth tokens, associates them with the user, and redirects back to the UI.
3. Access Token retrieval: Checks if a valid Google Drive integration exists.
4. Google Drive directory listings: Lists files inside the user's Google Drive.
5. Ingestion imports: Downloads selected files from Google Drive in the background
   and imports them into the RAG engine's database context.

BACKGROUND CONCURRENCY PATTERNS:
- File imports from Google Drive can be slow due to network latency and parsing overhead.
- In `google_import`, the router uses FastAPI's `BackgroundTasks` queue to execute imports asynchronously.
  This allows the API to return a quick success response while files are imported in the background.
"""

import logging
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from core.auth import get_current_user

# Import the Google Drive connector handlers.
from handlers.connector_handler import (
    handle_google_authorize,
    handle_google_callback,
    handle_google_token,
    handle_google_files,
    handle_google_import
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tag categories and router prefixes.
router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class SyncRequest(BaseModel):
    """
    Validation schema for triggering a connector sync.
    """
    agent_id: str # Target AI agent UUID


class GDriveImportRequest(BaseModel):
    """
    Validation schema for importing files from Google Drive.
    """
    agent_id: str # Target AI agent UUID to link files to
    files: list # List of file metadata objects selected for import


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/google/authorize")
async def google_authorize(user_id: str):
    """
    Redirects the user to Google's OAuth 2.0 server.

    Purpose:
        Constructs the Google Drive OAuth authorization request URL.

    Parameters:
        user_id (str): The unique UUID of the user establishing the connection.

    Returns:
        RedirectResponse: A redirect to Google's OAuth consent screen.

    Side Effects / State Changes:
        - Redirects the user's browser.

    Errors / Exceptions:
        - None.
    """
    # Generate the authorization URL using the handler.
    url = await handle_google_authorize(user_id)
    # Redirect the client's browser.
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, state: str):
    """
    Handles Google OAuth callbacks.

    Purpose:
        Exchanges the authorization code for access and refresh tokens,
        stores them in the database, and redirects back to the UI dashboard.

    Parameters:
        code (str): The Google OAuth authorization code.
        state (str): Contains the user's UUID to link the tokens to.

    Returns:
        RedirectResponse: A redirect to the frontend settings page.

    Side Effects / State Changes:
        - Writes or updates Google OAuth tokens in the `user_connectors` table.

    Errors / Exceptions:
        - Raises 400 Bad Request if the authorization exchange fails.
    """
    # Exchange the code and get the frontend redirect URL.
    url = await handle_google_callback(code, state)
    # Redirect the user to the frontend.
    return RedirectResponse(url)


@router.get("/google/token")
async def google_token(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the user's stored Google Drive OAuth access token.

    Purpose:
        Checks if a Google Drive connector is configured and active.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Token details containing access tokens or integration status flags.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Retrieve the token via the handler.
    return await handle_google_token(user_id)


@router.get("/google/files")
async def google_files(current_user: dict = Depends(get_current_user)):
    """
    Lists the files in the user's Google Drive.

    Purpose:
        Fetches file metadata (titles, IDs, sizes) to render a file picker in the UI.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Google Drive file metadata items.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 on authentication failures.
        - Raises 400 if Google Drive access is revoked or token exchange fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Retrieve files via the handler.
    return await handle_google_files(user_id)


@router.post("/google/import")
async def google_import(req: GDriveImportRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Imports selected files from Google Drive.

    Purpose:
        Saves document records to the database and schedules background tasks
        to download and parse the files.

    Parameters:
        req (GDriveImportRequest): Contains the target agent ID and selected file listings.
        background_tasks (BackgroundTasks): FastAPI's background tasks queue.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Creates placeholder rows in the `documents` table.
        - Schedules background file downloads and parsing.

    Errors / Exceptions:
        - Raises 401/403 on authorization issues.
        - Raises 400 if configurations are invalid.
    """
    # Convert Pydantic request attributes to a dictionary.
    data = req.dict()
    # Inject the user's UUID.
    data["user_id"] = current_user["sub"]
    # Trigger the import task asynchronously.
    return await handle_google_import(data, background_tasks)

