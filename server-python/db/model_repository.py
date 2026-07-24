import json
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from core.security import encrypt_key, decrypt_key

def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "********"
    return f"{key[:4]}********{key[-4:]}"

async def init_ai_models_table():
    """Ensure the ai_models table exists and contains seed data."""
    async with get_db_cursor_async(commit=True) as cursor:
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
        # Migrations
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS api_key TEXT;")
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;")
        await run_in_threadpool(cursor.execute, "ALTER TABLE ai_models DROP CONSTRAINT IF EXISTS ai_models_model_id_key;")

        # Seed defaults
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
            ('huggingface', 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 'DeepSeek R1 Qwen 32B (HF Endpoint)', 'HuggingFace DeepSeek reasoning model endpoint', TRUE, 'Reasoning', FALSE)
        ON CONFLICT (model_id) DO NOTHING;
        """
        await run_in_threadpool(cursor.execute, seed_sql)

async def get_active_models(user_id: str = None):
    """Retrieve all active models for agent creation / settings dropdowns."""
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
                "created_at": r[8].isoformat() if r[8] else None,
                "user_id": str(r[9]) if r[9] else None,
                "api_key": mask_key(decrypt_key(r[10])) if r[10] else ""
            }
            for r in rows
        ]

async def get_all_models(user_id: str = None):
    """Retrieve all models (active and inactive) for admin management."""
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
                "api_key": mask_key(decrypt_key(r[11])) if r[11] else ""
            }
            for r in rows
        ]

async def create_model(data: dict, user_id: str = None):
    """Add a new model entry into the catalog."""
    async with get_db_cursor_async(commit=True) as cursor:
        raw_key = data.get("api_key", "")
        enc_key = encrypt_key(raw_key) if raw_key else None
        
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO ai_models (provider, model_id, name, description, requires_key, base_url, category, is_active, user_id, api_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s)
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
    """Update model fields or active status."""
    async with get_db_cursor_async(commit=True) as cursor:
        # First ensure the user has access to update this model (cannot update system models or other user's models)
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, api_key FROM ai_models WHERE id = %s",
            (model_db_id,)
        )
        existing = await run_in_threadpool(cursor.fetchone)
        if not existing:
            return None
        
        db_user_id, db_api_key = existing
        if db_user_id is not None and str(db_user_id) != user_id:
            # Unauthorized to modify this user's model
            return None
        if db_user_id is None and "is_active" not in data:
            # Users can toggle is_active for system models, but cannot update other properties
            return None

        set_clauses = []
        values = []
        
        # Handle API key encryption specifically
        if "api_key" in data:
            raw_key = data["api_key"]
            if raw_key and not raw_key.startswith("********"):
                enc_key = encrypt_key(raw_key)
                set_clauses.append("api_key = %s")
                values.append(enc_key)
            elif not raw_key:
                set_clauses.append("api_key = NULL")

        allowed_keys = ["name", "description", "requires_key", "base_url", "is_active", "category", "provider", "model_id"]
        for key in allowed_keys:
            if key in data:
                # System models can only have their is_active updated by users
                if db_user_id is None and key != "is_active":
                    continue
                set_clauses.append(f"{key} = %s")
                values.append(data[key])

        if not set_clauses:
            return None

        values.append(model_db_id)
        query = f"""
        UPDATE ai_models
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING id, provider, model_id, name, description, requires_key, base_url, is_active, category, created_at, user_id, api_key;
        """
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
    """Delete a model entry."""
    async with get_db_cursor_async(commit=True) as cursor:
        # Check permissions: can only delete user-specific models
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id FROM ai_models WHERE id = %s",
            (model_db_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if not row or row[0] is None or str(row[0]) != user_id:
            return 0
            
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM ai_models WHERE id = %s AND user_id = %s",
            (model_db_id, user_id)
        )
        return cursor.rowcount
