from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import psycopg2.extras

async def upsert_google_token(user_id: str, access_token: str, refresh_token: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT id FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        existing = await run_in_threadpool(cursor.fetchone)
        
        if existing:
            await run_in_threadpool(
                cursor.execute,
                "UPDATE oauth_connections SET access_token = %s, refresh_token = COALESCE(%s, refresh_token), updated_at = NOW() WHERE id = %s",
                (access_token, refresh_token, existing[0])
            )
        else:
            await run_in_threadpool(
                cursor.execute,
                "INSERT INTO oauth_connections (user_id, provider, access_token, refresh_token) VALUES (%s, 'google', %s, %s)",
                (user_id, access_token, refresh_token)
            )

async def get_google_token(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT access_token, refresh_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        return await run_in_threadpool(cursor.fetchone)

async def update_access_token_only(user_id: str, access_token: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE oauth_connections SET access_token = %s, updated_at = NOW() WHERE user_id = %s AND provider = 'google'", 
            (access_token, user_id)
        )

async def get_agent_embed_info(agent_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchone)

async def create_document_stub(agent_id: str, filename: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', 0) RETURNING id;",
            (agent_id, filename)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]
