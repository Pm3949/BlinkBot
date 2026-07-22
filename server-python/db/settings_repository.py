from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_settings(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled, share_keys
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
    two_factor_enabled: bool = None,
    share_keys: bool = None
):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_settings (user_id, openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled, share_keys, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE 
            SET openai_api_key = COALESCE(EXCLUDED.openai_api_key, user_settings.openai_api_key),
                groq_api_key = COALESCE(EXCLUDED.groq_api_key, user_settings.groq_api_key),
                gemini_api_key = COALESCE(EXCLUDED.gemini_api_key, user_settings.gemini_api_key),
                openrouter_api_key = COALESCE(EXCLUDED.openrouter_api_key, user_settings.openrouter_api_key),
                anthropic_api_key = COALESCE(EXCLUDED.anthropic_api_key, user_settings.anthropic_api_key),
                huggingface_api_key = COALESCE(EXCLUDED.huggingface_api_key, user_settings.huggingface_api_key),
                two_factor_enabled = COALESCE(EXCLUDED.two_factor_enabled, user_settings.two_factor_enabled),
                share_keys = COALESCE(EXCLUDED.share_keys, user_settings.share_keys),
                updated_at = now()
            RETURNING openai_api_key, groq_api_key, gemini_api_key, openrouter_api_key, anthropic_api_key, huggingface_api_key, two_factor_enabled, share_keys;
            """,
            (user_id, openai_key, groq_key, gemini_key, openrouter_key, anthropic_key, huggingface_key, two_factor_enabled, share_keys)
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_effective_user_settings(user_id: str):
    settings = await get_user_settings(user_id)
    if settings and any(settings[i] for i in range(6)):
        return settings
        
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT s.openai_api_key, s.groq_api_key, s.gemini_api_key, s.openrouter_api_key, s.anthropic_api_key, s.huggingface_api_key, s.two_factor_enabled, s.share_keys
            FROM user_settings s
            JOIN workspaces w ON s.user_id = w.owner_id
            JOIN workspace_members m ON w.id = m.workspace_id
            WHERE m.user_id = %s AND s.share_keys = TRUE
            LIMIT 1;
            """,
            (user_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return row
            
    return settings
