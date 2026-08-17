"""
================================================================================
FASTAPI BOOTSTRAPPER & SYSTEM LIFE LIFECYCLE CONTROLLER (main.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the core entrypoint and orchestrator for the modular Python backend 
application. It coordinates starting up server tasks, registering API endpoints, 
applying middleware security, scheduling database cleanups, and gracefully shutting down resources.

KEY COMPONENT WORKFLOWS:
1. Application Lifecycle Management (lifespan):
   - Initializes logs directories and starts the cron scheduler.
   - Triggers concurrent, thread-safe background loading of heavy sentence transformer models.
   - Restores interrupted database ingestion states (resume pending document uploads).
   - Syncs agent settings and prompt structures into database records.
   - Cleans up thread log files and shuts down schedulers upon exit.
2. Custom Security Middleware:
   - Permissive Widget CORS Middleware: Chatbots can be embedded as widgets on any 
     website. This intercepts preflight and actual requests on widget paths, injecting 
     wildcard `Access-Control-Allow-Origin: *` headers.
   - Logging Context Middleware: Extracts client IPs and bearer JWT claims, injecting 
     them into thread-local ContextVars before executing request blocks.
3. Utility Services (TTS & STT):
   - Text-to-Speech (TTS): Receives text and returns an in-memory MP3 BytesIO stream.
   - Speech-to-Text (STT): Receives audio files, saves them to temporary files, 
     transcribes them using Groq's Whisper API, and ensures cleanup.
4. Database Maintenance Cron:
   - Launches a background thread worker using `APScheduler` to delete chat data 
     older than 30 days every day at midnight.

BEGINNER SYSTEM ARCHITECTURE CONCEPTS:
- CORS: Cross-Origin Resource Sharing is a browser security protocol that prevents 
  websites on one domain (e.g. your dashboard) from making requests to another (the API server) 
  unless explicitly allowed by headers.
- Middleware: Interceptor functions running sequentially before and after every single API call.
- Lifespan: An async context manager control block that executes logic exactly once when the 
  server starts up, yields control, and runs cleanup code when the server stops.
"""

import os
import tempfile
import shutil
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
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_db_connection
from fastapi.staticfiles import StaticFiles
from core.dependencies import UPLOAD_DIR
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

# Import all modular feature routers from the api package.
from api import (
    documents, analytics, admin, billing, chat, chat_history, workspaces, 
    agents, chatbots, settings, notifications, meta_agent, 
    demo, connectors, auth, oauth, models, workspace_tools
)
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Set up module logger using the centralized departmental system.
logger = get_department_logger("system")

# Initialize main FastAPI application.
app = FastAPI(title="Custom BlinkBot Backend")


# ==========================================
# LOADER.IO VERIFICATION
# ==========================================

@app.get("/loaderio-9c2c52496e408f1ec4033fadcc17a9b7.txt", response_class=PlainTextResponse)
def loaderio_verify() -> str:
    """
    Returns the verification token string required by Loader.io.

    Purpose:
        Used by the Loader.io load testing platform to verify domain ownership.

    Parameters:
        None.

    Returns:
        str: Loader.io verification token.
    """
    # Return the verification token text.
    return "loaderio-9c2c52496e408f1ec4033fadcc17a9b7"


# ==========================================
# CLIENT API CLIENTS
# ==========================================

# Initialize the Groq API client for transcription features.
try:
    groq_client = Groq()
except Exception as e:
    # Log warning and set to None if setup fails (e.g. key is missing).
    logger.warning(f"Groq client initialization failed: {e}")
    groq_client = None


# ==========================================
# CORS MIDDLEWARE & CONFIGURATION
# ==========================================

# Fetch permitted frontend client URLs. Fall back to local developer targets if undefined.
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
admin_url = os.getenv("ADMIN_URL", "http://localhost:5174")

# Parse comma-separated origin URLs, stripping whitespace.
allow_origins = [url.strip() for url in frontend_url.split(",")] if frontend_url != "*" else ["*"]
admin_origins = [url.strip() for url in admin_url.split(",")] if admin_url != "*" else ["*"]

# Consolidate origins lists.
if "*" in allow_origins or "*" in admin_origins:
    allow_origins = ["*"]
else:
    # Add admin URLs to the main origins list.
    allow_origins.extend(admin_origins)
    # Append local development ports to simplify local developer workflows.
    allow_origins.extend([
        "http://localhost:5173", "http://127.0.0.1:5173", 
        "http://localhost:5174", "http://127.0.0.1:5174"
    ])


