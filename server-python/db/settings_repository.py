from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_settings(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled
            FROM user_settings
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def upsert_user_settings(
    user_id: str, 
    openai_key: str = None, 
    groq_key: str = None, 
    gemini_key: str = None, 
    openrouter_key: str = None,
    anthropic_key: str = None,
    huggingface_key: str = None,
    two_factor_enabled: bool = None
):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_settings (user_id, openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE 
            SET openai_api_key = COALESCE(EXCLUDED.openai_api_key, user_settings.openai_api_key),
                groq_api_key = COALESCE(EXCLUDED.groq_api_key, user_settings.groq_api_key),
                gemini_api_key = COALESCE(EXCLUDED.gemini_api_key, user_settings.gemini_api_key),
                openrouter_api_key = COALESCE(EXCLUDED.openrouter_api_key, user_settings.openrouter_api_key),
                anthropic_api_key = COALESCE(EXCLUDED.anthropic_api_key, user_settings.anthropic_api_key),
                huggingface_api_key = COALESCE(EXCLUDED.huggingface_api_key, user_settings.huggingface_api_key),
                two_factor_enabled = COALESCE(EXCLUDED.two_factor_enabled, user_settings.two_factor_enabled),
                updated_at = now()
            RETURNING openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled;
            """,
            (user_id, openai_key, groq_key, gemini_key, openrouter_key, anthropic_key, huggingface_key, two_factor_enabled)
        )
        return await run_in_threadpool(cursor.fetchone)
