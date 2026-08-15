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
        # Create partial unique index to prevent duplicate system/global models while allowing custom models.
        await run_in_threadpool(cursor.execute, "CREATE UNIQUE INDEX IF NOT EXISTS ai_models_model_id_null_user_idx ON ai_models (model_id) WHERE user_id IS NULL;")

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
        ON CONFLICT (model_id) WHERE user_id IS NULL DO NOTHING;
        """
        # Execute seed block.
        await run_in_threadpool(cursor.execute, seed_sql)


async def get_active_models(user_id: str = None):
    """
    Retrieves all currently active AI models available to a specific user.
    Retrieves active models from system_ai_models plus user custom models from user_ai_models.
    """
    models = []
    # 1. Fetch system active models
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, provider, id as model_id, name, 'System model' as description, FALSE as requires_key, 
                   '' as base_url, category, created_at, credits_per_1k_tokens, tier_badge,
                   input_cost_per_1m, output_cost_per_1m
            FROM system_ai_models
            WHERE is_active = TRUE
            ORDER BY provider ASC, name ASC
            """
        )
        sys_rows = await run_in_threadpool(cursor.fetchall)
        for r in sys_rows:
            models.append({
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4],
                "requires_key": r[5],
                "base_url": r[6],
                "category": r[7] or "General",
                "created_at": r[8].isoformat() if r[8] else None,
                "user_id": None,
                "api_key": "",
                "credits_per_1k_tokens": float(r[9]),
                "tier_badge": r[10],
                "input_cost_per_1m": float(r[11]) if r[11] is not None else 0.0,
                "output_cost_per_1m": float(r[12]) if r[12] is not None else 0.0
            })

    # 2. Fetch user's custom models
    if user_id:
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(
                cursor.execute,
                """
                SELECT id, provider, model_identifier, name, base_url, created_at, user_id, api_key
                FROM user_ai_models
                WHERE is_active = TRUE AND user_id = %s
                ORDER BY provider ASC, name ASC
                """,
                (user_id,)
            )
            user_rows = await run_in_threadpool(cursor.fetchall)
            for r in user_rows:
                models.append({
                    "id": str(r[0]),
                    "provider": r[1],
                    "model_id": r[2],
                    "name": r[3],
                    "description": f"Custom user model: {r[2]}",
                    "requires_key": True,
                    "base_url": r[4],
                    "category": "General",
                    "created_at": r[5].isoformat() if r[5] else None,
                    "user_id": str(r[6]),
                    "api_key": mask_key(decrypt_key(r[7])) if r[7] else "",
                    "credits_per_1k_tokens": 0.0,
                    "tier_badge": "Custom"
                })

    return models