class PublicCORSMiddleware(BaseHTTPMiddleware):
    """
    Middleware that bypasses CORS restrictions for widget endpoints.

    Purpose:
        Widget routes (like `/api/widget/*` or `/api/chatbots/*`) are designed to be embedded 
        on third-party customer websites. This middleware overrides standard CORS restrictions 
        by returning permissive headers for these paths.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercepts incoming requests, applying permissive CORS policies where needed.

        Parameters:
            request (Request): The incoming HTTP request.
            call_next (Callable): Function to continue executing the request pipeline.

        Returns:
            Response: The HTTP response with appropriate CORS headers.
        """
        # If the request targets widget, chatbot, TTS, or STT routes, apply permissive headers.
        if (
            request.url.path.startswith("/api/widget") 
            or request.url.path.startswith("/api/v1") 
            or request.url.path.startswith("/api/chatbots/")
            or request.url.path == "/api/tts"
            or request.url.path == "/stt"
        ):
            # Intercept preflight (OPTIONS) requests and return immediately with success.
            if request.method == "OPTIONS":
                return Response(status_code=200, headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                })
            # Continue executing the request.
            response = await call_next(request)
            # Append wildcard origin permissions to the response headers.
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
            
        # For non-widget requests, continue standard execution.
        return await call_next(request)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that updates logging context variables with request details.

    Purpose:
        Extracts the client IP and User ID from the request headers
        and sets them in thread-local ContextVars so they are logged with each line.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Extracts client details and logs them with the request.

        Parameters:
            request (Request): The incoming HTTP request.
            call_next (Callable): Function to continue executing the request pipeline.

        Returns:
            Response: The HTTP response.
        """
        # 1. Extract the client's IP.
        client_ip = request.client.host if request.client else "-"
        # Parse 'x-forwarded-for' header if requests pass through reverse proxies (e.g. Nginx, Cloudflare).
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
            
        # 2. Extract the User ID from the Bearer JWT token if present.
        user_id = "-"
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            try:
                # Decrypt the token signature.
                from core.auth import JWT_SECRET, ALGORITHM
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
                # Extract the subject (sub) claim.
                user_id = payload.get("sub", "-")
            except Exception:
                # Catch decryption errors silently (e.g. expired tokens).
                pass

        # Set the context variables.
        from utils.logger import user_id_var, client_ip_var
        token_user = user_id_var.set(user_id)
        token_ip = client_ip_var.set(client_ip)
        
        try:
            # Continue request execution.
            response = await call_next(request)
            return response
        finally:
            # Reset context variables to clean up resources after the request completes.
            user_id_var.reset(token_user)
            client_ip_var.reset(token_ip)


# Register middlewares in reverse order of execution.
app.add_middleware(LoggingContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    # If using wildcard origin permissions (*), allow_credentials must be False.
    allow_credentials=False if "*" in allow_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PublicCORSMiddleware)


# ==========================================
# MOUNT ROUTERS
# ==========================================

# Attach modular routers to the main application instance.
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
app.include_router(notifications.router)
app.include_router(meta_agent.router)
app.include_router(demo.router)
app.include_router(auth.router)
app.include_router(connectors.router)
app.include_router(models.router)
app.include_router(workspace_tools.router)
app.include_router(oauth.router, prefix="/api/auth", tags=["OAuth Native Integrations"])


# ==========================================
# RATE LIMITING & STATIC FILES
# ==========================================

# Set up the slowapi rate limiter.
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount the static uploads directory to serve files (e.g. avatars, document previews) directly.
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ==========================================
# UTILITY ENDPOINTS (TTS & STT)
# ==========================================

class TTSRequest(BaseModel):
    """
    Validation schema for Text-to-Speech generation.
    """
    text: str # Text string to convert to speech
    language: str = "en" # Target language code (defaults to English 'en')


@app.post("/api/tts")
async def generate_tts(req: TTSRequest) -> StreamingResponse:
    """
    Generates speech audio from text using Google TTS (gTTS).

    Optimized: Delegates the blocking gTTS HTTP network request (write_to_fp) 
    to run_in_threadpool to keep the FastAPI main event loop non-blocking.
    """
    try:
        # Instantiate gTTS object
        tts = gTTS(text=req.text, lang=req.language, slow=False)
        fp = BytesIO()
        
        # Execute the blocking Google Translate HTTP network write in the threadpool
        await run_in_threadpool(tts.write_to_fp, fp)
        
        # Reset the stream pointer back to the beginning
        fp.seek(0)
        return StreamingResponse(fp, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = Form(None)) -> dict:
    """
    Transcribes audio to text using Groq's Whisper API.

    Optimized: Delegates the blocking disk file I/O operations and synchronous 
    Groq Whisper API network request to run_in_threadpool to keep the loop non-blocking.
    """
    # Verify the Groq client is initialized.
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client is not configured")
        
    # Verify the uploaded file type.
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format")
        
    # Save the upload stream to a temporary file on disk (run file writes inside threadpool)
    file_bytes = await file.read()
    temp_audio_fd, temp_audio_path = tempfile.mkstemp(suffix=".webm")
    
    def write_temp_file():
        with os.fdopen(temp_audio_fd, "wb") as temp_audio:
            temp_audio.write(file_bytes)
            
    await run_in_threadpool(write_temp_file)
        
    try:
        # Run blocking file read and Groq API call inside the worker threadpool
        def run_transcription():
            with open(temp_audio_path, "rb") as f:
                kwargs = {
                    "file": (file.filename, f.read()),
                    "model": "whisper-large-v3"
                }
                # Inject language configuration if provided.
                if language and language != "auto":
                    kwargs["language"] = language
                    
                return groq_client.audio.transcriptions.create(**kwargs)
                
        transcription = await run_in_threadpool(run_transcription)
        return {"text": transcription.text}
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Crucial: Always delete temporary files on a worker thread to avoid event loop latency
        def clean_temp_file():
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        await run_in_threadpool(clean_temp_file)



# ==========================================
# BACKGROUND TASKS (CRON JOBS)
# ==========================================

def cleanup_old_chat_data():
    """
    Deletes chat sessions older than 30 days.

    Purpose:
        Maintains database hygiene and complies with data retention policies.
        Runs daily via the background scheduler.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Deletes matching rows from `chat_sessions` and `chat_messages` tables.
    """
    logger.info("Running automatic cleanup of old chat data (>30 days)")
    conn = None
    cursor = None
    try:
        # Get a connection and execute cleanup.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE created_at < NOW() - INTERVAL '30 days'")
        cursor.execute("DELETE FROM langgraph_writes WHERE created_at < NOW() - INTERVAL '3 days'")
        cursor.execute("DELETE FROM langgraph_checkpoints WHERE created_at < NOW() - INTERVAL '3 days'")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to cleanup old chat data: {e}")
        if conn:
            conn.rollback()
    finally:
        # Close connection and cursor.
        if cursor: cursor.close()
        if conn: conn.close()


# Initialize the background scheduler.
scheduler = BackgroundScheduler()
# Schedule the cleanup task to run daily at midnight.
scheduler.add_job(cleanup_old_chat_data, 'cron', hour=0, minute=0)


# ==========================================
# APPLICATION LIFECYCLE MANAGEMENT
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager.

    Purpose:
        Coordinates startup and shutdown tasks.
        Startup tasks: creates the logs directory, starts the scheduler, 
        pre-loads models in the background, initializes tables, resumes 
        interrupted uploads, and configures default prompts.
        Shutdown tasks: stops the scheduler, closes log file handles,
        and deletes temporary directories.
    """
    # ------------------------------------------
    # STARTUP TASKS
    # ------------------------------------------
    os.makedirs("logs", exist_ok=True)
    # Start the cron scheduler.
    scheduler.start()
    
    # Initialize database migrations automatically.
    try:
        from database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool
        import glob
        
        # Get all .sql files from db/migrations in sorted order
        migration_dir = os.path.join(os.path.dirname(__file__), "db", "migrations")
        sql_files = sorted(glob.glob(os.path.join(migration_dir, "*.sql")))
        
        for sql_file in sql_files:
            try:
                logger.info(f"Running database migration file: {os.path.basename(sql_file)}")
                with open(sql_file, "r") as f:
                    sql_content = f.read()
                async with get_db_cursor_async(commit=True) as cursor:
                    await run_in_threadpool(cursor.execute, sql_content)
            except Exception as file_err:
                logger.warning(f"Migration file {os.path.basename(sql_file)} skipped or failed: {file_err}")
        logger.info("All database migrations synchronized.")
    except Exception as e:
        logger.error(f"Failed to synchronize database migrations on startup: {e}")
    
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

    # Synchronize default settings & system prompts for Network Manager and General Assistant core agents.
    try:
        from database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool
        from prompts.system_agent_prompts import NETWORK_MANAGER_SYSTEM_PROMPT, GENERAL_ASSISTANT_SYSTEM_PROMPT
        
        async with get_db_cursor_async(commit=True) as cursor:
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE agents 
                SET web_search_enabled = FALSE, system_prompt = %s 
                WHERE name = 'Network Manager'
                """,
                (NETWORK_MANAGER_SYSTEM_PROMPT,)
            )
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE agents 
                SET web_search_enabled = FALSE, description = 'Friendly greeting and default welcome assistant.', system_prompt = %s 
                WHERE name = 'General Assistant'
                """,
                (GENERAL_ASSISTANT_SYSTEM_PROMPT,)
            )
        logger.info("Successfully updated default web_search_enabled=False and system prompts for core agents.")
    except Exception as e:
        logger.error(f"Failed to update core agents settings on startup: {e}")

    # Yield control to allow the application to process requests.
    yield

    # ------------------------------------------
    # SHUTDOWN TASKS
    # ------------------------------------------
    # Stop scheduler background threads.
    scheduler.shutdown()
    # Close log file handles.
    cleanup_department_loggers()
    # Delete the local logs directory.
    if os.path.exists("logs"):
        shutil.rmtree("logs", ignore_errors=True)


# Bind the lifespan context manager to the FastAPI application instance.
app.router.lifespan_context = lifespan


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Modular BlinkBot Server on Port 8000...")
    # Run the server. reload=True enables hot-reloads on file changes.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

