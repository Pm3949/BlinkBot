"""
================================================================================
FASTAPI BOOTSTRAPPER - AI ENGINE (main_ai_engine.py)
================================================================================
"""

import os
import tempfile
from contextlib import asynccontextmanager
from utils.logger import get_department_logger, cleanup_department_loggers
from dotenv import load_dotenv

# Load local system environment variables.
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from io import BytesIO
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from fastapi.staticfiles import StaticFiles
from core.dependencies import UPLOAD_DIR
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool

# Import AI engine routers.
from api import (
    documents, chat, chatbots, notifications, connectors, meta_agent
)

# Set up module logger.
logger = get_department_logger("system")

# Initialize AI Engine FastAPI application.
app = FastAPI(title="BlinkBot AI & Real-Time Engine")

# Initialize the Groq API client for transcription features.
try:
    groq_client = Groq()
except Exception as e:
    logger.warning(f"Groq client initialization failed: {e}")
    groq_client = None

# CORS middleware configurations
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
admin_url = os.getenv("ADMIN_URL", "http://localhost:5174")

allow_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url != "*" else ["*"]
admin_origins = [url.strip() for url in admin_url.split(",")] if admin_url != "*" else ["*"]

if "*" in allow_origins or "*" in admin_origins:
    allow_origins = ["*"]
else:
    allow_origins.extend(admin_origins)
    allow_origins.extend([
        "http://localhost:5173", "http://127.0.0.1:5173", 
        "http://localhost:5174", "http://127.0.0.1:5174"
    ])


class PublicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            request.url.path.startswith("/api/widget") 
            or request.url.path.startswith("/api/v1") 
            or request.url.path.startswith("/api/chatbots/")
            or request.url.path == "/api/tts"
            or request.url.path == "/stt"
        ):
            if request.method == "OPTIONS":
                return Response(status_code=200, headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                })
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        return await call_next(request)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "-"
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
            
        user_id = "-"
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            try:
                from core.auth import JWT_SECRET, ALGORITHM
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
                user_id = payload.get("sub", "-")
            except Exception:
                pass

        from utils.logger import user_id_var, client_ip_var
        token_user = user_id_var.set(user_id)
        token_ip = client_ip_var.set(client_ip)
        
        try:
            response = await call_next(request)
            return response
        finally:
            user_id_var.reset(token_user)
            client_ip_var.reset(token_ip)


# Register middlewares in reverse order of execution.
app.add_middleware(LoggingContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False if "*" in allow_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PublicCORSMiddleware)


# ==========================================
# MOUNT AI ENGINE ROUTERS
# ==========================================
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(chatbots.router)
app.include_router(notifications.router)
app.include_router(connectors.router)
app.include_router(meta_agent.router)

# Mount the static uploads directory to serve files directly.
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ==========================================
# UTILITY ENDPOINTS (TTS & STT)
# ==========================================
class TTSRequest(BaseModel):
    text: str
    language: str = "en"


@app.post("/api/tts")
async def generate_tts(req: TTSRequest) -> StreamingResponse:
    try:
        tts = gTTS(text=req.text, lang=req.language, slow=False)
        fp = BytesIO()
        await run_in_threadpool(tts.write_to_fp, fp)
        fp.seek(0)
        return StreamingResponse(fp, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = Form(None)) -> dict:
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client is not configured")
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format")
        
    file_bytes = await file.read()
    temp_audio_fd, temp_audio_path = tempfile.mkstemp(suffix=".webm")
    
    def write_temp_file():
        with os.fdopen(temp_audio_fd, "wb") as temp_audio:
            temp_audio.write(file_bytes)
            
    await run_in_threadpool(write_temp_file)
        
    try:
        def run_transcription():
            with open(temp_audio_path, "rb") as f:
                kwargs = {
                    "file": (file.filename, f.read()),
                    "model": "whisper-large-v3"
                }
                if language and language != "auto":
                    kwargs["language"] = language
                return groq_client.audio.transcriptions.create(**kwargs)
                
        transcription = await run_in_threadpool(run_transcription)
        return {"text": transcription.text}
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        def clean_temp_file():
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        await run_in_threadpool(clean_temp_file)


# ==========================================
# APPLICATION LIFECYCLE MANAGEMENT
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("logs", exist_ok=True)
    
    # Pre-load embedding and reranking models in a background thread.
    try:
        from core.dependencies import warm_up_models_background
        warm_up_models_background()
    except Exception as e:
        logger.error(f"Failed to trigger model pre-loading in background: {e}")

    # Auto-resume interrupted document ingestion tasks.
    try:
        from handlers.document_processor import resume_interrupted_uploads
        await resume_interrupted_uploads()
    except Exception as e:
        logger.error(f"Failed to resume interrupted uploads on startup: {e}")

    yield

    # Shutdown
    cleanup_department_loggers()
    if os.path.exists("logs"):
        import shutil
        shutil.rmtree("logs", ignore_errors=True)


app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting AI Engine on Port 8001...")
    uvicorn.run("main_ai_engine:app", host="0.0.0.0", port=8001, reload=True)
