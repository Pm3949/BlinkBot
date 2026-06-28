import os
import urllib.parse
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
import httpx
from database import get_db_connection
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connectors"])

# Ensure these are set in your .env file
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# This must exactly match the authorized redirect URI in Google Cloud Console
# Example: http://localhost:8000/api/v1/connectors/google/callback
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/connectors/google/callback")

# ==========================================
# GOOGLE DRIVE OAUTH
# ==========================================

@router.get("/google/authorize")
async def google_authorize(user_id: str):
    """
    Step 1: Redirects the user to Google's OAuth 2.0 server.
    We pass the `user_id` as the state so we know who logged in during the callback.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured in backend.")
        
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/userinfo.email"
    ]
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id # Using user_id as state to map it back in callback
    }
    
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, state: str):
    """
    Step 2: Google redirects here with an authorization `code`.
    We exchange the code for an access token and refresh token, and save it to the DB.
    """
    user_id = state
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured.")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        token_data = response.json()

    if "error" in token_data:
        logger.error(f"Google OAuth Error: {token_data}")
        raise HTTPException(status_code=400, detail="Failed to retrieve access token from Google.")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token") # Note: Only provided on first auth or if prompt=consent
    expires_in = token_data.get("expires_in", 3600)

    # Save to database
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT id FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update
            cursor.execute(
                "UPDATE oauth_connections SET access_token = %s, refresh_token = COALESCE(%s, refresh_token), updated_at = NOW() WHERE id = %s",
                (access_token, refresh_token, existing[0])
            )
        else:
            # Insert
            cursor.execute(
                "INSERT INTO oauth_connections (user_id, provider, access_token, refresh_token) VALUES (%s, 'google', %s, %s)",
                (user_id, access_token, refresh_token)
            )
        conn.commit()
    except Exception as e:
        logger.exception("Failed to save OAuth token")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Database error while saving token")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Redirect back to frontend
    FRONTEND_URL = os.environ.get("VITE_FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(f"{FRONTEND_URL}/knowledge?connection=success&provider=google")

class SyncRequest(BaseModel):
    agent_id: str
    user_id: str

@router.post("/google/sync")
async def google_sync(req: SyncRequest):
    """
    Step 3: Perform a real sync from Google Drive using the stored access token.
    For this demo, we'll fetch the names of recent files from Drive to prove it works.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get token
        cursor.execute("SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (req.user_id,))
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        
        # Fetch files from Google Drive API
        headers = {"Authorization": f"Bearer {access_token}"}
        # Get just 5 most recent files for the demo to avoid blowing up the DB
        drive_url = "https://www.googleapis.com/drive/v3/files?pageSize=5&fields=files(id,name,size,mimeType)"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(drive_url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch from Google Drive. Token might be expired.")
                
            drive_data = resp.json()
            files = drive_data.get("files", [])
            
            if not files:
                return {"message": "Google Drive connected, but no files found."}
                
            inserted_count = 0
            for f in files:
                filename = f.get('name', 'Untitled Drive File')
                # Rough estimate of size or default to 1KB
                size = int(f.get('size', 1024))
                
                cursor.execute(
                    "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'completed', %s)",
                    (req.agent_id, f"[G-Drive] {filename}", size)
                )
                inserted_count += 1
                
        conn.commit()
        return {"message": f"Successfully synced {inserted_count} files from Google Drive!"}
    except Exception as e:
        logger.exception("Failed to sync Google Drive")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
