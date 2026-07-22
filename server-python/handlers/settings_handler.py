from fastapi import HTTPException
from core.security import encrypt_key, decrypt_key
from db import settings_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")


async def handle_get_user_settings(user_id: str):
    logger.info(f"Retrieving credential settings for user ID: {user_id}")
    try:
        logger.debug("Querying user settings configuration from database...")
        row = await settings_repository.get_user_settings(user_id)
        
        if not row:
            logger.info(f"No custom settings found. Returning default empty settings layout for user {user_id}.")
            return {
                "openai_api_key": "",
                "groq_api_key": "",
                "gemini_api_key": "",
                "openrouter_api_key": "",
                "anthropic_api_key": "",
                "huggingface_api_key": "",
                "two_factor_enabled": False,
                "share_keys": False
            }
            
        logger.info(f"Successfully retrieved settings details for user ID: {user_id}")
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "openrouter_api_key": decrypt_key(row[3]) or "",
            "anthropic_api_key": decrypt_key(row[4]) or "",
            "huggingface_api_key": decrypt_key(row[5]) or "",
            "two_factor_enabled": row[6],
            "share_keys": row[7] if len(row) > 7 else False
        }
    except Exception as e:
        logger.error(f"Error fetching user settings for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user settings")


async def handle_update_user_settings(
    user_id: str,
    openai_api_key: str = None,
    groq_api_key: str = None,
    gemini_api_key: str = None,
    openrouter_api_key: str = None,
    anthropic_api_key: str = None,
    huggingface_api_key: str = None,
    two_factor_enabled: bool = None,
    share_keys: bool = None
):
    # Log update intentions with masked api keys
    logger.info(f"Updating credential settings for user ID: {user_id} (share_keys: {share_keys}, 2FA: {two_factor_enabled})")
    logger.debug(f"Keys updated status: openai={bool(openai_api_key)}, groq={bool(groq_api_key)}, gemini={bool(gemini_api_key)}, openrouter={bool(openrouter_api_key)}, anthropic={bool(anthropic_api_key)}, huggingface={bool(huggingface_api_key)}")
    try:
        openai_key = encrypt_key(openai_api_key) if openai_api_key is not None else None
        groq_key = encrypt_key(groq_api_key) if groq_api_key is not None else None
        gemini_key = encrypt_key(gemini_api_key) if gemini_api_key is not None else None
        openrouter_key = encrypt_key(openrouter_api_key) if openrouter_api_key is not None else None
        anthropic_key = encrypt_key(anthropic_api_key) if anthropic_api_key is not None else None
        huggingface_key = encrypt_key(huggingface_api_key) if huggingface_api_key is not None else None

        logger.debug("Executing settings update query in settings_repository...")
        row = await settings_repository.upsert_user_settings(
            user_id, openai_key, groq_key, gemini_key, openrouter_key, anthropic_key, huggingface_key, two_factor_enabled, share_keys
        )
        
        logger.info(f"Settings successfully updated in database for user ID: {user_id}")
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "openrouter_api_key": decrypt_key(row[3]) or "",
            "anthropic_api_key": decrypt_key(row[4]) or "",
            "huggingface_api_key": decrypt_key(row[5]) or "",
            "two_factor_enabled": row[6],
            "share_keys": row[7] if len(row) > 7 else False
        }
    except Exception as e:
        logger.error(f"Error updating user settings for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user settings")
