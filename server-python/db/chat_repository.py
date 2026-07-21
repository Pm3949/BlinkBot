from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from typing import Optional, List, Dict
import uuid

async def fetch_temporary_memory_patch(agent_id: str) -> str:
    """Finds any bad feedback the user gave in the past."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT f.category, f.comment_text, m.content
            FROM message_feedback f
            JOIN chat_messages m ON f.message_id = m.id
            WHERE f.agent_id = %s AND f.status = 'open'
            """,
            (agent_id,)
        )
        open_tickets = await run_in_threadpool(cursor.fetchall)
        if not open_tickets:
            return ""
            
        patch = "\n\nCRITICAL TEMPORARY CORRECTIONS (USER FEEDBACK):\n"
        patch += "The following errors were flagged in your previous answers. You MUST NOT repeat these mistakes and MUST incorporate these corrections in your responses:\n"
        for cat, comment, msg_content in open_tickets:
            short_msg = msg_content[:50] + "..." if msg_content else "Unknown message"
            patch += f"- [Flagged {cat} in past answer: '{short_msg}']: {comment}\n"
        
        return patch

async def get_agent_for_chat(agent_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, project_id, parent_agent_id, is_active, endpoints, code_interpreter_enabled, databases, native_integrations FROM agents WHERE id = %s",
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_sub_agents_for_project(project_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT id, name, description, endpoints, code_interpreter_enabled, databases, native_integrations FROM agents WHERE project_id = %s", (project_id,))
        return await run_in_threadpool(cursor.fetchall)
        
async def get_agent_routing_info(agent_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, is_active, endpoints, code_interpreter_enabled, databases, native_integrations FROM agents WHERE id = %s",
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_user_chat_limits(user_id: str):
    from utils import get_user_limits_by_id
    limits = await get_user_limits_by_id(user_id)
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND date_trunc('month', m.created_at) = date_trunc('month', current_date)
            """,
            (user_id,),
        )
        current_msg_count = (await run_in_threadpool(cursor.fetchone))[0] or 0
        return current_msg_count, limits

async def get_documents_hybrid(message: str, query_vector: str, agent_id: str, limit: int = 5):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, %s, 0.3)",
            (message, query_vector, agent_id, limit),
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_chatbot_for_widget(chatbot_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT c.agent_id, c.settings, c.message_count, a.user_id, c.allowed_domains FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s",
            (chatbot_id,),
        )
        return await run_in_threadpool(cursor.fetchone)

async def check_widget_limits(user_id: str):
    from utils import get_user_limits_by_id
    limits = await get_user_limits_by_id(user_id)
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(message_count), 0)
            FROM chatbots c
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        total_widget_msgs = (await run_in_threadpool(cursor.fetchone))[0] or 0
        return total_widget_msgs, limits

async def log_widget_message(chatbot_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (chatbot_id,))
        await run_in_threadpool(cursor.execute, "INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,))

async def get_chatbot_by_api_key(x_api_key: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT c.id, c.agent_id, a.user_id FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.api_key = %s",
            (x_api_key,),
        )
        return await run_in_threadpool(cursor.fetchone)

async def create_chat_session(session_id: str, title: str, agent_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO chat_sessions (id, title, agent_id) VALUES (%s, %s, %s)",
            (session_id, title, agent_id)
        )

async def insert_chat_message(msg_id: str, session_id: str, role: str, content: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO chat_messages (id, session_id, role, content) VALUES (%s, %s, %s, %s)",
            (msg_id, session_id, role, content)
        )

async def get_session_history(session_id: str, limit: int = 10):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT %s",
            (session_id, limit)
        )
        return await run_in_threadpool(cursor.fetchall)

async def delete_agent(agent_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            WITH RECURSIVE agent_tree AS (
                SELECT id FROM agents WHERE id = %s
                UNION
                SELECT a.id 
                FROM agents a
                INNER JOIN agent_tree at ON a.parent_agent_id = at.id
            )
            SELECT id FROM agent_tree;
            """,
            (agent_id,)
        )
        agent_ids_to_delete = [row[0] for row in (await run_in_threadpool(cursor.fetchall))]

        if not agent_ids_to_delete:
            return 0
            
        for aid in agent_ids_to_delete:
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM document_embeddings
                WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
                """, (aid,)
            )
            await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE agent_id = %s", (aid,))
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM chat_messages 
                WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = %s)
                """, (aid,)
            )
            await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id = %s", (aid,))
            await run_in_threadpool(cursor.execute, "DELETE FROM chatbots WHERE agent_id = %s", (aid,))
            
        ids_tuple = tuple(agent_ids_to_delete)
        placeholders = ','.join(['%s'] * len(ids_tuple))
        await run_in_threadpool(cursor.execute, f"DELETE FROM agents WHERE id IN ({placeholders})", ids_tuple)
        return len(agent_ids_to_delete)

async def delete_chatbot(chatbot_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM widget_message_logs WHERE chatbot_id = %s", (chatbot_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM chatbots WHERE id = %s", (chatbot_id,))
