"""
================================================================================
USER SETTINGS AND OAUTH/API KEYS DATABASE REPOSITORY LAYER (settings_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database integration keys and configurations (e.g. OpenAI, Groq, Anthropic,
HuggingFace, Gemini, OpenRouter API keys) as well as security preferences (2FA and key sharing settings)
defined under `user_settings`. It supports:
1. Configuration retrieval: Fetches a user's settings profile.
2. Upsert (Insert-or-Update): Creates or modifies user settings. Uses an `ON CONFLICT (user_id)` update
   clause combined with SQL `COALESCE` to update only the fields that are actively provided, preserving
   pre-existing settings for unspecified parameters.
3. Shared Credentials (Effective Settings Resolution): A key-sharing system. If a workspace member
   has not configured their own API keys, RAGMate falls back to checking if the workspace Owner has
   enabled key-sharing (`share_keys = TRUE`) and inherits the owner's keys to execute LLM transactions.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async` and `run_in_threadpool`: Core DB access interfaces.

2. Repository Functions:
   - `get_user_settings(user_id)`: Fetches settings.
   - `upsert_user_settings(...)`: Runs insert statements. Merges inputs using `COALESCE(EXCLUDED.field, user_settings.field)`.
   - `get_effective_user_settings(user_id)`: Resolves active keys. Checks the user's settings first.
     If empty, joins workspaces and members to locate the owner's settings, checking if `share_keys` is active.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_settings(user_id: str):
    """
    Retrieves the configuration settings profile for a specific user.

    Purpose:
        Fetches stored API credentials, 2FA states, and sharing flags from `user_settings`.

    Parameters:
        user_id (str): The unique database user UUID.

    Returns:
        tuple | None: A tuple of settings values:
                      (openai_key, groq_key, gemini_key, openrouter_key, anthropic_key, huggingface_key, 2fa_enabled, share_keys)
                      or None if the record does not exist.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database execution exceptions.
    """
    # Open database connection in a read-only transaction (commit=False).
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
    """
    Creates or updates a user's settings profile.

    Purpose:
        Saves API credentials and configuration preferences. Uses `ON CONFLICT (user_id) DO UPDATE`
        with `COALESCE(EXCLUDED.field, user_settings.field)` to dynamically merge values—only replacing
        attributes that are explicitly provided, preserving existing data for any parameters passed as None.

    Parameters:
        user_id (str): The unique database user UUID.
        openai_key (str, optional): OpenAI API key. Defaults to None.
        groq_key (str, optional): Groq API key. Defaults to None.
        gemini_key (str, optional): Gemini API key. Defaults to None.
        openrouter_key (str, optional): OpenRouter API key. Defaults to None.
        anthropic_key (str, optional): Anthropic API key. Defaults to None.
        huggingface_key (str, optional): HuggingFace API key. Defaults to None.
        two_factor_enabled (bool, optional): Toggles 2FA security. Defaults to None.
        share_keys (bool, optional): Toggles key sharing. Defaults to None.

    Returns:
        tuple | None: The updated settings row tuple, or None.

    Side Effects / State Changes:
        - Inserts a new row or updates an existing row in the `user_settings` table.
        - Commits updates to the database (commit=True).

    Errors / Exceptions:
        - May raise database validation errors.
    """
    # Open database connection in a write transaction (commit=True).
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
    """
    Resolves the active API settings key configuration for a user, handling key-sharing fallbacks.

    Purpose:
        If a user has configured their own API keys, returns them. If not, checks if they are a
        member of a workspace whose owner has enabled key-sharing (`share_keys = TRUE`). If so,
        resolves and returns the owner's keys as the active configuration.

    Parameters:
        user_id (str): The unique database user UUID.

    Returns:
        tuple | None: The active settings row tuple, or None.

    Side Effects / State Changes:
        - None. Read-only queries.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Step 1: Fetch the user's own settings.
    settings = await get_user_settings(user_id)
    # If the user has configured at least one API key, return their settings directly.
    # We check indices 0 to 5 (the credential slots).
    if settings and any(settings[i] for i in range(6)):
        return settings
        
    # Step 2: Fallback query if no personal keys are configured.
    # Join user_settings (s) with workspaces (w) on s.user_id = w.owner_id,
    # and join with workspace_members (m) on w.id = m.workspace_id.
    # Filters where the caller is a member (m.user_id = %s) and the owner allows key sharing (s.share_keys = TRUE).
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
        # If shared owner settings are found, return them.
        if row:
            return row
            
    # Fallback to returning the user's own settings (even if empty).
    return settings

