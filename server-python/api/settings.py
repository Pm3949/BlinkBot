"""
================================================================================
USER SETTINGS & CREDENTIALS CONFIGURATION LAYER (settings.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for managing user settings.
It manages:
1. Credentials storage: Saving and retrieving API keys for LLM providers
   (OpenAI, Groq, Gemini, OpenRouter, Anthropic, Hugging Face).
2. Two-Factor Authentication state toggling.
3. Workspace Key Sharing: Toggling key sharing settings (`share_keys`), allowing other
   workspace members to use the owner's API keys for RAG execution.

SECURITY & ENCRYPTION:
- All routes are protected by the `get_current_user` JWT check.
- When retrieving settings, keys are masked using helper functions before transmission.
- When writing settings, keys are encrypted using symmetric Fernet encryption before being saved.
"""

import logging
from utils.logger import get_department_logger
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

# Import settings management handlers.
from handlers.settings_handler import (
    handle_get_user_settings,
    handle_update_user_settings
)

# Initialize standard module logger.
logger = get_department_logger("system")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["settings"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class UserSettingsUpdate(BaseModel):
    """
    Validation schema for modifying user keys and settings preferences.
    """
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    two_factor_enabled: Optional[bool] = None # Optional 2FA preference toggle
    share_keys: Optional[bool] = None # Optional toggle to share keys with workspace members


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the authenticated user's settings and masked API keys.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Masked API keys, 2FA status, and key sharing preferences.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Retrieve settings from the database.
    return await handle_get_user_settings(user_id)


@router.post("/api/settings")
async def update_user_settings(payload: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    """
    Updates the user's API keys and settings preferences.

    Purpose:
        Encrypts and stores provider keys and configures sharing settings.

    Parameters:
        payload (UserSettingsUpdate): Contains the new keys or preferences to save.
        current_user (dict): JWT details.

    Returns:
        dict: The updated settings.

    Side Effects / State Changes:
        - Updates the matching row in the `user_settings` table.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
        - Raises 400 Bad Request if validation checks fail.
    """
    # Save the updated configurations.
    return await handle_update_user_settings(
        current_user["sub"],
        payload.openai_api_key,
        payload.groq_api_key,
        payload.gemini_api_key,
        payload.openrouter_api_key,
        payload.anthropic_api_key,
        payload.huggingface_api_key,
        payload.two_factor_enabled,
        payload.share_keys
    )

