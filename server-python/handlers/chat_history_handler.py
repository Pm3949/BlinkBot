from fastapi import HTTPException
from db import chat_history_repository

from utils.logger import get_department_logger

logger = get_department_logger("agent")

async def handle_get_chat_sessions(workspace_id: str, user_id: str):
    logger.info(f"Retrieving chat sessions list for workspace ID: {workspace_id} (User ID: {user_id})")
    try:
        logger.debug("Executing chat sessions fetch query in database...")
        rows = await chat_history_repository.get_chat_sessions(workspace_id, user_id)
        logger.debug(f"Retrieved {len(rows)} chat session records.")
        
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
            
        logger.info(f"Successfully processed and returned {len(sessions)} chat sessions.")
        return sessions
    except Exception as e:
        logger.error(f"Error fetching chat sessions for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chat sessions")


async def handle_create_chat_session(payload: dict):
    logger.info(f"Creating a new chat session. Workspace ID: {payload.get('workspace_id')}")
    try:
        logger.debug("Executing database creation query in chat_history_repository...")
        row = await chat_history_repository.create_chat_session(
            payload.get("user_id"),
            payload.get("workspace_id"),
            payload.get("agent_id"),
            payload.get("title", "New chat")
        )
        
        logger.info(f"Chat session successfully created. ID: {row[0]}")
        return {
            "id": row[0],
            "agent_id": row[1],
            "title": row[2],
            "pinned": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chat session")


async def handle_update_chat_session(session_id: str, payload: dict):
    logger.info(f"Updating chat session ID: {session_id} (Title: '{payload.get('title')}', Pinned: {payload.get('pinned')})")
    try:
        logger.debug("Executing database update query in chat_history_repository...")
        updated = await chat_history_repository.update_chat_session(
            session_id,
            payload.get("title"),
            payload.get("pinned")
        )
            
        if not updated:
            logger.warning(f"No updates matched or no parameters changed for session ID: {session_id}")
            return {"message": "No updates provided"}
            
        logger.info(f"Chat session ID {session_id} successfully updated.")
        return {"message": "Chat session updated"}
    except Exception as e:
        logger.error(f"Error updating chat session ID {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chat session")


async def handle_delete_chat_session(session_id: str):
    logger.info(f"Deleting chat session ID: {session_id}")
    try:
        logger.debug("Executing database delete query in chat_history_repository...")
        await chat_history_repository.delete_chat_session(session_id)
        logger.info(f"Chat session ID {session_id} successfully deleted.")
        return {"message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session ID {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete chat session")


async def handle_clear_agent_chat_history(agent_id: str):
    logger.info(f"Scrubbing/clearing chat history for agent ID: {agent_id}")
    try:
        logger.debug("Executing database purge query in chat_history_repository...")
        await chat_history_repository.clear_agent_chat_history(agent_id)
        logger.info(f"All chat history for agent ID {agent_id} successfully scrubbed.")
        return {"message": "All chat history for this agent has been scrubbed"}
    except Exception as e:
        logger.error(f"Error clearing agent chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


async def handle_get_chat_messages(session_id: str):
    logger.info(f"Retrieving messages list for chat session: {session_id}")
    try:
        logger.debug("Executing chat messages fetch query...")
        rows = await chat_history_repository.get_chat_messages(session_id)
        logger.debug(f"Retrieved {len(rows)} message records.")
        
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "latency": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            })
            
        logger.info(f"Successfully processed {len(messages)} messages.")
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chat messages")


async def handle_create_chat_message(payload: dict):
    logger.info(f"Creating a new chat message entry. Session ID: {payload.get('session_id')} (Role: {payload.get('role')})")
    try:
        logger.debug("Executing message insertion query...")
        row = await chat_history_repository.create_chat_message(
            payload.get("session_id"),
            payload.get("role"),
            payload.get("content"),
            payload.get("latency")
        )
        
        logger.info(f"Chat message successfully created. ID: {row[0]}")
        return {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "latency": row[3],
            "created_at": row[4].isoformat() if row[4] else None
        }
    except Exception as e:
        logger.error(f"Error creating chat message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chat message")
