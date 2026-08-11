"""
================================================================================
AI MODELS DATABASE CATALOG REPOSITORY LAYER (model_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) / repository layer for managing
the catalog of Large Language Models (LLMs) and foundation models (e.g. OpenAI,
Anthropic, Google, HuggingFace, OpenRouter, Groq). It supports:
1. Catalog Initialization & Seeding: Creating the `ai_models` table, migrations,
   and seeding pre-defined models.
2. Model Discovery: Fetching active models for UI selection dropdowns.
3. Custom Model Integrations: Enabling users to define custom LLMs/endpoint configurations,
   encrypting and masking custom endpoint keys.
4. Security & Permissions: Enforcing rules on model modification—preventing regular users
   from editing system models (except toggling active status) or other users' custom models.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `json`: Standard JSON library.
   - `get_db_cursor_async` and `run_in_threadpool`: Core DB access interfaces.
   - `encrypt_key`, `decrypt_key`: Security module helpers for key encryption.

2. Helpers & Initializers:
   - `mask_key(key)`: Truncates and obscures keys (e.g. "sk-o********abcd") to prevent leakages.
   - `init_ai_models_table()`: Sets up the database catalog, runs migrations (schema adjustments),
     and seeds standard Groq, OpenRouter, OpenAI, Claude, Gemini, and HuggingFace models.

3. Repository Functions:
   - `get_active_models(user_id)`: Fetches active models scoped to global system defaults plus
     the user's own custom models, decrypting and masking API keys.
   - `get_all_models(user_id)`: Returns all models (including inactive ones) scoped to the user.
   - `create_model(data, user_id)`: Inserts a custom user model record, encrypting credentials.
   - `update_model(model_db_id, data, user_id)`: Safely updates attributes. Enforces rules:
     - Regular users cannot update properties of system models (only `is_active` status).
     - Users can only edit custom models they created.
     - Custom API keys are encrypted at rest and masked.
   - `delete_model(model_db_id, user_id)`: Deletes custom models, verifying ownership first.
"""

import json
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from core.security import encrypt_key, decrypt_key

def mask_key(key: str) -> str:
    """
    Masks a sensitive API key to prevent exposing it in UI dashboards.

    Purpose:
        Redacts intermediate characters of a credential string while leaving the prefix and
        suffix visible for verification (e.g. "sk-u...abcd").

    Parameters:
        key (str): The raw decrypted credential string.

    Returns:
        str: The masked credential string.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - None.
    """
    # If key is empty or None, return empty string.
    if not key:
        return ""
    # If the key is too short, return a generic placeholder.
    if len(key) <= 8:
        return "********"
    # Slice the string to keep the first 4 and last 4 characters, masking the rest.
    return f"{key[:4]}********{key[-4:]}"


