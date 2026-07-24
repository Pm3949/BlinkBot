"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the backend business logic handler for managing external integrations,
specifically focusing on the Google Drive Connector in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads modules for environment variables (os), URL parsing (urllib.parse),
   async HTTP requests (httpx), temporary file handling, async controls, FastAPI errors,
   and database cursors.
2. Environment Configurations: Reads Google Client credentials and base redirection URLs
   from server environment parameters.
3. Google Auth Redirection (`handle_google_authorize`): Builds the authorization consent
   link so users can grant RAGMate read-only access to their Google Drive files.
4. Google Auth Verification (`handle_google_callback`): Receives the authorization code,
   exchanges it for persistent access and refresh tokens, and saves them in the database.
5. Credentials Retrieval (`handle_google_token`): Fetches saved token parameters.
6. Google Drive File Ingestion:
   - `handle_google_files`: Queries Google Drive files list, automatically executing
     refresh token logic if the access token has expired.
   - `background_gdrive_import` (background task): Downloads files, exports Google Docs to text,
     extracts text, chunks it, generates embeddings, and saves vectors in database tables.
   - `handle_google_import`: Main handler that registers document stubs and spawns 
     `background_gdrive_import` tasks asynchronously so the client doesn't block waiting for vectors.
"""

import os  # Read system environment parameters
import urllib.parse  # Encode variables into URL queries
import httpx  # Perform non-blocking async HTTP client requests (to Google APIs)
import tempfile  # Create local files on disk (purged after processing)
import asyncio  # Asynchronous thread execution controls
from fastapi import HTTPException  # Return clean HTTP error responses to client
from database import get_db_cursor_async  # Non-blocking async database cursors
from fastapi.concurrency import run_in_threadpool  # Run synchronous functions in an async threadpool
from db import connector_repository  # Database query repository for connectors

# Logger utility
from utils.logger import get_department_logger

# Scope department logger specifically to "knowledge_base"
logger = get_department_logger("knowledge_base")

# Read Client Credentials from Environment configurations
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
# The callback URI Google redirect client back to after authentication completes
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", f"{API_BASE_URL}/api/v1/connectors/google/callback")
FRONTEND_URL = os.environ.get("VITE_FRONTEND_URL", "http://localhost:5173")


async def handle_google_authorize(user_id: str):
    """
    Constructs the redirection URL to point users to Google's OAuth 2.0 consent window.
    Forces permission settings to 'drive.readonly' to protect user privacy.

    Parameters:
        user_id (str): The unique database UUID identifying the target user.

    Returns:
        str: Google OAuth consent redirection URL query.

    Exceptions Raised:
        HTTPException(500): Raised if GOOGLE_CLIENT_ID is not configured.
    """
    logger.info(f"Generating Google Drive authorization URL for user ID: {user_id}")
    if not GOOGLE_CLIENT_ID:
        logger.error("Google Drive Auth failed: GOOGLE_CLIENT_ID is not configured.")
        raise HTTPException(status_code=500, detail="Google Client ID not configured in backend.")
        
    # Request read-only permissions for Google Drive, along with email profile data
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "email",
        "profile"
    ]
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    # Construct query string options
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",                     # Requests refresh token to generate access tokens offline
        "prompt": "consent",                          # Forces consent screen layout to display every time
        "state": user_id                              # Pass user_id back in 'state' variable to verify user identity on callback
    }
    
    # URL encode query parameters
    target_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    logger.debug(f"Generated OAuth URL: {target_url}")
    return target_url


async def handle_google_callback(code: str, state: str):
    """
    Receives Google's code callback parameters.
    Exchanges the authorization code for access and refresh tokens, and saves them in the database.

    Parameters:
        code (str): The temporary authentication code returned by Google.
        state (str): The 'state' value containing the user ID.

    Returns:
        str: Frontend callback redirection URL string.

    Exceptions Raised:
        HTTPException(400): Raised if token exchange with Google fails.
        HTTPException(500): Raised if OAuth settings are missing or database saves crash.
    """
    user_id = state
    logger.info(f"Handling Google Drive OAuth callback for user ID: {user_id}")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth failed: client credentials not configured.")
        raise HTTPException(status_code=500, detail="Google OAuth not configured.")

    token_url = "https://oauth2.googleapis.com/token"
    # Form post payload to exchange authorization code for access tokens
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    logger.debug(f"Requesting tokens from: {token_url}")
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        token_data = response.json()

    # Raise error if token exchange fails
    if "error" in token_data:
        logger.error(f"Google OAuth Token Request failed: {token_data}")
        raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google.")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    logger.debug("Successfully retrieved tokens from Google.")

    try:
        # Save tokens in connector settings table
        logger.debug("Saving/updating Google OAuth tokens in database...")
        await connector_repository.upsert_google_token(user_id, access_token, refresh_token)
        logger.info(f"Google Drive integration successfully configured for user ID: {user_id}")
    except Exception as e:
        logger.error(f"Failed to save Google OAuth token for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error while saving token")

    # Redirect user back to frontend dashboard
    return f"{FRONTEND_URL}/knowledge?connection=success&provider=google"


async def handle_google_token(user_id: str):
    """
    Retrieves Google Drive API keys and access tokens for client authentication on the frontend.

    Parameters:
        user_id (str): The unique database UUID identifying the user.

    Returns:
        dict: A dictionary containing 'access_token', 'api_key', and 'client_id'.

    Exceptions Raised:
        HTTPException(400): Raised if user is not connected.
        HTTPException(500): Raised if API keys are missing on the server.
    """
    logger.info(f"Fetching Google Drive token parameters for user ID: {user_id}")
    try:
        # Fetch tokens from DB
        logger.debug("Querying Google OAuth tokens from database...")
        row = await connector_repository.get_google_token(user_id)
        if not row:
            logger.warning(f"Tokens not found. User {user_id} is not connected to Google Drive.")
            raise HTTPException(status_code=400, detail="Google Drive not connected.")
            
        # Get Drive API Key
        google_drive_api_key = os.environ.get("GOOGLE_DRIVE_API_KEY")
        if not google_drive_api_key:
            logger.error("Backend configuration error: GOOGLE_DRIVE_API_KEY not configured.")
            raise HTTPException(status_code=500, detail="Google API Key not configured in backend.")
            
        logger.info("Successfully retrieved credentials configuration.")
        return {
            "access_token": row[0],
            "api_key": google_drive_api_key,
            "client_id": GOOGLE_CLIENT_ID
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Google Drive credentials config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_google_files(user_id: str):
    """
    Fetches the list of files in a user's Google Drive.
    Filters files to include only PDFs, Text files, and Word Documents.
    Automatically refreshes expired access tokens.

    Parameters:
        user_id (str): The unique database UUID identifying the user.

    Returns:
        dict: A dictionary with a key "files" containing the list of files.

    Exceptions Raised:
        HTTPException(400): Raised if not connected or token expired.
        HTTPException(500): Raised for API failures.
    """
    logger.info(f"Listing Google Drive files for user ID: {user_id}")
    try:
        logger.debug("Querying Google OAuth token credentials...")
        token_row = await connector_repository.get_google_token(user_id)
        if not token_row:
            logger.warning(f"Files request rejected: User {user_id} is not connected to Google Drive.")
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        refresh_token = token_row[1]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        # Filter files to target document formats
        q = "mimeType = 'application/pdf' or mimeType = 'text/plain' or mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType = 'application/vnd.google-apps.document'"
        drive_url = f"https://www.googleapis.com/drive/v3/files?pageSize=30&q={urllib.parse.quote(q)}&fields=files(id,name,size,mimeType)"
        
        logger.debug("Requesting Google Drive files API...")
        async with httpx.AsyncClient() as client:
            resp = await client.get(drive_url, headers=headers)
            # If token expired (HTTP 401 Unauthorized), execute refresh token sequence
            if resp.status_code == 401 and refresh_token:
                logger.info("Access token expired. Attempting to refresh Google OAuth token...")
                token_url = "https://oauth2.googleapis.com/token"
                data = {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
                refresh_resp = await client.post(token_url, data=data)
                token_data = refresh_resp.json()
                
                if "access_token" in token_data:
                    access_token = token_data["access_token"]
                    logger.debug("Updating refreshed access token in database...")
                    # Save refreshed token to DB
                    await connector_repository.update_access_token_only(user_id, access_token)
                    
                    # Retry file list call using new credentials
                    headers = {"Authorization": f"Bearer {access_token}"}
                    resp = await client.get(drive_url, headers=headers)

            if resp.status_code != 200:
                logger.error(f"Google Drive API returned non-200 status: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=400, detail="Failed to fetch from Google Drive. Token might be expired.")
                
            drive_data = resp.json()
            files_list = drive_data.get("files", [])
            logger.info(f"Successfully retrieved {len(files_list)} files from Google Drive.")
            return {"files": files_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve files from Google Drive: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def background_gdrive_import(
    document_id: str,
    agent_id: str,
    file_id: str,
    filename: str,
    mime_type: str,
    access_token: str,
    refresh_token: str,
    user_id: str,
    strategy: str,
    embed_model: str
):
    """
    Performs background file downloads and document embedding tasks (RAG ingestion).
    - Downloads the file from Google Drive.
    - Exports Google Docs to plain text.
    - Extracts text from PDFs/Docs.
    - Chunks text based on workspace strategies.
    - Embeds chunks into vectors.
    - Inserts vectors into database, and updates status flags.

    This function runs in a background thread task to prevent blocking server boot.
    """
    logger.info(f"Starting background Google Drive file import task. Doc ID: {document_id} ('{filename}')")
    file_path = None
    try:
        from core.dependencies import UPLOAD_DIR
        from core.dependencies import rag_engine
        from core.security import encrypt_key
        
        dest_filename = f"[G-Drive] {filename}"
        file_path = UPLOAD_DIR / dest_filename
        
        # Google Docs require exporting to plain text, normal files are downloaded directly
        is_google_doc = mime_type.startswith("application/vnd.google-apps")
        
        if is_google_doc:
            target_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
            logger.debug(f"Target is a Google Doc. Configuring export url: {target_url}")
        else:
            target_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            logger.debug(f"Target is a binary file. Configuring media url: {target_url}")

        async def fetch_with_retry(url: str):
            """Downloads content from Google Drive, automatic token refreshing included."""
            nonlocal access_token
            current_headers = {"Authorization": f"Bearer {access_token}"}
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, headers=current_headers)
                if resp.status_code == 401 and refresh_token:
                    logger.info("Access token expired during import download. Refreshing token...")
                    token_url = "https://oauth2.googleapis.com/token"
                    data = {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    }
                    refresh_resp = await client.post(token_url, data=data)
                    token_data = refresh_resp.json()
                    
                    if "access_token" in token_data:
                        access_token = token_data["access_token"]
                        current_headers = {"Authorization": f"Bearer {access_token}"}
                        try:
                            await connector_repository.update_access_token_only(user_id, access_token)
                        except Exception as db_e:
                            logger.error(f"Failed to update token in DB: {db_e}")
                        
                        resp = await client.get(url, headers=current_headers)

                if resp.status_code != 200:
                    raise Exception(f"Failed to download from Drive: {resp.text}")
                return resp.content

        logger.debug("Downloading file payload from Google Drive...")
        file_bytes = await fetch_with_retry(target_url)
        
        if is_google_doc and not dest_filename.endswith(".txt"):
            dest_filename += ".txt"
            file_path = UPLOAD_DIR / dest_filename
            
        logger.debug(f"Saving downloaded content to disk: {file_path}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # 1. Extract text content
        logger.debug("Executing threadpool text extraction from the downloaded connector file...")
        raw_text = rag_engine.extract_text_from_file(str(file_path), filename)
        
        # 2. Slice text into chunks
        logger.debug(f"Partitioning text using chunking strategy: '{strategy}'...")
        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the content")

        # 3. Vectorize chunks
        logger.debug(f"Generating embeddings using model: '{embed_model}'...")
        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        # 4. Save vectors to DB
        logger.debug("Saving vectorized chunks in database document_embeddings table...")
        async with get_db_cursor_async(commit=True) as cursor:
            for text, vector in zip(chunks, vectors):
                # Encrypt text chunks before inserting into database
                encrypted_chunk = encrypt_key(text)
                await run_in_threadpool(
                    cursor.execute,
                    "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                    (document_id, encrypted_chunk, str(vector)),
                )

            # 5. Set status to 'completed'
            logger.debug("Updating document stub metadata status to 'completed'...")
            await run_in_threadpool(
                cursor.execute,
                "UPDATE documents SET filename = %s, status = 'completed', file_size_bytes = %s WHERE id = %s", 
                (dest_filename, len(raw_text.encode('utf-8')), document_id)
            )

        logger.info(f"✅ Background GDrive Sync completed successfully for doc ID: {document_id}")

    except Exception as e:
        # Catch ingestion failures, update document status to 'failed', and clean up temporary files
        logger.error(f"Background GDrive Sync failed for doc ID {document_id}: {str(e)}", exc_info=True)
        try:
            async with get_db_cursor_async(commit=True) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "UPDATE documents SET status = 'failed' WHERE id = %s",
                    (document_id,),
                )
        except Exception as db_err:
            logger.error(f"Failed to set document state failed: {db_err}")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


async def handle_google_import(payload: dict, background_tasks):
    """
    Spawns background tasks to import and ingest files from Google Drive.
    Fleshes out agent settings, grabs OAuth tokens, registers document stubs in DB,
    and queues imports.

    Parameters:
        payload (dict): Ingestion options.
        background_tasks (BackgroundTasks): FastAPI BackgroundTasks scheduler.

    Returns:
        dict: Ingestion status and list of queued files.

    Exceptions Raised:
        HTTPException(404): Raised if agent not found.
        HTTPException(400): Raised if not connected to Google Drive.
        HTTPException(500): Raised for pipeline failures.
    """
    logger.info(f"Handling Google Drive files import request for agent ID: {payload.get('agent_id')}")
    try:
        logger.debug("Querying agent embedding configurations...")
        agent_row = await connector_repository.get_agent_embed_info(payload.get("agent_id"))
        if not agent_row:
            logger.warning("Import aborted: Agent not found.")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        embed_model = agent_row[0] if agent_row[0] else "all-MiniLM-L6-v2"
        strategy = agent_row[1] if agent_row[1] else "sentence"

        logger.debug("Fetching OAuth tokens...")
        token_row = await connector_repository.get_google_token(payload.get("user_id"))
        if not token_row:
            logger.warning("Import aborted: Google Drive connection is missing.")
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        refresh_token = token_row[1]

        imported_files = []
        for file_info in payload.get("files", []):
            file_id = file_info.get("id")
            filename = file_info.get("name", "Untitled Drive File")
            mime_type = file_info.get("mimeType", "")
            
            dest_filename = f"[G-Drive] {filename}"
            # Register document stub to show 'processing' status on frontend UI
            logger.debug(f"Creating stub index for file '{filename}'...")
            document_id = await connector_repository.create_document_stub(payload.get("agent_id"), dest_filename)
            
            # Spin up background ingestion
            logger.info(f"Scheduling background import task for file: '{filename}' (ID: {file_id})")
            background_tasks.add_task(
                background_gdrive_import,
                document_id,
                payload.get("agent_id"),
                file_id,
                filename,
                mime_type,
                access_token,
                refresh_token,
                payload.get("user_id"),
                strategy,
                embed_model
            )
            imported_files.append(filename)
            
        logger.info(f"Successfully scheduled {len(imported_files)} files for ingestion.")
        return {"message": f"Successfully queued {len(imported_files)} files for embedding.", "files": imported_files}
    except Exception as e:
        logger.error(f"Failed to initiate Google Drive import: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
