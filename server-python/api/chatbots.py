"""
================================================================================
CHATBOT WIDGET CONTROLLER LAYER (chatbots.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for managing embeddable chatbot widgets.
It supports:
1. Retrieval: Listing all widgets created under a workspace, or loading configuration parameters
   for a specific widget.
2. Creation: Provisioning new public widget records linked to backing agent engines.
3. Modification: Customizing UI properties (colors, headers, placeholders) and setting allowed domains
   to prevent hotlinking.

CORS & PUBLIC ACCESS:
- While creation and modification endpoints require authentication (`get_current_user`), the
  `/api/chatbots/{chatbot_id}` detail route is public. This enables embeddable frontend scripts
  to load settings (like color themes and welcome messages) without authentication.
"""

import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

# Import the chatbot widget handlers.
from handlers.chatbot_handler import (
    handle_get_chatbots,
    handle_get_chatbot_by_id,
    handle_create_chatbot,
    handle_update_chatbot
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["chatbots"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class ChatbotCreate(BaseModel):
    """
    Validation schema for establishing a new chatbot widget endpoint.
    """
    agent_id: str # Backing AI agent UUID
    name: str # Widget display name
    settings: Optional[dict] = {} # UI customization parameters (theme, branding, welcome text)


class ChatbotUpdate(BaseModel):
    """
    Validation schema for modifying widget settings.
    """
    name: Optional[str] = None # Optional name rename
    settings: Optional[dict] = None # Optional theme and behavior updates
    api_key: Optional[str] = None # Optional custom authorization key
    allowed_domains: Optional[str] = None # Comma-separated list of domains allowed to embed the widget


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/chatbots")
async def get_chatbots(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves all chatbot widgets configured in a workspace.

    Purpose:
        Lists widgets on the dashboard.

    Parameters:
        workspace_id (str): UUID of the parent workspace.
        current_user (dict): JWT details.

    Returns:
        list of dict: Registered chatbot widget records.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification checks fail.
    """
    # Fetch widgets from the database.
    return await handle_get_chatbots(workspace_id)


@router.get("/api/chatbots/{chatbot_id}")
async def get_chatbot_by_id(chatbot_id: str):
    """
    Retrieves configuration details for a single chatbot widget.

    Purpose:
        Public endpoint used by embeddable widget scripts to fetch UI configurations.

    Parameters:
        chatbot_id (str): UUID of the chatbot widget.

    Returns:
        dict: The chatbot widget configurations (branding, theme, backing agent details).

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 404 Not Found if the widget is not found.
    """
    # Fetch widget details.
    return await handle_get_chatbot_by_id(chatbot_id)


@router.post("/api/chatbots")
async def create_chatbot(payload: ChatbotCreate, current_user: dict = Depends(get_current_user)):
    """
    Creates a new embeddable chatbot widget.

    Purpose:
        Links a public widget interface to an existing AI agent.

    Parameters:
        payload (ChatbotCreate): Pydantic body containing the target agent ID and UI settings.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created chatbot database record attributes.

    Side Effects / State Changes:
        - Writes a new row to the `chatbots` table.

    Errors / Exceptions:
        - Raises 401 on authentication failures.
        - Raises 400 Bad Request if configurations are invalid.
    """
    # Register the widget.
    return await handle_create_chatbot(payload.dict())


@router.put("/api/chatbots/{chatbot_id}")
async def update_chatbot(chatbot_id: str, payload: ChatbotUpdate, current_user: dict = Depends(get_current_user)):
    """
    Updates the configuration of an embeddable chatbot widget.

    Purpose:
        Updates widget parameters, allowed domains, or theme settings.

    Parameters:
        chatbot_id (str): UUID of the target widget.
        payload (ChatbotUpdate): Contains the settings to update.
        current_user (dict): JWT details.

    Returns:
        dict: The updated chatbot database record attributes.

    Side Effects / State Changes:
        - Updates the matching row in the `chatbots` table.

    Errors / Exceptions:
        - Raises 401/403 on permission issues.
        - Raises 404 if the widget is not found.
    """
    # Update the widget.
    return await handle_update_chatbot(chatbot_id, payload.dict())

