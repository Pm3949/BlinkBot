import os
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

# Import routers
from routers import documents, analytics, admin, billing, chat, workspaces, agents, chatbots, settings, notes

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Custom RAGMate Backend")

# Initialize Groq client
try:
    groq_client = Groq()
except Exception as e:
    logger.warning(f"Groq client initialization failed: {e}")
    groq_client = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(documents.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(chat.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(chatbots.router)
app.include_router(settings.router)
app.include_router(notes.router)

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

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Modular RAGMate Server on Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
