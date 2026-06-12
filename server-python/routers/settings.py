import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

class UserSettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    two_factor_enabled: Optional[bool] = None

@router.get("/api/settings/{user_id}")
async def get_user_settings(user_id: str):
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
        
        if not row:
            return {
                "openai_api_key": "",
                "groq_api_key": "",
                "gemini_api_key": "",
                "two_factor_enabled": False
            }
            
        return {
            "openai_api_key": row[0],
            "groq_api_key": row[1],
            "gemini_api_key": row[2],
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
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            (user_id, payload.openai_api_key, payload.groq_api_key, payload.gemini_api_key, payload.two_factor_enabled)
        )
        row = cursor.fetchone()
        conn.commit()
        
        return {
            "openai_api_key": row[0],
            "groq_api_key": row[1],
            "gemini_api_key": row[2],
            "two_factor_enabled": row[3]
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user settings")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
