import logging
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import get_current_user

from handlers.chat_history_handler import (
    handle_get_chat_sessions,
    handle_create_chat_session,
    handle_update_chat_session,
    handle_delete_chat_session,
    handle_clear_agent_chat_history,
    handle_get_chat_messages,
    handle_create_chat_message
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat_history"])

class ChatSessionCreate(BaseModel):
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
async def get_chat_sessions(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch the list of chat threads to display in the left sidebar.
    Args:
        workspace_id (str): The workspace ID.
        user_id (str): The user ID.
    Returns: A list of chat sessions.
    """
    user_id = current_user["sub"]
    return await handle_get_chat_sessions(workspace_id, user_id)

@router.post("/api/chat_sessions")
async def create_chat_session(payload: ChatSessionCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create a new empty thread.
    Args:
        payload (ChatSessionCreate): The chat session details.
    Returns: The created session.
    """
    data = payload.dict()
    data["user_id"] = current_user["sub"]
    return await handle_create_chat_session(data)

@router.put("/api/chat_sessions/{session_id}")
async def update_chat_session(session_id: str, payload: ChatSessionUpdate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to update or rename a chat thread.
    Args:
        session_id (str): The session ID.
        payload (ChatSessionUpdate): The update details.
    Returns: A success message.
    """
    return await handle_update_chat_session(session_id, payload.dict(exclude_unset=True))

@router.delete("/api/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to delete a specific thread.
    Args:
        session_id (str): The session ID.
    Returns: A success message.
    """
    return await handle_delete_chat_session(session_id)

@router.delete("/api/agents/{agent_id}/chat_sessions")
async def clear_agent_chat_history(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to clear all chat history for a specific agent.
    Args:
        agent_id (str): The agent ID.
    Returns: A success message.
    """
    return await handle_clear_agent_chat_history(agent_id)

@router.get("/api/chat_messages/{session_id}")
async def get_chat_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch all raw message bubbles for a given thread.
    Args:
        session_id (str): The session ID.
    Returns: A list of messages.
    """
    return await handle_get_chat_messages(session_id)

@router.post("/api/chat_messages")
async def create_chat_message(payload: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to log a single chat message.
    Args:
        payload (ChatMessageCreate): The message details.
    Returns: The saved message.
    """
    return await handle_create_chat_message(payload.dict())
