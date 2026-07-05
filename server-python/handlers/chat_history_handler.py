import logging
import uuid
from fastapi import HTTPException
from database_layer import chat_history_repository

logger = logging.getLogger(__name__)

async def handle_get_chat_sessions(workspace_id: str, user_id: str):
    try:
        rows = await chat_history_repository.get_chat_sessions(workspace_id, user_id)
        
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


async def handle_create_chat_session(payload: dict):
    try:
        row = await chat_history_repository.create_chat_session(
            payload.get("user_id"),
            payload.get("workspace_id"),
            payload.get("agent_id"),
            payload.get("title", "New chat")
        )
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "title": row[2],
            "pinned": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")


async def handle_update_chat_session(session_id: str, payload: dict):
    try:
        updated = await chat_history_repository.update_chat_session(
            session_id,
            payload.get("title"),
            payload.get("pinned")
        )
            
        if not updated:
            return {"message": "No updates provided"}
            
        return {"message": "Chat session updated"}
    except Exception as e:
        logger.error(f"Error updating chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chat session")


async def handle_delete_chat_session(session_id: str):
    try:
        await chat_history_repository.delete_chat_session(session_id)
        return {"message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat session")


async def handle_clear_agent_chat_history(agent_id: str):
    try:
        await chat_history_repository.clear_agent_chat_history(agent_id)
        return {"message": "All chat history for this agent has been scrubbed"}
    except Exception as e:
        logger.error(f"Error clearing agent chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


async def handle_get_chat_messages(session_id: str):
    try:
        rows = await chat_history_repository.get_chat_messages(session_id)
        
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


async def handle_create_chat_message(payload: dict):
    try:
        row = await chat_history_repository.create_chat_message(
            payload.get("session_id"),
            payload.get("role"),
            payload.get("content"),
            payload.get("latency")
        )
        
        return {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "latency": row[3],
            "created_at": row[4].isoformat() if row[4] else None
        }
    except Exception as e:
        logger.error(f"Error creating chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chat message")
