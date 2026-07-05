import logging
import uuid
from fastapi import HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

async def handle_get_chat_sessions(workspace_id: str, user_id: str):
    """
    What it does: Fetches the list of chat threads to display in the left sidebar.
    Args:
        workspace_id (str): The workspace ID.
        user_id (str): The user ID.
    Returns: A list of chat sessions.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT s.id, s.agent_id, s.title, s.pinned, s.created_at, s.updated_at, a.name as agent_name
            FROM chat_sessions s
            LEFT JOIN agents a ON s.agent_id = a.id
            WHERE s.workspace_id = %s AND s.user_id = %s
            ORDER BY s.pinned DESC, s.updated_at DESC
            """,
            (workspace_id, user_id)
        )
        rows = cursor.fetchall()
        
        sessions = []
        for row in rows:
            sessions.append({
                "id": row[0],
                "agent_id": row[1],
                "title": row[2],
                "pinned": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "agent_name": row[6] or "General"
            })
            
        return sessions
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat sessions")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_create_chat_session(payload: dict):
    """
    What it does: Creates a new empty thread when the user clicks 'New Chat'.
    Args:
        payload (dict): The chat session payload.
    Returns: The created session details.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        session_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO chat_sessions (id, user_id, workspace_id, agent_id, title)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, agent_id, title, pinned, created_at, updated_at;
            """,
            (session_id, payload.get("user_id"), payload.get("workspace_id"), payload.get("agent_id"), payload.get("title", "New chat"))
        )
        row = cursor.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "title": row[2],
            "pinned": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_update_chat_session(session_id: str, payload: dict):
    """
    What it does: Allows renaming the thread or pinning it.
    Args:
        session_id (str): The session ID.
        payload (dict): The updates.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        title = payload.get("title")
        pinned = payload.get("pinned")
        if title is not None:
            updates.append("title = %s")
            values.append(title)
        if pinned is not None:
            updates.append("pinned = %s")
            values.append(pinned)
            
        if not updates:
            return {"message": "No updates provided"}
            
        updates.append("updated_at = timezone('utc'::text, now())")
        values.append(session_id)
        
        query = f"UPDATE chat_sessions SET {', '.join(updates)} WHERE id = %s"
        
        cursor.execute(query, tuple(values))
        conn.commit()
        
        return {"message": "Chat session updated"}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chat session")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_delete_chat_session(session_id: str):
    """
    What it does: Deletes a specific thread and all its underlying messages via CASCADE.
    Args:
        session_id (str): The session ID.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
        conn.commit()
        
        return {"message": "Chat session deleted"}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat session")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_clear_agent_chat_history(agent_id: str):
    """
    What it does: Mass-deletion utility. Clears all chat history for a specific agent.
    Args:
        agent_id (str): The agent ID.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id = %s", (agent_id,))
        conn.commit()
        
        return {"message": "All chat history for this agent has been scrubbed"}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error clearing agent chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_chat_messages(session_id: str):
    """
    What it does: Fetches all raw message bubbles for a given thread to render the UI.
    Args:
        session_id (str): The session ID.
    Returns: A list of messages.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, role, content, latency, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,)
        )
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "latency": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            })
            
        return messages
    except Exception as e:
        logger.error(f"Error fetching chat messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat messages")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_create_chat_message(payload: dict):
    """
    What it does: Logs a single chat message (either 'user' or 'assistant') into the database.
    Args:
        payload (dict): The message details.
    Returns: The saved message details.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, latency)
            VALUES (%s, %s, %s, %s)
            RETURNING id, role, content, latency, created_at;
            """,
            (payload.get("session_id"), payload.get("role"), payload.get("content"), payload.get("latency"))
        )
        row = cursor.fetchone()
        
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = timezone('utc'::text, now()) WHERE id = %s",
            (payload.get("session_id"),)
        )
        
        conn.commit()
        
        return {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "latency": row[3],
            "created_at": row[4].isoformat() if row[4] else None
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat message")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
