from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import json

async def get_chatbots(workspace_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE a.workspace_id = %s
            ORDER BY c.created_at DESC
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_chatbot_by_id(chatbot_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE c.id = %s
            """,
            (chatbot_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def create_chatbot(agent_id: str, name: str, settings: dict):
    settings_json = json.dumps(settings)
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chatbots (agent_id, name, settings)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at
            """,
            (agent_id, name, settings_json)
        )
        return await run_in_threadpool(cursor.fetchone)

async def update_chatbot(chatbot_id: str, set_clauses: list, values: list):
    async with get_db_cursor_async(commit=True) as cursor:
        query = f"UPDATE chatbots SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at;"
        await run_in_threadpool(cursor.execute, query, tuple(values))
        return await run_in_threadpool(cursor.fetchone)
