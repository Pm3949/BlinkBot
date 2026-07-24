"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all User Settings and API
Credential management actions in the RAGMate backend. It maps inbound HTTP REST requests
directly to the underlying business logic executors defined inside the settings
handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging controllers, typing variables, Pydantic validation schemas,
   FastAPI APIRouter routing components, and JWT authentication token guards.
2. Routing Initialization: Declares the APIRouter for 'settings' tag groupings.
3. Input Payload Validation Schema:
   - `UserSettingsUpdate`: Validates JSON payloads when updating custom API credentials
     and security preferences (e.g. OpenAI keys, Groq keys, Gemini keys, 2FA status).
4. HTTP Routes:
   - GET `/api/settings`: Retrieves decrypted credentials configured by the user.
   - POST `/api/settings`: Updates, encrypts, and registers user configurations.
"""

import logging  # Import python logging library
from typing import Optional  # Import Optional type mapping for query validations
from pydantic import BaseModel  # Pydantic BaseModels for request validations
from fastapi import APIRouter, Depends  # FastAPI Router and Depends injection dependencies
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import settings logic handlers
from handlers.settings_handler import (
    handle_get_user_settings,
    handle_update_user_settings
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for settings endpoints
router = APIRouter(tags=["settings"])

class UserSettingsUpdate(BaseModel):
    """
    Validates payload options when updating user settings and credentials.
    """
    openai_api_key: Optional[str] = None       # OpenAI key override (optional)
    groq_api_key: Optional[str] = None         # Groq key override (optional)
    gemini_api_key: Optional[str] = None       # Gemini key override (optional)
    two_factor_enabled: Optional[bool] = None  # Two-factor authentication status override (optional)


@router.get("/api/settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch user settings and decrypted API keys.
    Requires user authentication.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary of configurations containing decrypted API keys.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract the subject (user UUID) from the validated JWT dictionary
    return await handle_get_user_settings(user_id)  # Route task execution to handlers layer


@router.post("/api/settings")
async def update_user_settings(payload: UserSettingsUpdate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to encrypt and update user settings.
    Requires user authentication.

    Parameters:
        payload (UserSettingsUpdate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly saved and decrypted settings.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database updates crash.
    """
    # Route execution to handlers layer, passing credentials parameters
    return await handle_update_user_settings(
        current_user["sub"],
        payload.openai_api_key,
        payload.groq_api_key,
        payload.gemini_api_key,
        payload.two_factor_enabled
    )
