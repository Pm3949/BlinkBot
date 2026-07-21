import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request, Header, Response, WebSocket

from schemas import ChatRequest, WidgetChatRequest
from api.auth import limiter
from handlers.chat_handler import (
    handle_chat_with_agent,
    handle_widget_chat,
    handle_api_v1_chat,
    handle_delete_agent,
    handle_delete_chatbot
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

class APIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None

@router.websocket("/ws/chat/{client_id}")
async def chat_with_agent(websocket: WebSocket, client_id: str):
    """
    What it does: Opens a real-time connection for the internal web dashboard chat, passing messages to the handler.
    Args:
        websocket (WebSocket): The connection provided by the user's browser.
        client_id (str): The unique ID of the user's chat session.
    Returns: None.
    """
    await handle_chat_with_agent(websocket, client_id)


@router.websocket("/ws/widget/chat/{client_id}")
async def widget_chat(websocket: WebSocket, client_id: str):
    """
    What it does: Opens a real-time connection for external website widgets, passing visitor messages to the handler.
    Args:
        websocket (WebSocket): The connection provided by the visitor's browser.
        client_id (str): The unique ID of the visitor's chat session.
    Returns: None.
    """
    await handle_widget_chat(websocket, client_id)


@router.post("/api/v1/chat")
@limiter.limit("25/minute")
async def api_v1_chat(req: APIChatRequest, request: Request, response: Response, x_api_key: str = Header(...)):
    """
    What it does: Receives a programmatic chat request via an API key and streams the response back.
    Args:
        req (APIChatRequest): The request containing the message and optional session data.
        request (Request): The incoming HTTP request.
        response (Response): The outgoing HTTP response.
        x_api_key (str): The developer API key required for access.
    Returns: A streaming response of the generated answer.
    """
    stream_response, session_id = await handle_api_v1_chat(req.message, req.session_id, req.language, x_api_key)
    response.headers["X-Session-ID"] = session_id
    return stream_response


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """
    What it does: Receives a request to completely delete an agent and calls the handler to wipe its data.
    Args:
        agent_id (str): The ID of the agent to delete.
    Returns: A confirmation message.
    """
    return await handle_delete_agent(agent_id)


@router.delete("/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str):
    """
    What it does: Receives a request to delete an external chat widget and calls the handler to erase it.
    Args:
        chatbot_id (str): The ID of the chatbot widget to delete.
    Returns: A confirmation message.
    """
    return await handle_delete_chatbot(chatbot_id)
