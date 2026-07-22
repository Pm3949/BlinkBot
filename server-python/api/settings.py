import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

from handlers.settings_handler import (
    handle_get_user_settings,
    handle_update_user_settings
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

class UserSettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    two_factor_enabled: Optional[bool] = None
    share_keys: Optional[bool] = None

@router.get("/api/settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch the user's settings.
    Args:
        user_id (str): The ID of the user.
    Returns: A dictionary containing the user's decrypted API keys and 2FA status.
    """
    user_id = current_user["sub"]
    return await handle_get_user_settings(user_id)


@router.post("/api/settings")
async def update_user_settings(payload: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to update the user's API keys and 2FA preferences securely.
    Args:
        user_id (str): The ID of the user.
        payload (UserSettingsUpdate): The new keys or 2FA preference.
    Returns: A dictionary containing the newly saved settings.
    """
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
