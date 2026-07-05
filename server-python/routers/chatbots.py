import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

from handlers.chatbot_handler import (
    handle_get_chatbots,
    handle_get_chatbot_by_id,
    handle_create_chatbot,
    handle_update_chatbot
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chatbots"])

class ChatbotCreate(BaseModel):
    agent_id: str
    name: str
    settings: Optional[dict] = {}

class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


@router.get("/api/chatbots")
async def get_chatbots(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: Fetches all public widgets deployed in a workspace.
    Args:
        workspace_id (str): The workspace ID.
    Returns: A list of chatbots.
    """
    return await handle_get_chatbots(workspace_id)

@router.get("/api/chatbots/{chatbot_id}")
async def get_chatbot_by_id(chatbot_id: str):
    """
    What it does: Fetches the configuration for a single widget.
    Args:
        chatbot_id (str): The chatbot ID.
    Returns: The chatbot details.
    """
    return await handle_get_chatbot_by_id(chatbot_id)

@router.post("/api/chatbots")
async def create_chatbot(payload: ChatbotCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: Creates a new public endpoint/widget for an existing Agent.
    Args:
        payload (ChatbotCreate): The new chatbot details.
    Returns: The created chatbot.
    """
    return await handle_create_chatbot(payload.dict())

@router.put("/api/chatbots/{chatbot_id}")
async def update_chatbot(chatbot_id: str, payload: ChatbotUpdate, current_user: dict = Depends(get_current_user)):
    """
    What it does: Updates widget settings dynamically.
    Args:
        chatbot_id (str): The chatbot ID.
        payload (ChatbotUpdate): The update payload.
    Returns: The updated chatbot.
    """
    return await handle_update_chatbot(chatbot_id, payload.dict())
