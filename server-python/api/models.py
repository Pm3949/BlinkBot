from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from handlers import model_handler

router = APIRouter()

class ModelCreate(BaseModel):
    provider: str
    model_id: str
    name: str
    description: Optional[str] = ""
    requires_key: Optional[bool] = False
    base_url: Optional[str] = ""
    category: Optional[str] = "General"
    api_key: Optional[str] = ""

class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requires_key: Optional[bool] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    provider: Optional[str] = None
    model_id: Optional[str] = None
    api_key: Optional[str] = None

class KeyTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""

@router.get("/api/models")
async def get_active_models(current_user: dict = Depends(get_current_user)):
    """Returns all active AI models grouped by provider for agent creation/dropdowns."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_get_active_models(user_id=user_id)

@router.get("/api/models/all")
async def get_all_models(current_user: dict = Depends(get_current_user)):
    """Returns all models (active & inactive) for administration."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_get_all_models(user_id=user_id)

@router.post("/api/models")
async def create_model(payload: ModelCreate, current_user: dict = Depends(get_current_user)):
    """Adds a new model entry to the system catalog."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_create_model(payload.dict(), user_id=user_id)

@router.put("/api/models/{model_id}")
async def update_model(model_id: str, payload: ModelUpdate, current_user: dict = Depends(get_current_user)):
    """Updates an existing model configuration or toggles active state."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_update_model(model_id, payload.dict(exclude_unset=True), user_id=user_id)

@router.delete("/api/models/{model_id}")
async def delete_model(model_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes a model entry from the system catalog."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_delete_model(model_id, user_id=user_id)

class SingleModelTestRequest(BaseModel):
    provider: str
    model_id: str
    api_key: Optional[str] = ""
    base_url: Optional[str] = ""

@router.post("/api/models/test-key")
async def test_provider_key(payload: KeyTestRequest, current_user: dict = Depends(get_current_user)):
    """Tests connectivity to a provider API key or custom server base URL."""
    return await model_handler.handle_test_provider_key(payload.provider, payload.api_key, payload.base_url)

@router.post("/api/models/test-model")
async def test_single_model(payload: SingleModelTestRequest, current_user: dict = Depends(get_current_user)):
    """Tests live execution of a single model in the catalog."""
    user_id = current_user.get("sub") if isinstance(current_user, dict) else str(current_user)
    return await model_handler.handle_test_single_model(payload.dict(), user_id=user_id)
