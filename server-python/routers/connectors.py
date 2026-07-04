import os
import urllib.parse
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
import httpx
from database import get_db_connection
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# Ensure these are set in your .env file
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# This must exactly match the authorized redirect URI in Google Cloud Console
# Example: http://localhost:8000/api/v1/connectors/google/callback
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", f"{API_BASE_URL}/api/v1/connectors/google/callback")

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
        "email",
        "profile"
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

@router.get("/google/token")
async def google_token(user_id: str):
    """
    Returns the stored Google OAuth access token and the backend's Google API Key
    so the frontend can initialize the native Google Picker.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Google Drive not connected.")
            
        google_drive_api_key = os.environ.get("GOOGLE_DRIVE_API_KEY")
        if not google_drive_api_key:
            raise HTTPException(status_code=500, detail="Google API Key not configured in backend.")
            
        return {
            "access_token": row[0],
            "api_key": google_drive_api_key,
            "client_id": GOOGLE_CLIENT_ID
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch Google Drive token")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class SyncRequest(BaseModel):
    agent_id: str
    user_id: str

@router.get("/google/files")
async def google_files(user_id: str):
    """
    Fetch the list of files in the user's Google Drive.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get token
        cursor.execute("SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        
        # Fetch files from Google Drive API
        headers = {"Authorization": f"Bearer {access_token}"}
        # Fetching PDFs, Docx, Text, and Google Docs
        q = "mimeType = 'application/pdf' or mimeType = 'text/plain' or mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType = 'application/vnd.google-apps.document'"
        drive_url = f"https://www.googleapis.com/drive/v3/files?pageSize=30&q={urllib.parse.quote(q)}&fields=files(id,name,size,mimeType)"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(drive_url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch from Google Drive. Token might be expired.")
                
            drive_data = resp.json()
            return {"files": drive_data.get("files", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch Google Drive files")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class GDriveImportRequest(BaseModel):
    agent_id: str
    user_id: str
    files: list # list of dicts: {"id": str, "name": str, "mimeType": str}

import tempfile
import asyncio
from core.dependencies import rag_engine
from core.security import encrypt_key
from fastapi import BackgroundTasks

def background_gdrive_import(
    document_id: str,
    agent_id: str,
    file_id: str,
    filename: str,
    mime_type: str,
    access_token: str,
    strategy: str,
    embed_model: str
):
    conn = None
    cursor = None
    file_path = None
    try:
        from core.dependencies import UPLOAD_DIR
        dest_filename = f"[G-Drive] {filename}"
        file_path = UPLOAD_DIR / dest_filename
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Determine if it's a Google Doc that needs exporting or a standard file
        is_google_doc = mime_type.startswith("application/vnd.google-apps")
        
        if is_google_doc:
            # Export as plain text
            export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
            async def fetch_doc():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(export_url, headers=headers)
                    if resp.status_code != 200:
                        raise Exception(f"Failed to export Google Doc: {resp.text}")
                    return resp.content
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            file_bytes = loop.run_until_complete(fetch_doc())
            # Save permanently to UPLOAD_DIR as .txt so it can be previewed/accessed
            # Force .txt suffix if not present
            if not dest_filename.endswith(".txt"):
                dest_filename += ".txt"
                file_path = UPLOAD_DIR / dest_filename
                
            with open(file_path, "wb") as f:
                f.write(file_bytes)
        else:
            # Download directly
            download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            async def download_file():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(download_url, headers=headers)
                    if resp.status_code != 200:
                        raise Exception(f"Failed to download file from Drive: {resp.text}")
                    return resp.content
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            file_bytes = loop.run_until_complete(download_file())
            with open(file_path, "wb") as f:
                f.write(file_bytes)

        # Now extract text from the downloaded file using the RAG engine
        raw_text = rag_engine.extract_text_from_file(str(file_path), filename)
        
        # Run chunking & embedding
        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the content")

        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        conn = get_db_connection()
        cursor = conn.cursor()

        for text, vector in zip(chunks, vectors):
            encrypted_chunk = encrypt_key(text)
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, encrypted_chunk, str(vector)),
            )

        # Update filename in case we changed it (like appending .txt) and set status
        cursor.execute(
            "UPDATE documents SET filename = %s, status = 'completed', file_size_bytes = %s WHERE id = %s", 
            (dest_filename, len(raw_text.encode('utf-8')), document_id)
        )
        conn.commit()
        logger.info(f"✅ Background GDrive Sync completed for doc id: {document_id}")

    except Exception as e:
        logger.exception(f"Background GDrive Sync failed for doc id {document_id}")
        if conn and cursor:
            try:
                cursor.execute(
                    "UPDATE documents SET status = 'failed' WHERE id = %s",
                    (document_id,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
        # Clean up the file if it failed
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.post("/google/import")
async def google_import(req: GDriveImportRequest, background_tasks: BackgroundTasks):
    """
    Create a document entry and trigger background download and embedding.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch agent settings for chunking and embedding configuration
        cursor.execute(
            "SELECT embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (req.agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        embed_model = agent_row[0] if agent_row[0] else "all-MiniLM-L6-v2"
        strategy = agent_row[1] if agent_row[1] else "sentence"

        # Get access token
        cursor.execute("SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (req.user_id,))
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]

        imported_files = []
        for file_info in req.files:
            file_id = file_info.get("id")
            filename = file_info.get("name", "Untitled Drive File")
            mime_type = file_info.get("mimeType", "")
            
            # Create standard processing document
            cursor.execute(
                "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', 0) RETURNING id;",
                (req.agent_id, f"[G-Drive] {filename}",)
            )
            document_id = cursor.fetchone()[0]
            conn.commit()
            
            background_tasks.add_task(
                background_gdrive_import,
                document_id,
                req.agent_id,
                file_id,
                filename,
                mime_type,
                access_token,
                strategy,
                embed_model
            )
            imported_files.append(filename)
            
        return {"message": f"Successfully queued {len(imported_files)} files for embedding.", "files": imported_files}
    except Exception as e:
        logger.exception("Failed to initiate Google Drive import")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
