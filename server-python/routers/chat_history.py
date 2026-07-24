"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Chat History and Message
management actions in the RAGMate backend. It maps incoming HTTP REST requests
directly to the underlying business logic executors defined inside the chat history
handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard typing modules, FastAPI APIRouter routing components,
   Pydantic schemas, and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter for 'chat_history' tag groupings.
3. Input Payload Validation Schemas:
   - `ChatSessionCreate`: Validates JSON payloads when starting a new empty chat thread.
   - `ChatSessionUpdate`: Validates JSON payloads when renaming or pinning a chat thread.
   - `ChatMessageCreate`: Validates JSON payloads when inserting a new chat message bubble.
4. HTTP Routes:
   - GET `/api/chat_sessions/{workspace_id}`: Lists chat sessions active in a workspace.
   - POST `/api/chat_sessions`: Creates a new chat session.
   - PUT `/api/chat_sessions/{session_id}`: Renames or pins a chat session.
   - DELETE `/api/chat_sessions/{session_id}`: Wipes a single chat session.
   - DELETE `/api/agents/{agent_id}/chat_sessions`: Clears all history for an agent.
   - GET `/api/chat_messages/{session_id}`: Lists chat message bubbles in a session.
   - POST `/api/chat_messages`: Logs a single chat message.
"""

import logging  # Import python logging library
from typing import Optional  # Import Optional type mapping for query validations
from fastapi import APIRouter, Depends  # FastAPI Router and Dependency Injection components
from pydantic import BaseModel  # Pydantic BaseModels for payload validations
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import chat history logic handlers
from handlers.chat_history_handler import (
    handle_get_chat_sessions,
    handle_create_chat_session,
    handle_update_chat_session,
    handle_delete_chat_session,
    handle_clear_agent_chat_history,
    handle_get_chat_messages,
    handle_create_chat_message
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for chat history endpoints
router = APIRouter(tags=["chat_history"])

class ChatSessionCreate(BaseModel):
    """
    Validates payload options for starting a new chat session.
    """
    workspace_id: str                          # Workspace UUID where chat session is registered
    agent_id: Optional[str] = None             # Linked AI Agent ID (optional)
    title: str = "New chat"                    # Initial conversation title placeholder

class ChatSessionUpdate(BaseModel):
    """
    Validates payload options for updating chat session properties.
    """
    title: Optional[str] = None                # New custom title
    pinned: Optional[bool] = None               # Pin status flag

class ChatMessageCreate(BaseModel):
    """
    Validates payload options for inserting a message bubble.
    """
    session_id: str                            # Parent conversation session UUID
    role: str                                  # Sender identity ('user' or 'assistant')
    content: str                               # Text content body of message
    latency: Optional[float] = None            # Latency (for assistant completions)


@router.get("/api/chat_sessions/{workspace_id}")
async def get_chat_sessions(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch chat sessions list in a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of chat session dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if queries fail.
    """
    user_id = current_user["sub"]  # Extract requester's User ID from JWT
    return await handle_get_chat_sessions(workspace_id, user_id)  # Route task execution to handlers layer


@router.post("/api/chat_sessions")
async def create_chat_session(payload: ChatSessionCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to create a new chat session.

    Parameters:
        payload (ChatSessionCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly registered chat session details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database inserts crash.
    """
    data = payload.dict()  # Convert Pydantic request structure to dictionary
    data["user_id"] = current_user["sub"]  # Inject user ID subject from JWT
    return await handle_create_chat_session(data)  # Route task execution to handlers layer


@router.put("/api/chat_sessions/{session_id}")
async def update_chat_session(session_id: str, payload: ChatSessionUpdate, current_user: dict = Depends(get_current_user)):
    """
    HTTP PUT endpoint to update or rename a chat session.

    Parameters:
        session_id (str): Target Session UUID path parameter.
        payload (ChatSessionUpdate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if session ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    # Exclude unset fields from the payload dictionary to update only targeted properties
    return await handle_update_chat_session(session_id, payload.dict(exclude_unset=True))


@router.delete("/api/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP DELETE endpoint to delete a chat session.

    Parameters:
        session_id (str): Target Session UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if deletions crash.
    """
    return await handle_delete_chat_session(session_id)  # Route task execution to handlers layer


@router.delete("/api/agents/{agent_id}/chat_sessions")
async def clear_agent_chat_history(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP DELETE endpoint to clear all chat history for an agent.

    Parameters:
        agent_id (str): Target Agent UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database purges crash.
    """
    return await handle_clear_agent_chat_history(agent_id)  # Route task execution to handlers layer


@router.get("/api/chat_messages/{session_id}")
async def get_chat_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch chat message bubbles in a session.

    Parameters:
        session_id (str): Target Session UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of message bubble dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    return await handle_get_chat_messages(session_id)  # Route task execution to handlers layer


@router.post("/api/chat_messages")
async def create_chat_message(payload: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to log a single message bubble.

    Parameters:
        payload (ChatMessageCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Saved message bubble details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database writes crash.
    """
    return await handle_create_chat_message(payload.dict())  # Route task execution to handlers layer
