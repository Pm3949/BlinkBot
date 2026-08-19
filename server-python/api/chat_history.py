"""
================================================================================
CHAT SESSION & MESSAGE HISTORY ROUTER LAYER (chat_history.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for retrieving, creating, and modifying
user chat threads (sessions) and message logs. It handles:
1. Chat Session management: Creating threads, retrieving thread lists for the UI sidebar,
   renaming titles, pinning threads, and deleting sessions.
2. Message logging: Saving individual message bubbles (user prompts, agent answers, latency stats)
   and retrieving chronological message logs for active sessions.
3. Batch operations: Clearing all chat histories linked to an agent.

DATA FLOW:
- Requests pass through authentication checks (`get_current_user`).
- Input schemas (`ChatSessionCreate`, `ChatSessionUpdate`, `ChatMessageCreate`) validate request formats.
- Handler functions in `handlers/chat_history_handler.py` are executed to query and update the database.
"""

import logging
from utils.logger import get_department_logger
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import get_current_user

# Import the history management handlers.
from handlers.chat_history_handler import (
    handle_get_chat_sessions,
    handle_create_chat_session,
    handle_update_chat_session,
    handle_delete_chat_session,
    handle_clear_agent_chat_history,
    handle_get_chat_messages,
    handle_create_chat_message
)

# Initialize standard module-level logger.
logger = get_department_logger("agent")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["chat_history"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class ChatSessionCreate(BaseModel):
    """
    Validation schema for creating a new chat session thread.
    """
    workspace_id: str # Parent workspace UUID
    agent_id: Optional[str] = None # Target agent UUID. If None, defaults to the greeting assistant.
    title: str = "New chat" # Default placeholder title for the thread


class ChatSessionUpdate(BaseModel):
    """
    Validation schema for editing chat session properties.
    """
    title: Optional[str] = None # New title for renaming threads
    pinned: Optional[bool] = None # Pin status to keep the thread at the top of the sidebar


class ChatMessageCreate(BaseModel):
    """
    Validation schema for logging an individual message bubble.
    """
    session_id: str # Target chat session UUID
    role: str # Sender role (e.g. 'user', 'assistant', 'system')
    content: str # Raw text content of the message
    latency: Optional[float] = None # Model response latency in seconds
    steps: Optional[list] = None # Agent execution steps trace (JSONB)


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/chat_sessions/{workspace_id}")
async def get_chat_sessions(workspace_id: str, agent_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """
    Retrieves all chat sessions for a user within a target workspace, optionally filtered by agent.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Retrieve sessions via the handler.
    return await handle_get_chat_sessions(workspace_id, user_id, agent_id)


@router.post("/api/chat_sessions")
async def create_chat_session(payload: ChatSessionCreate, current_user: dict = Depends(get_current_user)):
    """
    Creates a new empty chat session thread.

    Purpose:
        Starts a new chat thread for user-agent interactions.

    Parameters:
        payload (ChatSessionCreate): Pydantic body containing workspace ID, target agent ID, and default title.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created chat session database record attributes.

    Side Effects / State Changes:
        - Writes a new row to the `chat_sessions` database table.

    Errors / Exceptions:
        - Raises 401 on authentication failures.
        - Raises 400 Bad Request if the target agent or workspace is invalid.
    """
    # Convert Pydantic model parameters to a dictionary.
    data = payload.dict()
    # Inject the user's UUID.
    data["user_id"] = current_user["sub"]
    # Create the session via the handler.
    return await handle_create_chat_session(data)


@router.put("/api/chat_sessions/{session_id}")
async def update_chat_session(session_id: str, payload: ChatSessionUpdate, current_user: dict = Depends(get_current_user)):
    """
    Updates properties of an existing chat session.

    Purpose:
        Handles renaming and pinning/unpinning chat threads.

    Parameters:
        session_id (str): The unique UUID of the target session.
        payload (ChatSessionUpdate): Contains properties to update.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Updates the corresponding columns in the `chat_sessions` table.

    Errors / Exceptions:
        - Raises 401/403 on permission issues.
        - Raises 404 Not Found if the session does not exist.
    """
    # Exclude unset fields to avoid overwriting database values with nulls.
    return await handle_update_chat_session(session_id, payload.dict(exclude_unset=True))


@router.delete("/api/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Deletes a specific chat session and all its messages.

    Purpose:
        Permanently removes a chat thread and its message logs.

    Parameters:
        session_id (str): UUID of the target session.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Deletes matching rows in the `chat_sessions` and `chat_messages` tables.

    Errors / Exceptions:
        - Raises 401/403 on authorization issues.
        - Raises 404 if the session is not found.
    """
    # Delete the session using the handler.
    return await handle_delete_chat_session(session_id)


@router.delete("/api/agents/{agent_id}/chat_sessions")
async def clear_agent_chat_history(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    Clears all chat history associated with a specific agent.

    Purpose:
        Removes all chat sessions and message logs linked to an agent.

    Parameters:
        agent_id (str): UUID of the target agent.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes rows in `chat_sessions` and `chat_messages` tables linked to the agent.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
    """
    # Delete agent chat history via the handler.
    return await handle_clear_agent_chat_history(agent_id)


@router.get("/api/chat_messages/{session_id}")
async def get_chat_messages(
    session_id: str,
    limit: Optional[int] = 20,
    before: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves messages for a specific chat session, supporting optional pagination.

    Purpose:
        Loads the chat message history to render the active conversation thread.

    Parameters:
        session_id (str): UUID of the target session.
        limit (int, optional): Number of recent messages to return.
        before (str, optional): ISO timestamp cursor.
        current_user (dict): JWT details.

    Returns:
        list of dict: Chronological list of message logs.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 on auth errors.
        - Raises 404 if the session does not exist.
    """
    # Fetch messages using the handler.
    return await handle_get_chat_messages(session_id, limit, before)


@router.post("/api/chat_messages")
async def create_chat_message(payload: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    """
    Logs a single chat message.

    Purpose:
        Appends a message (user prompt or agent response) to the database history logs.

    Parameters:
        payload (ChatMessageCreate): Pydantic body containing the message properties.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created message database record attributes.

    Side Effects / State Changes:
        - Writes a new row to the `chat_messages` table.

    Errors / Exceptions:
        - Raises 401 on authentication failures.
        - Raises 400 if the target session ID is invalid.
    """
    # Log the message using the handler.
    return await handle_create_chat_message(payload.dict())

