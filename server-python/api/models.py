"""
================================================================================
AI MODEL CATALOG MANAGEMENT ROUTER LAYER (models.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for the platform's AI model catalog.
It manages:
1. Catalog Listings: Retrieving active models for selection in drop-downs or fetching all catalog items
   for administrators.
2. CRUD Operations: Adding new custom models, updating configurations (toggling active states, renaming,
   changing providers), and deleting catalog items.
3. Model and API Key Verification: Verifying provider connectivity (`/test-key`) and verifying model responses
   by sending a test request (`/test-model`).

SECURITY & KEY DECRYPTION:
- Most endpoints are protected by the `get_current_user` JWT check.
- Custom API keys (e.g. OpenAI/Groq keys) stored in the database are decrypted and verified by
  `handlers/model_handler.py` before test requests are made to third-party endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from handlers import model_handler

# Initialize router instance for model paths.
router = APIRouter()

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class ModelCreate(BaseModel):
    """
    Validation schema for adding a new AI model entry to the system catalog.
    """
    provider: str # LLM provider (e.g. 'openai', 'groq', 'custom_openai')
    model_id: str # Technical model identifier (e.g. 'gpt-4o', 'llama3-70b')
    name: str # Display name
    description: Optional[str] = "" # Optional details of the model
    requires_key: Optional[bool] = False # Toggles if the model requires a custom key
    base_url: Optional[str] = "" # Base URL path for custom OpenAI-compatible hosts
    category: Optional[str] = "General" # Category (e.g. 'General', 'Embedding')
    api_key: Optional[str] = "" # Optional API key for custom servers
    input_cost_per_1m: Optional[float] = 0.0
    output_cost_per_1m: Optional[float] = 0.0
    credits_per_1k_tokens: Optional[float] = 0.0
    badge: Optional[str] = ""


class ModelUpdate(BaseModel):
    """
    Validation schema for modifying existing catalog entries.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    requires_key: Optional[bool] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    provider: Optional[str] = None
    model_id: Optional[str] = None
    api_key: Optional[str] = None
    input_cost_per_1m: Optional[float] = None
    output_cost_per_1m: Optional[float] = None
    credits_per_1k_tokens: Optional[float] = None
    badge: Optional[str] = None


class KeyTestRequest(BaseModel):
    """
    Validation schema for testing credentials connectivity.
    """
    provider: str # Target provider (e.g. 'groq', 'openai')
    api_key: Optional[str] = "" # API key string to test
    base_url: Optional[str] = "" # Optional target endpoint override


class SingleModelTestRequest(BaseModel):
    """
    Validation schema for testing model response outputs.
    """
    provider: str
    model_id: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/models")
async def get_active_models(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all active AI models in the catalog.

    Purpose:
        Fetches active models for dropdown selections.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Active models list grouped by provider.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Query active models.
    return await model_handler.handle_get_active_models(user_id=user_id)


@router.get("/api/models/all")
async def get_all_models(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all models in the catalog (active and inactive).

    Purpose:
        Lists all catalog models for administrative management.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Complete models database records list.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
    """
    # Extract the user's UUID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Query all models.
    return await model_handler.handle_get_all_models(user_id=user_id)


@router.post("/api/models")
async def create_model(payload: ModelCreate, current_user: dict = Depends(get_current_user)):
    """
    Adds a new model entry to the system catalog.

    Parameters:
        payload (ModelCreate): Pydantic body containing model attributes.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created model database record attributes.

    Side Effects / State Changes:
        - Writes a new row to the `ai_models` database table.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 Bad Request if the payload is invalid.
    """
    # Extract user ID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Save the new model entry.
    return await model_handler.handle_create_model(payload.dict(), user_id=user_id)


@router.put("/api/models/{model_id}")
async def update_model(model_id: str, payload: ModelUpdate, current_user: dict = Depends(get_current_user)):
    """
    Updates an existing model configuration.

    Parameters:
        model_id (str): UUID of the target model entry.
        payload (ModelUpdate): Contains properties to update.
        current_user (dict): JWT details.

    Returns:
        dict: The updated model database record attributes.

    Side Effects / State Changes:
        - Updates the matching row in `ai_models`.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the model entry is not found.
    """
    # Extract user ID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Update the catalog entry.
    return await model_handler.handle_update_model(model_id, payload.dict(exclude_unset=True), user_id=user_id)


@router.delete("/api/models/{model_id}")
async def delete_model(model_id: str, current_user: dict = Depends(get_current_user)):
    """
    Deletes a model entry from the catalog.

    Parameters:
        model_id (str): UUID of the model entry to delete.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes the matching row in `ai_models`.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the model is not found.
    """
    # Extract user ID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Delete the model entry.
    return await model_handler.handle_delete_model(model_id, user_id=user_id)


@router.post("/api/models/test-key")
async def test_provider_key(payload: KeyTestRequest, current_user: dict = Depends(get_current_user)):
    """
    Tests connectivity to a provider API key.

    Purpose:
        Verifies API key validity by making a lightweight test request.

    Parameters:
        payload (KeyTestRequest): Contains target provider details, API key, and optional base URL.
        current_user (dict): JWT details.

    Returns:
        dict: Connection test status (success/failure details).

    Errors / Exceptions:
        - Returns failure status if connection checks fail.
    """
    # Test the API key connection.
    return await model_handler.handle_test_provider_key(payload.provider, payload.api_key, payload.base_url)


@router.post("/api/models/test-model")
async def test_single_model(payload: SingleModelTestRequest, current_user: dict = Depends(get_current_user)):
    """
    Tests live execution of a single model.

    Purpose:
        Validates model configuration by sending a test chat request.

    Parameters:
        payload (SingleModelTestRequest): Model specifications and credentials to test.
        current_user (dict): JWT details.

    Returns:
        dict: Test response output details.
    """
    # Extract user ID.
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    # Test the model execution.
    return await model_handler.handle_test_single_model(payload.dict(), user_id=user_id)


@router.get("/api/models/available")
async def get_available_models(current_user: dict = Depends(get_current_user)):
    """
    Retrieves available system and user custom models, along with BYOK authorization status, wallet balance, and credentials state.
    """
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    
    # Check if BYOK is allowed
    from database import get_db_cursor_async
    from fastapi.concurrency import run_in_threadpool
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT allow_byok FROM user_subscriptions WHERE user_id = %s",
            (user_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        allow_byok = row[0] if row else False

    from db import billing_repository, settings_repository
    # Retrieve wallet balance
    credit_balance = await billing_repository.get_wallet_balance(user_id)

    # Retrieve BYOK keys status
    user_keys = await settings_repository.get_effective_user_settings(user_id)
    byok_status = {
        "openai": bool(user_keys[0]) if user_keys else False,
        "groq": bool(user_keys[1]) if user_keys else False,
        "gemini": bool(user_keys[2]) if user_keys else False,
        "openrouter": bool(user_keys[3]) if user_keys else False,
        "anthropic": bool(user_keys[4]) if user_keys else False,
        "huggingface": bool(user_keys[5]) if user_keys else False,
        "nvidia": bool(user_keys[6]) if user_keys else False,
    }

    active_models = await model_handler.handle_get_active_models(user_id=user_id)
    return {
        "allow_byok": allow_byok,
        "credit_balance": credit_balance,
        "byok_status": byok_status,
        "providers": active_models.get("providers", {}),
        "models": active_models.get("models", [])
    }



