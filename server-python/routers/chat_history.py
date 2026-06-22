import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat_history"])

# Models
class ChatSessionCreate(BaseModel):
    user_id: str
    workspace_id: str
    agent_id: Optional[str] = None
    title: str = "New chat"

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None

class ChatMessageCreate(BaseModel):
    session_id: str
    role: str
    content: str
    latency: Optional[float] = None

@router.get("/api/chat_sessions/{workspace_id}")
async def get_chat_sessions(workspace_id: str, user_id: str):
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

@router.post("/api/chat_sessions")
async def create_chat_session(payload: ChatSessionCreate):
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
            (session_id, payload.user_id, payload.workspace_id, payload.agent_id, payload.title)
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

@router.put("/api/chat_sessions/{session_id}")
async def update_chat_session(session_id: str, payload: ChatSessionUpdate):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if payload.title is not None:
            updates.append("title = %s")
            values.append(payload.title)
        if payload.pinned is not None:
            updates.append("pinned = %s")
            values.append(payload.pinned)
            
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

@router.delete("/api/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str):
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

@router.delete("/api/agents/{agent_id}/chat_sessions")
async def clear_agent_chat_history(agent_id: str):
    """Clears all chat history for a specific agent (for GDPR/CCPA scrub)."""
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

@router.get("/api/chat_messages/{session_id}")
async def get_chat_messages(session_id: str):
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

@router.post("/api/chat_messages")
async def create_chat_message(payload: ChatMessageCreate):
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
            (payload.session_id, payload.role, payload.content, payload.latency)
        )
        row = cursor.fetchone()
        
        # Update session updated_at
        cursor.execute(
            "UPDATE chat_sessions SET updated_at = timezone('utc'::text, now()) WHERE id = %s",
            (payload.session_id,)
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
