import os
import logging
import urllib.parse
import httpx
import tempfile
import asyncio
from fastapi import HTTPException
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from database_layer import connector_repository

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", f"{API_BASE_URL}/api/v1/connectors/google/callback")
FRONTEND_URL = os.environ.get("VITE_FRONTEND_URL", "http://localhost:5173")


async def handle_google_authorize(user_id: str):
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
        "state": user_id 
    }
    
    return f"{auth_url}?{urllib.parse.urlencode(params)}"


async def handle_google_callback(code: str, state: str):
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
    refresh_token = token_data.get("refresh_token")

    try:
        await connector_repository.upsert_google_token(user_id, access_token, refresh_token)
    except Exception as e:
        logger.exception("Failed to save OAuth token")
        raise HTTPException(status_code=500, detail="Database error while saving token")

    return f"{FRONTEND_URL}/knowledge?connection=success&provider=google"


async def handle_google_token(user_id: str):
    try:
        row = await connector_repository.get_google_token(user_id)
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


async def handle_google_files(user_id: str):
    try:
        token_row = await connector_repository.get_google_token(user_id)
        if not token_row:
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        refresh_token = token_row[1]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        q = "mimeType = 'application/pdf' or mimeType = 'text/plain' or mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType = 'application/vnd.google-apps.document'"
        drive_url = f"https://www.googleapis.com/drive/v3/files?pageSize=30&q={urllib.parse.quote(q)}&fields=files(id,name,size,mimeType)"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(drive_url, headers=headers)
            if resp.status_code == 401 and refresh_token:
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
                    await connector_repository.update_access_token_only(user_id, access_token)
                    
                    headers = {"Authorization": f"Bearer {access_token}"}
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
    file_path = None
    try:
        from core.dependencies import UPLOAD_DIR
        from core.dependencies import rag_engine
        from core.security import encrypt_key
        
        dest_filename = f"[G-Drive] {filename}"
        file_path = UPLOAD_DIR / dest_filename
        
        is_google_doc = mime_type.startswith("application/vnd.google-apps")
        
        if is_google_doc:
            target_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
        else:
            target_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

        async def fetch_with_retry(url: str):
            nonlocal access_token
            current_headers = {"Authorization": f"Bearer {access_token}"}
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, headers=current_headers)
                if resp.status_code == 401 and refresh_token:
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
                        except Exception as e:
                            logger.error(f"Failed to update token in DB: {e}")
                        
                        resp = await client.get(url, headers=current_headers)

                if resp.status_code != 200:
                    raise Exception(f"Failed to download from Drive: {resp.text}")
                return resp.content

        file_bytes = await fetch_with_retry(target_url)
        
        if is_google_doc and not dest_filename.endswith(".txt"):
            dest_filename += ".txt"
            file_path = UPLOAD_DIR / dest_filename
            
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        raw_text = rag_engine.extract_text_from_file(str(file_path), filename)
        
        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the content")

        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        async with get_db_cursor_async(commit=True) as cursor:
            for text, vector in zip(chunks, vectors):
                encrypted_chunk = encrypt_key(text)
                await run_in_threadpool(
                    cursor.execute,
                    "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                    (document_id, encrypted_chunk, str(vector)),
                )

            await run_in_threadpool(
                cursor.execute,
                "UPDATE documents SET filename = %s, status = 'completed', file_size_bytes = %s WHERE id = %s", 
                (dest_filename, len(raw_text.encode('utf-8')), document_id)
            )

        logger.info(f"✅ Background GDrive Sync completed for doc id: {document_id}")

    except Exception as e:
        logger.exception(f"Background GDrive Sync failed for doc id {document_id}")
        try:
            async with get_db_cursor_async(commit=True) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "UPDATE documents SET status = 'failed' WHERE id = %s",
                    (document_id,),
                )
        except Exception:
            pass
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


async def handle_google_import(payload: dict, background_tasks):
    try:
        agent_row = await connector_repository.get_agent_embed_info(payload.get("agent_id"))
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        embed_model = agent_row[0] if agent_row[0] else "all-MiniLM-L6-v2"
        strategy = agent_row[1] if agent_row[1] else "sentence"

        token_row = await connector_repository.get_google_token(payload.get("user_id"))
        if not token_row:
            raise HTTPException(status_code=400, detail="Not connected to Google Drive")
            
        access_token = token_row[0]
        refresh_token = token_row[1]

        imported_files = []
        for file_info in payload.get("files", []):
            file_id = file_info.get("id")
            filename = file_info.get("name", "Untitled Drive File")
            mime_type = file_info.get("mimeType", "")
            
            dest_filename = f"[G-Drive] {filename}"
            document_id = await connector_repository.create_document_stub(payload.get("agent_id"), dest_filename)
            
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
            
        return {"message": f"Successfully queued {len(imported_files)} files for embedding.", "files": imported_files}
    except Exception as e:
        logger.exception("Failed to initiate Google Drive import")
        raise HTTPException(status_code=500, detail=str(e))
