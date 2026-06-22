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

# Import routers
from routers import documents, analytics, admin, billing, chat, chat_history, workspaces, agents, chatbots, settings, feedback, notifications, meta_agent, demo

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Custom BlinkBot Backend")

# Initialize Groq client
try:
    groq_client = Groq()
except Exception as e:
    logger.warning(f"Groq client initialization failed: {e}")
    groq_client = None

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Split by comma if multiple URLs are provided, and strip whitespace
allow_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url != "*" else ["*"]

# Always allow local development URLs
if "*" not in allow_origins:
    allow_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"])

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class PublicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/widget") or request.url.path.startswith("/api/v1"):
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

app.add_middleware(PublicCORSMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False if "*" in allow_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import documents, analytics, admin, billing, chat, chat_history, workspaces, agents, chatbots, settings, feedback, notifications, meta_agent, demo, auth
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Include Routers
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

# Configure Rate Limiter
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

@app.post("/api/tts")
async def generate_tts(req: TTSRequest):
    try:
        # Generate speech from text using gTTS
        tts = gTTS(text=req.text, lang=req.language, slow=False)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return StreamingResponse(fp, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = Form(None)):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client is not configured")
        
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format")
        
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
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

def cleanup_old_chat_data():
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

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_chat_data, 'cron', hour=0, minute=0)

@app.on_event("startup")
def startup_event():
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Modular BlinkBot Server on Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
