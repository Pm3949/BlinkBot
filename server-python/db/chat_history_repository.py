from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import uuid

async def get_chat_sessions(workspace_id: str, user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT s.id, s.agent_id, s.title, s.pinned, s.created_at, s.updated_at, a.name as agent_name
            FROM chat_sessions s
            LEFT JOIN agents a ON s.agent_id = a.id
            WHERE s.workspace_id = %s AND s.user_id = %s
            ORDER BY s.pinned DESC, s.updated_at DESC
            """,
            (workspace_id, user_id)
        )
        return await run_in_threadpool(cursor.fetchall)

async def create_chat_session(user_id: str, workspace_id: str, agent_id: str, title: str):
    session_id = str(uuid.uuid4())
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chat_sessions (id, user_id, workspace_id, agent_id, title)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, agent_id, title, pinned, created_at, updated_at;
            """,
            (session_id, user_id, workspace_id, agent_id, title)
        )
        return await run_in_threadpool(cursor.fetchone)

async def update_chat_session(session_id: str, title: str, pinned: bool):
    async with get_db_cursor_async(commit=True) as cursor:
        updates = []
        values = []
        
        if title is not None:
            updates.append("title = %s")
            values.append(title)
        if pinned is not None:
            updates.append("pinned = %s")
            values.append(pinned)
            
        if not updates:
            return False
            
        updates.append("updated_at = timezone('utc'::text, now())")
        values.append(session_id)
        
        query = f"UPDATE chat_sessions SET {', '.join(updates)} WHERE id = %s"
        await run_in_threadpool(cursor.execute, query, tuple(values))
        return True

async def delete_chat_session(session_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE id = %s", (session_id,))

async def clear_agent_chat_history(agent_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id = %s", (agent_id,))

async def get_chat_messages(session_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, role, content, latency, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def create_chat_message(session_id: str, role: str, content: str, latency: float):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chat_messages (session_id, role, content, latency)
            VALUES (%s, %s, %s, %s)
            RETURNING id, role, content, latency, created_at;
            """,
            (session_id, role, content, latency)
        )
        row = await run_in_threadpool(cursor.fetchone)
        
        await run_in_threadpool(
            cursor.execute,
            "UPDATE chat_sessions SET updated_at = timezone('utc'::text, now()) WHERE id = %s",
            (session_id,)
        )
        return row
