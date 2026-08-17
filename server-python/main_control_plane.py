"""
================================================================================
FASTAPI BOOTSTRAPPER - CONTROL PLANE (main_control_plane.py)
================================================================================
"""

import os
from contextlib import asynccontextmanager
from utils.logger import get_department_logger, cleanup_department_loggers
from dotenv import load_dotenv

# Load local system environment variables.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from core.database import get_db_connection
from fastapi.staticfiles import StaticFiles
from core.dependencies import UPLOAD_DIR
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

# Import only control plane routers from the api package.
from api import (
    analytics, admin, billing, chat_history, workspaces, 
    agents, settings, auth, oauth, models, demo, workspace_tools
)
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Set up module logger using the centralized departmental system.
logger = get_department_logger("system")

# Initialize Control Plane FastAPI application.
app = FastAPI(title="BlinkBot Control Plane API Gateway")

# Permitted frontend client URLs.
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
# MOUNT CONTROL PLANE ROUTERS
# ==========================================
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(chat_history.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(settings.router)
app.include_router(auth.router)
app.include_router(models.router)
app.include_router(demo.router)
app.include_router(workspace_tools.router)
app.include_router(oauth.router, prefix="/api/auth", tags=["OAuth Native Integrations"])

# Set up the slowapi rate limiter.
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount the static uploads directory to serve files directly.
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ==========================================
# BACKGROUND TASKS (CRON JOBS)
# ==========================================
def cleanup_old_chat_data():
    logger.info("Running automatic cleanup of old chat data (>30 days)")
    conn = None
    cursor = None
    try:
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
    os.makedirs("logs", exist_ok=True)
    scheduler.start()
    
    # Initialize database migrations automatically.
    try:
        from core.database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool
        import glob
        
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

    # Synchronize default settings & system prompts for core agents.
    try:
        from core.database import get_db_cursor_async
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

    yield

    # Shutdown
    scheduler.shutdown()
    cleanup_department_loggers()
    if os.path.exists("logs"):
        import shutil
        shutil.rmtree("logs", ignore_errors=True)


app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Control Plane Gateway on Port 8000...")
    uvicorn.run("main_control_plane:app", host="0.0.0.0", port=8000, reload=True)
