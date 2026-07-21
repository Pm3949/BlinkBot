import logging
from fastapi import HTTPException
from core.security import encrypt_key, decrypt_key
from db import settings_repository

logger = logging.getLogger(__name__)


async def handle_get_user_settings(user_id: str):
    try:
        row = await settings_repository.get_user_settings(user_id)
        
        if not row:
            return {
                "openai_api_key": "",
                "groq_api_key": "",
                "gemini_api_key": "",
                "openrouter_api_key": "",
                "anthropic_api_key": "",
                "huggingface_api_key": "",
                "two_factor_enabled": False
            }
            
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "openrouter_api_key": decrypt_key(row[3]) or "",
            "anthropic_api_key": decrypt_key(row[4]) or "",
            "huggingface_api_key": decrypt_key(row[5]) or "",
            "two_factor_enabled": row[6]
        }
    except Exception as e:
        logger.error(f"Error fetching user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user settings")


async def handle_update_user_settings(
    user_id: str,
    openai_api_key: str = None,
    groq_api_key: str = None,
    gemini_api_key: str = None,
    openrouter_api_key: str = None,
    anthropic_api_key: str = None,
    huggingface_api_key: str = None,
    two_factor_enabled: bool = None
):
    try:
        openai_key = encrypt_key(openai_api_key) if openai_api_key is not None else None
        groq_key = encrypt_key(groq_api_key) if groq_api_key is not None else None
        gemini_key = encrypt_key(gemini_api_key) if gemini_api_key is not None else None
        openrouter_key = encrypt_key(openrouter_api_key) if openrouter_api_key is not None else None
        anthropic_key = encrypt_key(anthropic_api_key) if anthropic_api_key is not None else None
        huggingface_key = encrypt_key(huggingface_api_key) if huggingface_api_key is not None else None

        row = await settings_repository.upsert_user_settings(
            user_id, openai_key, groq_key, gemini_key, openrouter_key, anthropic_key, huggingface_key, two_factor_enabled
        )
        
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "openrouter_api_key": decrypt_key(row[3]) or "",
            "anthropic_api_key": decrypt_key(row[4]) or "",
            "huggingface_api_key": decrypt_key(row[5]) or "",
            "two_factor_enabled": row[6]
        }
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user settings")