async def init_ai_models_table():
    """
    Ensures the `ai_models` database table exists and is populated with default models.

    Purpose:
        Database bootstrap operation. Runs migrations and seeds default providers (Groq, OpenRouter,
        OpenAI, Anthropic, Gemini, HuggingFace) on installation startup.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Creates the `ai_models` table if missing.
        - Runs schema updates (appends `api_key` and `user_id` columns, drops model constraints).
        - Populates catalog using seed statements with ON CONFLICT resolution rules.
        - Commits all modifications.

    Errors / Exceptions:
        - May raise database execution exceptions.
    """
    # Open database connection in a DDL write transaction (commit=True).
    async with get_db_cursor_async(commit=True) as cursor:
        # Create table schema if missing.
        await run_in_threadpool(
            cursor.execute,
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                provider VARCHAR(50) NOT NULL,
                model_id VARCHAR(100) NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                requires_key BOOLEAN DEFAULT FALSE,
                base_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                category VARCHAR(50) DEFAULT 'General',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # --- Migrations & Updates ---
        # Add column for custom model API key storage.
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS api_key TEXT;")
        # Link custom models to the creator's user account with CASCADE deletion rules.
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE CASCADE;")
        # Drop unique constraints on model_id to allow different users to register the same model_id.
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models DROP CONSTRAINT IF EXISTS ai_models_model_id_key;")

        # --- Seed Data statements ---
        # Lists standard AI models. Custom key models start as inactive (`is_active = FALSE`).
        seed_sql = """
        INSERT INTO ai_models (provider, model_id, name, description, requires_key, category, is_active)
        VALUES 
            -- Groq Models (Free)
            ('groq', 'llama-3.3-70b-versatile', 'Llama 3.3 70B (Free - Smart)', 'High intelligence 70B model powered by Groq', FALSE, 'General', TRUE),
            ('groq', 'llama-3.1-8b-instant', 'Llama 3.1 8B (Free - Fast)', 'Fast, low-latency open model powered by Groq', FALSE, 'Fast', TRUE),
            ('groq', 'deepseek-r1-distill-llama-70b', 'DeepSeek R1 Distill 70B (Free)', 'Reasoning model powered by Groq Llama 70B', FALSE, 'Reasoning', TRUE),
            ('groq', 'mixtral-8x7b-32768', 'Mixtral 8x7B (Large Context)', 'High context window mixture of experts model', FALSE, 'General', TRUE),
            ('groq', 'qwen-2.5-32b', 'Qwen 2.5 32B (Coding/Logic)', 'Alibaba Qwen model optimized for coding & logic', FALSE, 'Coding', TRUE),
            ('groq', 'gemma2-9b-it', 'Gemma 2 9B (Free - Google)', 'Google lightweight open model via Groq', FALSE, 'Fast', TRUE),

            -- OpenRouter Models (Free Tier with OpenRouter API Key)
            ('openrouter', 'deepseek/deepseek-r1:free', 'DeepSeek R1 (Free - OpenRouter)', 'DeepSeek reasoning model via OpenRouter free tier', TRUE, 'Reasoning', FALSE),
            ('openrouter', 'deepseek/deepseek-chat:free', 'DeepSeek V3 (Free - OpenRouter)', 'DeepSeek flagship chat model via OpenRouter free tier', TRUE, 'General', FALSE),
            ('openrouter', 'meta-llama/llama-3.3-70b-instruct:free', 'Llama 3.3 70B (Free - OpenRouter)', 'Meta flagship open model via OpenRouter free tier', TRUE, 'General', FALSE),
            ('openrouter', 'qwen/qwen-2.5-coder-32b-instruct:free', 'Qwen 2.5 Coder 32B (Free - OpenRouter)', 'Alibaba flagship coding model via OpenRouter free tier', TRUE, 'Coding', FALSE),
            ('openrouter', 'google/gemini-2.0-flash-exp:free', 'Gemini 2.0 Flash (Free - OpenRouter)', 'Google Flash experimental model via OpenRouter free tier', TRUE, 'Fast', FALSE),

            -- OpenAI Models (Paid)
            ('openai', 'gpt-4o', 'GPT-4o (Paid - Flagship)', 'OpenAI flagship multimodal reasoning model', TRUE, 'Reasoning', FALSE),
            ('openai', 'gpt-4o-mini', 'GPT-4o Mini (Paid - Fast)', 'Fast, cost-effective OpenAI flagship mini model', TRUE, 'Fast', FALSE),
            ('openai', 'o1', 'OpenAI o1 (Paid - Advanced Reasoning)', 'Advanced reasoning model for complex STEM & coding', TRUE, 'Reasoning', FALSE),
            ('openai', 'o1-mini', 'OpenAI o1 Mini (Paid - Fast Reasoning)', 'Fast reasoning model for coding and STEM queries', TRUE, 'Fast', FALSE),
            ('openai', 'gpt-4-turbo', 'GPT-4 Turbo (Paid - Vision)', 'High capability GPT-4 Turbo model with vision support', TRUE, 'General', FALSE),

            -- Anthropic Claude Models (Paid)
            ('anthropic', 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (Paid - Flagship)', 'Anthropic flagship reasoning and coding model', TRUE, 'Reasoning', FALSE),
            ('anthropic', 'claude-3-5-haiku-20241022', 'Claude 3.5 Haiku (Paid - Fast)', 'Anthropic lightning fast lightweight model', TRUE, 'Fast', FALSE),
            ('anthropic', 'claude-3-opus-20240229', 'Claude 3 Opus (Paid - High Intelligence)', 'Anthropic most intelligent model for complex tasks', TRUE, 'Reasoning', FALSE),

            -- Google Gemini Models (Paid / API Key)
            ('gemini', 'gemini-2.0-flash-exp', 'Gemini 2.0 Flash (Fast / Multimodal)', 'Google next-gen high speed multimodal model', TRUE, 'Fast', FALSE),
            ('gemini', 'gemini-1.5-pro', 'Gemini 1.5 Pro (2M Token Context)', 'Google flagship model with massive 2M token context', TRUE, 'Reasoning', FALSE),
            ('gemini', 'gemini-1.5-flash', 'Gemini 1.5 Flash (Lightweight)', 'Google fast and efficient model for general tasks', TRUE, 'Fast', FALSE),

            -- HuggingFace Models
            ('huggingface', 'meta-llama/Llama-3.3-70B-Instruct', 'Llama 3.3 70B (HF Endpoint)', 'HuggingFace inference endpoint model', TRUE, 'General', FALSE),
            ('huggingface', 'Qwen/Qwen2.5-Coder-32B-Instruct', 'Qwen 2.5 Coder 32B (HF Endpoint)', 'HuggingFace coding inference endpoint model', TRUE, 'Coding', FALSE),
            ('huggingface', 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 'DeepSeek R1 Qwen 32B (HF Endpoint)', 'HuggingFace DeepSeek reasoning model endpoint', TRUE, 'Reasoning', FALSE),

            -- NVIDIA NIM Models (Paid / API Key)
            ('nvidia', 'nvidia/llama-3.1-nemotron-70b-instruct', 'Llama 3.1 Nemotron 70B (NVIDIA NIM)', 'NVIDIA Nemotron model optimized for helpfulness & correctness', TRUE, 'General', FALSE),
            ('nvidia', 'nvidia/llama-3.2-11b-vision-instruct', 'Llama 3.2 11B Vision (NVIDIA NIM)', 'NVIDIA lightweight multimodal vision model', TRUE, 'Fast', FALSE),
            ('nvidia', 'nvidia/llama-3.3-70b-instruct', 'Llama 3.3 70B (NVIDIA NIM)', 'Meta flagship open model powered by NVIDIA NIM', TRUE, 'General', FALSE)
        ON CONFLICT (model_id) DO NOTHING;
        """
        # Execute seed block.
        await run_in_threadpool(cursor.execute, seed_sql)


async def get_active_models(user_id: str = None):
    """
    Retrieves all currently active AI models available to a specific user.

    Purpose:
        Provides options for user settings and agent creation forms. Retrieves global active models
        (`user_id IS NULL`) plus custom models created by the user requesting the active list.

    Parameters:
        user_id (str, optional): Unique database user identifier. Defaults to None.

    Returns:
        list of dict: A list of model configuration dictionaries. API keys are decrypted
                      and masked before formatting.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, provider, model_id, name, description, requires_key, base_url, category, created_at, user_id, api_key
            FROM ai_models
            WHERE is_active = TRUE AND (user_id IS NULL OR user_id = %s)
            ORDER BY provider ASC, name ASC
            """,
            (user_id,)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        # Parse output tuple array to standard Python dictionary structures.
        return [
            {
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4] or "",
                "requires_key": r[5],
                "base_url": r[6] or "",
                "category": r[7] or "General",
                # Convert timestamps to standardized ISO formats.
                "created_at": r[8].isoformat() if r[8] else None,
                "user_id": str(r[9]) if r[9] else None,
                # Crucial security protection: decrypt key and mask it so the full token is never exposed in API payloads.
                "api_key": mask_key(decrypt_key(r[10])) if r[10] else ""
            }
            for r in rows
        ]


