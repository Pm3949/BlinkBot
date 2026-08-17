"""
================================================================================
CHAT CONTROLLER AND WEBSOCKET LAYER (chat.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the entrypoint for real-time messaging and chat sessions.
It supports:
1. Real-time WebSockets (`/ws/chat/{client_id}`): Enables persistent, bidirectional
   connections for internal user-to-agent dashboard interactions.
2. Web Widget WebSockets (`/ws/widget/chat/{client_id}`): Handles public guest visitor
   interactions on third-party websites where the chatbot widget is embedded.
3. Programmatic API Endpoint (`/api/v1/chat`): Provides developer access to the agents
   using custom API keys, returning token-streamed HTTP responses.
4. Agent and Chatbot Deletion: Handles requests to remove agent configurations and public chatbot profiles.

DATA FLOW & PROTOCOLS:
- WebSockets: Upgrades HTTP protocols to RFC 6455 connections.
  State parameters (like connections and queue histories) are managed inside `handlers/chat_handler.py`.
- REST Endpoints: Uses `x_api_key` custom headers to authenticate and authorize queries.
"""

import logging
from utils.logger import get_department_logger
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request, Header, Response, WebSocket

# Import Pydantic schemas validating input payloads.
from core.schemas import ChatRequest, WidgetChatRequest
# Import API rate limiter instance.
from api.auth import limiter
# Import chat handler logic.
from handlers.chat_handler import (
    handle_chat_with_agent,
    handle_widget_chat,
    handle_api_v1_chat,
    handle_delete_agent,
    handle_delete_chatbot
)

# Initialize standard module logger.
logger = get_department_logger("agent")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["chat"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class APIChatRequest(BaseModel):
    """
    Validation schema for programmatic API client calls.
    """
    message: str # Prompt query sent to the agent
    session_id: Optional[str] = None # Optional session ID to resume thread context
    language: Optional[str] = None # Optional language code parameter


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.websocket("/ws/chat/{client_id}")
async def chat_with_agent(websocket: WebSocket, client_id: str):
    """
    Opens a real-time WebSocket connection for internal agent chat.

    Purpose:
        Establishes a persistent, low-latency WebSocket connection for dashboard-level
        chats, enabling real-time token streaming.

    Parameters:
        websocket (WebSocket): The connection object.
        client_id (str): A unique ID identifier tracking the client's connection.

    Returns:
        None.

    Side Effects / State Changes:
        - Upgrades HTTP connection to WebSocket.
        - Manages real-time data streams.

    Errors / Exceptions:
        - Raises 403/401 connection handshake failures if headers are invalid.
    """
    # Delegate communication processes and streaming loops to the chat handler.
    await handle_chat_with_agent(websocket, client_id)


@router.websocket("/ws/widget/chat/{client_id}")
async def widget_chat(websocket: WebSocket, client_id: str):
    """
    Opens a real-time WebSocket connection for public embeddable chat widgets.

    Purpose:
        Supports guest traffic on external websites where the widget is embedded.
        Applies loose connection settings to allow access without standard accounts.

    Parameters:
        websocket (WebSocket): The connection object.
        client_id (str): A unique ID identifier tracking the guest session.

    Returns:
        None.

    Side Effects / State Changes:
        - Upgrades connection to WebSocket.

    Errors / Exceptions:
        - Raises handshake errors.
    """
    # Delegate public communication and message ingestion tasks to the handler.
    await handle_widget_chat(websocket, client_id)


@router.post("/api/v1/chat")
@limiter.limit("25/minute")
async def api_v1_chat(req: APIChatRequest, request: Request, response: Response, x_api_key: str = Header(...)):
    """
    Processes chat prompts programmatically using API keys.

    Purpose:
        Allows external systems to interact with agents, returning streamed responses.
        This endpoint is rate-limited to 25 requests per minute.

    Parameters:
        req (APIChatRequest): Contains the message and optional session parameters.
        request (Request): The incoming request. Required by the rate limiter.
        response (Response): The outgoing response. Used to set headers.
        x_api_key (str): Developer API key passed via headers (`x-api-key`).

    Returns:
        StreamingResponse: Stream of the generated output tokens.

    Side Effects / State Changes:
        - Injects or retrieves chat logs.
        - Increments API key usage count records.

    Errors / Exceptions:
        - Raises 401 Unauthorized if the API key is missing or invalid.
    """
    # Delegate authentication, lookup, and streaming to the handler.
    stream_response, session_id = await handle_api_v1_chat(req.message, req.session_id, req.language, x_api_key)
    # Set the session ID in response headers so the caller can resume the thread context.
    response.headers["X-Session-ID"] = session_id
    # Return the streamed content.
    return stream_response


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """
    Deletes an agent profile.

    Purpose:
        Removes an agent's records from the database and deletes associated configurations.

    Parameters:
        agent_id (str): UUID of the agent to delete.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes rows in the `agents` table.

    Errors / Exceptions:
        - Raises 404 Not Found if the agent does not exist.
    """
    # Delegate deletion tasks to the handler.
    return await handle_delete_agent(agent_id)


@router.delete("/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str):
    """
    Deletes a public chatbot widget profile.

    Purpose:
        Removes a chatbot configuration.

    Parameters:
        chatbot_id (str): UUID of the chatbot widget to delete.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes rows in the `chatbots` table.

    Errors / Exceptions:
        - Raises 404 if the chatbot is not found.
    """
    # Delegate deletion tasks to the handler.
    return await handle_delete_chatbot(chatbot_id)

