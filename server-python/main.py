"""
Main Application Entrypoint.
Responsibility: Bootstraps the FastAPI application, configures CORS, mounts all 
the individual feature routers, sets up global middleware/exception handlers, 
and manages background tasks (like data cleanup). 
"""
import os
import tempfile
import logging

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_db_connection

from fastapi.staticfiles import StaticFiles
from core.dependencies import UPLOAD_DIR

# Import routers (These are like sub-applications handling specific feature sets)
from routers import documents, analytics, admin, billing, chat, chat_history, workspaces, agents, chatbots, settings, feedback, notifications, meta_agent, demo, connectors

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

app = FastAPI(title="Custom BlinkBot Backend")

# Initialize Groq client for Speech-to-Text capabilities
try:
    groq_client = Groq()
except Exception as e:
    logger.warning(f"Groq client initialization failed: {e}")
    groq_client = None

# ==========================================
# CORS CONFIGURATION (Cross-Origin Resource Sharing)
# ==========================================
# Browsers block frontend apps from calling APIs on different domains for security.
# We must explicitly list the URLs allowed to talk to this backend.

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
admin_url = os.getenv("ADMIN_URL", "http://localhost:5174")

# Split by comma if multiple URLs are provided, and strip whitespace
allow_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url != "*" else ["*"]
admin_origins = [url.strip() for url in admin_url.split(",")] if admin_url != "*" else ["*"]

if "*" in allow_origins or "*" in admin_origins:
    allow_origins = ["*"]
else:
    allow_origins.extend(admin_origins)
    # Always allow local development ports
    allow_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"])

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class PublicCORSMiddleware(BaseHTTPMiddleware):
    """
    Custom Middleware for Public Widget API Endpoints.
    Why? The chat widget needs to be embeddable on ANY website, not just our frontend.
    This intercepts requests to `/api/widget` and `/api/v1` and injects permissive CORS headers (*).
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/widget") or request.url.path.startswith("/api/v1"):
            # Handle Preflight requests (OPTIONS) which browsers send before the actual request
            if request.method == "OPTIONS":
                return Response(status_code=200, headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                })
            # Let the actual request process, then attach the permissive header to the response
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        # If it's a normal API request, just pass it through to the standard CORSMiddleware
        return await call_next(request)

app.add_middleware(PublicCORSMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    # If we allow all origins (*), we cannot allow credentials (cookies/sessions) for security reasons
    allow_credentials=False if "*" in allow_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import documents, analytics, admin, billing, chat, chat_history, workspaces, agents, chatbots, settings, feedback, notifications, meta_agent, demo, auth
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# ==========================================
# MOUNT ROUTERS
# ==========================================
# Attach all the feature-specific endpoints to the main app instance.
app.include_router(documents.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(chat.router)
app.include_router(chat_history.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(chatbots.router)
app.include_router(settings.router)
app.include_router(feedback.router)
app.include_router(notifications.router)
app.include_router(meta_agent.router)
app.include_router(demo.router)
app.include_router(auth.router)
app.include_router(connectors.router)

# ==========================================
# RATE LIMITING & STATIC FILES
# ==========================================
# Configure Rate Limiter (prevents spam/DDoS by limiting requests per IP/User)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount uploads directory so files (like user avatars or document previews) can be served directly via URL
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ==========================================
# UTILITY ENDPOINTS (TTS & STT)
# ==========================================

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

@app.post("/api/tts")
async def generate_tts(req: TTSRequest):
    """
    Text-to-Speech Generation using Google TTS.
    Data Flow: Text -> gTTS Engine -> In-Memory Byte Stream -> HTTP Streaming Response
    """
    try:
        tts = gTTS(text=req.text, lang=req.language, slow=False)
        # We use a BytesIO stream instead of saving to a physical file to save disk I/O and speed up the response
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0) # Reset stream pointer to the beginning before sending
        return StreamingResponse(fp, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = Form(None)):
    """
    Speech-to-Text Transcription using Groq's Whisper API.
    """
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client is not configured")
        
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format")
        
    # Edge Case Handled: Groq's API requires a physical file path or a proper file object. 
    # We save the incoming upload to a temporary file, process it, and guarantee its deletion in the `finally` block.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name
        
    try:
        with open(temp_audio_path, "rb") as f:
            kwargs = {
                "file": (file.filename, f.read()),
                "model": "whisper-large-v3"
            }
            if language and language != "auto":
                kwargs["language"] = language
                
            transcription = groq_client.audio.transcriptions.create(**kwargs)
        return {"text": transcription.text}
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Crucial: Always clean up temporary files to prevent disk space exhaustion over time.
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# ==========================================
# BACKGROUND TASKS (CRON JOBS)
# ==========================================

def cleanup_old_chat_data():
    """
    Periodic task to maintain database hygiene and comply with data retention policies.
    Deletes any chat sessions older than 30 days.
    """
    logger.info("Running automatic cleanup of old chat data (>30 days)")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE created_at < NOW() - INTERVAL '30 days'")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to cleanup old chat data: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Use APScheduler to run the cleanup task in the background
scheduler = BackgroundScheduler()
# Run daily at midnight
scheduler.add_job(cleanup_old_chat_data, 'cron', hour=0, minute=0)

# Hook the scheduler into FastAPI's lifecycle events
@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Modular BlinkBot Server on Port 8000...")
    # reload=True is useful for development, auto-restarting the server on file changes.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