async def get_all_models(user_id: str = None):
    """
    Retrieves all models (both active and inactive) scoped to the user.

    Purpose:
        Populates administrative listings, enabling users to toggle active states or view
        unconfigured integrations.

    Parameters:
        user_id (str, optional): Unique database user identifier. Defaults to None.

    Returns:
        list of dict: A list of model configuration dictionaries.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, provider, model_id, name, description, requires_key, base_url, is_active, category, created_at, user_id, api_key
            FROM ai_models
            WHERE user_id IS NULL OR user_id = %s
            ORDER BY provider ASC, created_at DESC
            """,
            (user_id,)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4] or "",
                "requires_key": r[5],
                "base_url": r[6] or "",
                "is_active": r[7],
                "category": r[8] or "General",
                "created_at": r[9].isoformat() if r[9] else None,
                "user_id": str(r[10]) if r[10] else None,
                # Decrypt and mask secret keys.
                "api_key": mask_key(decrypt_key(r[11])) if r[11] else ""
            }
            for r in rows
        ]


async def create_model(data: dict, user_id: str = None):
    """
    Adds a new model configuration to the catalog.

    Purpose:
        Allows users to register custom API models (such as custom HuggingFace endpoints).
        Encrypts provided credentials before saving them.

    Parameters:
        data (dict): Model definition attributes:
            - provider (str): Endpoint provider.
            - model_id (str): Model name ID.
            - name (str): Display title.
            - description (str, optional): Summary.
            - requires_key (bool, optional): Indicates if authentication credentials are required.
            - base_url (str, optional): Target base endpoint URL.
            - category (str, optional): Group category labels.
            - api_key (str, optional): Plaintext credentials key.
        user_id (str, optional): Unique database user identifier. Defaults to None.

    Returns:
        dict | None: The created model configuration dictionary, or None if creation failed.

    Side Effects / State Changes:
        - Writes a new row to the `ai_models` table.
        - Commits modifications to the database (commit=True).

    Errors / Exceptions:
        - May raise database constraint errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        raw_key = data.get("api_key", "")
        # Protect credentials: encrypt keys using the core security module.
        enc_key = encrypt_key(raw_key) if raw_key else None
        
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO ai_models (provider, model_id, name, description, requires_key, base_url, category, is_active, user_id, api_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)
            RETURNING id, provider, model_id, name, description, requires_key, base_url, is_active, category, created_at, user_id, api_key;
            """,
            (
                data.get("provider", "openai"),
                data.get("model_id"),
                data.get("name"),
                data.get("description", ""),
                data.get("requires_key", False),
                data.get("base_url", ""),
                data.get("category", "General"),
                user_id,
                enc_key
            )
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4] or "",
                "requires_key": r[5],
                "base_url": r[6] or "",
                "is_active": r[7],
                "category": r[8] or "General",
                "created_at": r[9].isoformat() if r[9] else None,
                "user_id": str(r[10]) if r[10] else None,
                "api_key": mask_key(decrypt_key(r[11])) if r[11] else ""
            }
        return None


