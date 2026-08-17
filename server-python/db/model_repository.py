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
from core.database import get_db_cursor_async
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



async def get_active_models(user_id: str = None):
    """
    Retrieves all currently active AI models available to a specific user.
    Uses a single UNION ALL query to fetch system_ai_models + user_ai_models
    in one DB round-trip instead of two sequential queries.
    """
    models = []

    if user_id:
        # ── Single UNION ALL: system models + this user's custom models ──────────
        query = """
            SELECT
                id::text            AS id,
                provider,
                id                  AS model_id,
                name,
                'System model'      AS description,
                FALSE               AS requires_key,
                ''                  AS base_url,
                COALESCE(category, 'General') AS category,
                created_at,
                credits_per_1k_tokens::float,
                tier_badge,
                COALESCE(input_cost_per_1m,  0.0)::float AS input_cost_per_1m,
                COALESCE(output_cost_per_1m, 0.0)::float AS output_cost_per_1m,
                NULL::uuid          AS user_id,
                NULL::text          AS api_key
            FROM system_ai_models
            WHERE is_active = TRUE

            UNION ALL

            SELECT
                id::text            AS id,
                provider,
                model_identifier    AS model_id,
                name,
                'Custom user model: ' || model_identifier AS description,
                TRUE                AS requires_key,
                base_url,
                'General'           AS category,
                created_at,
                0.0::float          AS credits_per_1k_tokens,
                'Custom'            AS tier_badge,
                0.0::float          AS input_cost_per_1m,
                0.0::float          AS output_cost_per_1m,
                user_id,
                api_key
            FROM user_ai_models
            WHERE is_active = TRUE AND user_id = %s

            ORDER BY provider ASC, name ASC
        """
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(cursor.execute, query, (user_id,))
            rows = await run_in_threadpool(cursor.fetchall)
    else:
        # ── System models only (no user_id provided) ──────────────────────────
        query = """
            SELECT
                id::text, provider, id, name,
                'System model', FALSE, '',
                COALESCE(category, 'General'), created_at,
                credits_per_1k_tokens::float, tier_badge,
                COALESCE(input_cost_per_1m,  0.0)::float,
                COALESCE(output_cost_per_1m, 0.0)::float,
                NULL::uuid, NULL::text
            FROM system_ai_models
            WHERE is_active = TRUE
            ORDER BY provider ASC, name ASC
        """
        async with get_db_cursor_async(commit=False) as cursor:
            await run_in_threadpool(cursor.execute, query)
            rows = await run_in_threadpool(cursor.fetchall)

    # ── Map rows → dicts, differentiating system vs custom by user_id ─────────
    for r in rows:
        is_system = r[13] is None  # user_id slot is NULL for system models
        models.append({
            "id":                   r[0],
            "provider":             r[1],
            "model_id":             r[2],
            "name":                 r[3],
            "description":          r[4],
            "requires_key":         r[5],
            "base_url":             r[6],
            "category":             r[7] or "General",
            "created_at":           r[8].isoformat() if r[8] else None,
            "user_id":              None if is_system else str(r[13]),
            "api_key":              "" if is_system else (mask_key(decrypt_key(r[14])) if r[14] else ""),
            "credits_per_1k_tokens": float(r[9]),
            "tier_badge":           r[10],
            "input_cost_per_1m":    float(r[11]) if r[11] is not None else 0.0,
            "output_cost_per_1m":   float(r[12]) if r[12] is not None else 0.0,
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