async def get_all_models(user_id: str = None):
    """
    Retrieves all models (both active and inactive) scoped to the user/admin.
    """
    models = []
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, provider, id as model_id, name, 'System model' as description, FALSE as requires_key, 
                   '' as base_url, is_active, category, created_at, credits_per_1k_tokens, tier_badge
            FROM system_ai_models
            ORDER BY provider ASC, name ASC
            """
        )
        sys_rows = await run_in_threadpool(cursor.fetchall)
        for r in sys_rows:
            models.append({
                "id": r[0],
                "provider": r[1],
                "model_id": r[2],
                "name": r[3],
                "description": r[4],
                "requires_key": r[5],
                "base_url": r[6],
                "is_active": r[7],
                "category": r[8] or "General",
                "created_at": r[9].isoformat() if r[9] else None,
                "user_id": None,
                "api_key": "",
                "credits_per_1k_tokens": float(r[10]),
                "tier_badge": r[11]
            })

    if user_id:
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(
                cursor.execute,
                """
                SELECT id, provider, model_identifier, name, base_url, is_active, created_at, user_id, api_key
                FROM user_ai_models
                WHERE user_id = %s
                ORDER BY provider ASC, created_at DESC
                """,
                (user_id,)
            )
            user_rows = await run_in_threadpool(cursor.fetchall)
            for r in user_rows:
                models.append({
                    "id": str(r[0]),
                    "provider": r[1],
                    "model_id": r[2],
                    "name": r[3],
                    "description": f"Custom user model: {r[2]}",
                    "requires_key": True,
                    "base_url": r[4],
                    "is_active": r[5],
                    "category": "General",
                    "created_at": r[6].isoformat() if r[6] else None,
                    "user_id": str(r[7]),
                    "api_key": mask_key(decrypt_key(r[8])) if r[8] else "",
                    "credits_per_1k_tokens": 0.0,
                    "tier_badge": "Custom"
                })

    return models


async def create_model(data: dict, user_id: str = None):
    """
    Registers a new model entry.
    If user_id is provided, creates in user_ai_models.
    If user_id is None, creates in system_ai_models (Admin only).
    """
    async with get_db_cursor_async(commit=True) as cursor:
        if user_id:
            raw_key = data.get("api_key", "")
            enc_key = encrypt_key(raw_key) if raw_key else None
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO user_ai_models (user_id, name, provider, model_identifier, base_url, api_key, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id, provider, model_identifier, name, base_url, is_active, created_at, user_id, api_key;
                """,
                (
                    user_id,
                    data.get("name"),
                    data.get("provider", "openai"),
                    data.get("model_id"),
                    data.get("base_url", ""),
                    enc_key
                )
            )
            r = await run_in_threadpool(cursor.fetchone)
            if r:
                return {
                    "id": str(r[0]),
                    "provider": r[1],
                    "model_id": r[2],
                    "name": r[3],
                    "description": f"Custom user model: {r[2]}",
                    "requires_key": True,
                    "base_url": r[4],
                    "is_active": r[5],
                    "category": "General",
                    "created_at": r[6].isoformat() if r[6] else None,
                    "user_id": str(r[7]),
                    "api_key": mask_key(decrypt_key(r[8])) if r[8] else "",
                    "credits_per_1k_tokens": 0.0,
                    "tier_badge": "Custom"
                }
        else:
            # System model admin creation
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO system_ai_models (id, name, provider, category, credits_per_1k_tokens, tier_badge, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id, name, provider, category, credits_per_1k_tokens, tier_badge, is_active, created_at;
                """,
                (
                    data.get("model_id"),
                    data.get("name"),
                    data.get("provider"),
                    data.get("category", "General"),
                    data.get("credits_per_1k_tokens", 0.1),
                    data.get("tier_badge", "Low Burn")
                )
            )
            r = await run_in_threadpool(cursor.fetchone)
            if r:
                return {
                    "id": r[0],
                    "provider": r[2],
                    "model_id": r[0],
                    "name": r[1],
                    "description": "System model",
                    "requires_key": False,
                    "base_url": "",
                    "is_active": r[6],
                    "category": r[3],
                    "created_at": r[7].isoformat() if r[7] else None,
                    "user_id": None,
                    "api_key": "",
                    "credits_per_1k_tokens": float(r[4]),
                    "tier_badge": r[5]
                }
        return None


async def update_model(model_db_id: str, data: dict, user_id: str = None):
    """
    Updates a model catalog entry configuration or active status.
    Determines system vs user model by parsing model_db_id.
    """
    is_user_model = False
    try:
        import uuid
        uuid.UUID(str(model_db_id))
        is_user_model = True
    except ValueError:
        is_user_model = False

    async with get_db_cursor_async(commit=True) as cursor:
        if is_user_model:
            # 1. Update user custom model
            await run_in_threadpool(
                cursor.execute,
                "SELECT user_id, api_key FROM user_ai_models WHERE id = %s",
                (model_db_id,)
            )
            existing = await run_in_threadpool(cursor.fetchone)
            if not existing or (user_id and str(existing[0]) != user_id):
                return None

            set_clauses = []
            values = []

            if "api_key" in data:
                raw_key = data["api_key"]
                if raw_key and not raw_key.startswith("********"):
                    enc_key = encrypt_key(raw_key)
                    set_clauses.append("api_key = %s")
                    values.append(enc_key)
                elif not raw_key:
                    set_clauses.append("api_key = NULL")

            allowed_keys = ["name", "is_active", "base_url", "provider", "model_id"]
            for key in allowed_keys:
                if key in data:
                    db_col = "model_identifier" if key == "model_id" else key
                    set_clauses.append(f"{db_col} = %s")
                    values.append(data[key])

            if not set_clauses:
                return None

            values.append(model_db_id)
            query = f"""
            UPDATE user_ai_models
            SET {', '.join(set_clauses)}
            WHERE id = %s
            RETURNING id, provider, model_identifier, name, base_url, is_active, created_at, user_id, api_key;
            """
            await run_in_threadpool(cursor.execute, query, tuple(values))
            r = await run_in_threadpool(cursor.fetchone)
            if r:
                return {
                    "id": str(r[0]),
                    "provider": r[1],
                    "model_id": r[2],
                    "name": r[3],
                    "description": f"Custom user model: {r[2]}",
                    "requires_key": True,
                    "base_url": r[4],
                    "is_active": r[5],
                    "category": "General",
                    "created_at": r[6].isoformat() if r[6] else None,
                    "user_id": str(r[7]),
                    "api_key": mask_key(decrypt_key(r[8])) if r[8] else "",
                    "credits_per_1k_tokens": 0.0,
                    "tier_badge": "Custom"
                }
        else:
            # 2. Update system model
            await run_in_threadpool(
                cursor.execute,
                "SELECT id FROM system_ai_models WHERE id = %s",
                (model_db_id,)
            )
            existing = await run_in_threadpool(cursor.fetchone)
            if not existing:
                return None

            # Standard users can only toggle is_active. Admin (user_id = None) can update everything.
            set_clauses = []
            values = []

            if user_id:
                # Regular user toggling status
                if "is_active" in data:
                    set_clauses.append("is_active = %s")
                    values.append(data["is_active"])
            else:
                # Admin updating system model attributes
                allowed_keys = ["name", "is_active", "provider", "category", "credits_per_1k_tokens", "tier_badge"]
                for key in allowed_keys:
                    if key in data:
                        set_clauses.append(f"{key} = %s")
                        values.append(data[key])

            if not set_clauses:
                return None

            values.append(model_db_id)
            query = f"""
            UPDATE system_ai_models
            SET {', '.join(set_clauses)}
            WHERE id = %s
            RETURNING id, name, provider, category, credits_per_1k_tokens, tier_badge, is_active, created_at;
            """
            await run_in_threadpool(cursor.execute, query, tuple(values))
            r = await run_in_threadpool(cursor.fetchone)
            if r:
                return {
                    "id": r[0],
                    "provider": r[2],
                    "model_id": r[0],
                    "name": r[1],
                    "description": "System model",
                    "requires_key": False,
                    "base_url": "",
                    "is_active": r[6],
                    "category": r[3],
                    "created_at": r[7].isoformat() if r[7] else None,
                    "user_id": None,
                    "api_key": "",
                    "credits_per_1k_tokens": float(r[4]),
                    "tier_badge": r[5]
                }
        return None


async def delete_model(model_db_id: str, user_id: str = None):
    """
    Deletes a user custom model entry from user_ai_models.
    Only allows users to delete their own custom models.
    """
    is_user_model = False
    try:
        import uuid
        uuid.UUID(str(model_db_id))
        is_user_model = True
    except ValueError:
        is_user_model = False

    if not is_user_model:
        return 0

    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id FROM user_ai_models WHERE id = %s",
            (model_db_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if not row or (user_id and str(row[0]) != user_id):
            return 0

        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM user_ai_models WHERE id = %s AND user_id = %s",
            (model_db_id, user_id)
        )
        return cursor.rowcount


