import logging
from fastapi import HTTPException
from database import get_db_connection
from core.security import encrypt_key, decrypt_key

logger = logging.getLogger(__name__)


async def handle_get_user_settings(user_id: str):
    """
    What it does: Fetches a user's saved API keys and 2FA settings from the database. It decrypts the keys on the fly using the system's Fernet master key before returning them.
    Args:
        user_id (str): The ID of the user whose settings are being fetched.
    Returns: A dictionary of the decrypted user settings.
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


async def handle_update_user_settings(
    user_id: str,
    openai_api_key: str = None,
    groq_api_key: str = None,
    gemini_api_key: str = None,
    two_factor_enabled: bool = None
):
    """
    What it does: Updates the user's API keys and 2FA preferences. Crucially, all provided plaintext keys are encrypted securely BEFORE being saved to the database (encryption at rest).
    Args:
        user_id (str): The ID of the user updating their settings.
        openai_api_key (str, optional): The OpenAI key to save.
        groq_api_key (str, optional): The Groq key to save.
        gemini_api_key (str, optional): The Gemini key to save.
        two_factor_enabled (bool, optional): 2FA preference.
    Returns: A dictionary of the newly saved, decrypted user settings.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        openai_key = encrypt_key(openai_api_key) if openai_api_key is not None else None
        groq_key = encrypt_key(groq_api_key) if groq_api_key is not None else None
        gemini_key = encrypt_key(gemini_api_key) if gemini_api_key is not None else None

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
            (user_id, openai_key, groq_key, gemini_key, two_factor_enabled)
        )
        row = cursor.fetchone()
        conn.commit()
        
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
