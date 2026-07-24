"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Web Chatbot Widget actions
in the RAGMate backend. It maps inbound HTTP REST requests directly to the
underlying business logic executors defined inside the chatbot handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard typing libraries, FastAPI APIRouter routing components,
   Pydantic schemas, and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter for 'chatbots' tag groupings.
3. Input Payload Validation Schemas:
   - `ChatbotCreate`: Validates JSON payloads when creating a new chatbot widget link.
   - `ChatbotUpdate`: Validates JSON payloads when modifying widget properties
     (e.g., allowed domains, styles, API keys).
4. HTTP Routes:
   - GET `/api/chatbots`: Lists all widgets deployed in a workspace.
   - GET `/api/chatbots/{chatbot_id}`: Fetches the configuration for a single widget.
   - POST `/api/chatbots`: Deploys a new widget for an agent.
   - PUT `/api/chatbots/{chatbot_id}`: Modifies widget options dynamically.
"""

import logging  # Import python logging library
from typing import Optional  # Import Optional type mapping for query validations
from pydantic import BaseModel  # Pydantic BaseModels for payload validations
from fastapi import APIRouter, Depends  # FastAPI Router and Dependency Injection components
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import chatbot logic handlers
from handlers.chatbot_handler import (
    handle_get_chatbots,
    handle_get_chatbot_by_id,
    handle_create_chatbot,
    handle_update_chatbot
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for chatbot endpoints
router = APIRouter(tags=["chatbots"])

class ChatbotCreate(BaseModel):
    """
    Validates payload options for creating a new chatbot widget.
    """
    agent_id: str                               # Linked AI Agent UUID
    name: str                                   # Chatbot display name
    settings: Optional[dict] = {}               # Style/behavior settings dictionary (e.g. avatar, logo, widget color)

class ChatbotUpdate(BaseModel):
    """
    Validates optional payload options for modifying an existing chatbot widget.
    """
    name: Optional[str] = None                  # Updated display name
    settings: Optional[dict] = None             # Updated settings dictionary
    api_key: Optional[str] = None               # Updated developer API key
    allowed_domains: Optional[str] = None       # Updated CORS domains whitelist (comma-separated string)


@router.get("/api/chatbots")
async def get_chatbots(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch all chatbot widgets registered in a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID query param.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of chatbot widget dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if SQL database queries crash.
    """
    return await handle_get_chatbots(workspace_id)  # Route task execution to handlers layer


@router.get("/api/chatbots/{chatbot_id}")
async def get_chatbot_by_id(chatbot_id: str):
    """
    HTTP GET endpoint to fetch details of a specific chatbot widget.
    Publicly accessible (does not require auth) so widgets can retrieve their settings on external sites.

    Parameters:
        chatbot_id (str): Target Chatbot UUID path parameter.

    Returns:
        dict: Chatbot configuration details dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if chatbot ID is not found.
        HTTPException(500): Raised if database queries fail.
    """
    return await handle_get_chatbot_by_id(chatbot_id)  # Route task execution to handlers layer


@router.post("/api/chatbots")
async def create_chatbot(payload: ChatbotCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to register a new chatbot widget for an agent.

    Parameters:
        payload (ChatbotCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly registered chatbot details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database writes crash.
    """
    return await handle_create_chatbot(payload.dict())  # Convert to dictionary and route to handlers layer


@router.put("/api/chatbots/{chatbot_id}")
async def update_chatbot(chatbot_id: str, payload: ChatbotUpdate, current_user: dict = Depends(get_current_user)):
    """
    HTTP PUT endpoint to update widget configurations dynamically.

    Parameters:
        chatbot_id (str): Target Chatbot UUID path parameter.
        payload (ChatbotUpdate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: The updated chatbot details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if chatbot not found.
        HTTPException(500): Raised if updates crash.
    """
    return await handle_update_chatbot(chatbot_id, payload.dict())  # Route task execution to handlers layer