async def update_model(model_db_id: str, data: dict, user_id: str = None):
    """
    Updates the configuration or active status of a model in the catalog.

    Purpose:
        Modifies properties of a model catalog entry. Enforces access control permissions:
        1. Users can toggle the `is_active` flag of system models, but cannot edit other fields.
        2. Users can modify all fields of custom models they created.
        3. Users cannot edit or toggle models owned by other users.

    Parameters:
        model_db_id (str): Database key UUID of the target model.
        data (dict): Key-value pairs containing model updates.
        user_id (str, optional): Unique user database ID. Defaults to None.

    Returns:
        dict | None: The updated model configuration dictionary, or None.

    Side Effects / State Changes:
        - Modifies columns in `ai_models`.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Query database to verify permissions.
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, api_key FROM ai_models WHERE id = %s",
            (model_db_id,)
        )
        existing = await run_in_threadpool(cursor.fetchone)
        # Exit early if the model does not exist.
        if not existing:
            return None
        
        db_user_id, db_api_key = existing
        # Access Check: If the model has a user owner, confirm it matches the caller's user_id.
        if db_user_id is not None and str(db_user_id) != user_id:
            # Unauthorized to modify this model.
            return None
        # Access Check: If it is a global system model (`db_user_id IS NULL`), users can only toggle `is_active`.
        if db_user_id is None and "is_active" not in data:
            # Unauthorized to edit properties on a global system model.
            return None

        set_clauses = []
        values = []
        
        # Step 2: Handle API key encryption updates specifically.
        if "api_key" in data:
            raw_key = data["api_key"]
            # If the user inputted a new plaintext key (not the masked placeholder starting with stars), encrypt and store it.
            if raw_key and not raw_key.startswith("********"):
                enc_key = encrypt_key(raw_key)
                set_clauses.append("api_key = %s")
                values.append(enc_key)
            # If they cleared the key, set the column to NULL.
            elif not raw_key:
                set_clauses.append("api_key = NULL")

        # Step 3: Loop through other allowed whitelisted columns.
        allowed_keys = ["name", "description", "requires_key", "base_url", "is_active", "category", "provider", "model_id"]
        for key in allowed_keys:
            if key in data:
                # Double-check rules: skip updating metadata columns on global system models (only allow is_active).
                if db_user_id is None and key != "is_active":
                    continue
                set_clauses.append(f"{key} = %s")
                values.append(data[key])

        # If no clauses were generated (e.g. invalid keys), exit early.
        if not set_clauses:
            return None

        # Bind the model ID to the final WHERE clause query parameter.
        values.append(model_db_id)
        # Format update statement query.
        query = f"""
        UPDATE ai_models
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING id, provider, model_id, name, description, requires_key, base_url, is_active, category, created_at, user_id, api_key;
        """
        # Execute query.
        await run_in_threadpool(cursor.execute, query, tuple(values))
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4] or "",
                "requires_key": r[5],
                "base_url": r[6] or "",
                "is_active": r[7],
                "category": r[8] or "General",
                "created_at": r[9].isoformat() if r[9] else None,
                "user_id": str(r[10]) if r[10] else None,
                "api_key": mask_key(decrypt_key(r[11])) if r[11] else ""
            }
        return None


async def delete_model(model_db_id: str, user_id: str = None):
    """
    Deletes a model entry from the database.

    Purpose:
        Permanently deletes a custom model definition from the database catalog. Enforces permissions
        so that users can only delete custom models they created.

    Parameters:
        model_db_id (str): The unique database UUID of the target model.
        user_id (str, optional): The unique database ID of the user requesting deletion. Defaults to None.

    Returns:
        int: The number of rows affected by the deletion statement (typically 1).

    Side Effects / State Changes:
        - Deletes a row in `ai_models`.
        - Commits change.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Check permissions: verify ownership before execution.
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id FROM ai_models WHERE id = %s",
            (model_db_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        # Deny deletion if the model is a global system model (`row[0] is None`) or belongs to someone else.
        if not row or row[0] is None or str(row[0]) != user_id:
            return 0
            
        # Execute deletion statement.
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM ai_models WHERE id = %s AND user_id = %s",
            (model_db_id, user_id)
        )
        return cursor.rowcount

