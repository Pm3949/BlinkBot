"""
Settings Router.
Responsibility: Manages user-specific preferences and API Key configurations.
Critically, this router encrypts sensitive API keys (OpenAI, Gemini, Groq) at rest
in the database using Fernet symmetric encryption, ensuring that if the DB is dumped,
the keys cannot be stolen.
"""
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from database import get_db_connection
from core.security import encrypt_key, decrypt_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

class UserSettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    two_factor_enabled: Optional[bool] = None

@router.get("/api/settings/{user_id}")
async def get_user_settings(user_id: str):
    """
    Fetches the user's settings. 
    API keys are decrypted on-the-fly using the system's Fernet master key before 
    being sent to the frontend.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT openai_api_key, groq_api_key, gemini_api_key, two_factor_enabled
            FROM user_settings
            WHERE user_id = %s
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        
        # Return sensible defaults if they haven't configured anything yet
        if not row:
            return {
                "openai_api_key": "",
                "groq_api_key": "",
                "gemini_api_key": "",
                "two_factor_enabled": False
            }
            
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "two_factor_enabled": row[3]
        }
    except Exception as e:
        logger.error(f"Error fetching user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user settings")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.post("/api/settings/{user_id}")
async def update_user_settings(user_id: str, payload: UserSettingsUpdate):
    """
    Updates the user's API keys and 2FA preferences.
    All provided keys are encrypted BEFORE being inserted into the database.
    Uses ON CONFLICT DO UPDATE (Upsert) to cleanly handle both first-time saves and subsequent edits.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ENCRYPT AT REST: Convert plaintext keys to Fernet tokens
        openai_key = encrypt_key(payload.openai_api_key) if payload.openai_api_key is not None else None
        groq_key = encrypt_key(payload.groq_api_key) if payload.groq_api_key is not None else None
        gemini_key = encrypt_key(payload.gemini_api_key) if payload.gemini_api_key is not None else None

        cursor.execute(
            """
            INSERT INTO user_settings (user_id, openai_api_key, groq_api_key, gemini_api_key, two_factor_enabled, updated_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE 
            SET openai_api_key = COALESCE(EXCLUDED.openai_api_key, user_settings.openai_api_key),
                groq_api_key = COALESCE(EXCLUDED.groq_api_key, user_settings.groq_api_key),
                gemini_api_key = COALESCE(EXCLUDED.gemini_api_key, user_settings.gemini_api_key),
                two_factor_enabled = COALESCE(EXCLUDED.two_factor_enabled, user_settings.two_factor_enabled),
                updated_at = now()
            RETURNING openai_api_key, groq_api_key, gemini_api_key, two_factor_enabled;
            """,
            (user_id, openai_key, groq_key, gemini_key, payload.two_factor_enabled)
        )
        row = cursor.fetchone()
        conn.commit()
        
        # Decrypt them before returning the success response so the UI state remains correct
        return {
            "openai_api_key": decrypt_key(row[0]) or "",
            "groq_api_key": decrypt_key(row[1]) or "",
            "gemini_api_key": decrypt_key(row[2]) or "",
            "two_factor_enabled": row[3]
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user settings")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
