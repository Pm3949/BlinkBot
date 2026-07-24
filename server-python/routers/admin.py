"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Administrative actions
in the RAGMate backend. It maps inbound HTTP REST request endpoints directly to
underlying business logic executors defined inside the admin handler modules.

From top to bottom, the file executes as follows:
1. Imports: Loads standard logging controllers, FastAPI routing tools, Pydantic schemas,
   and JWT authentication guards (`get_current_user`).
2. Authentication Guard mapping: Endpoints leverage `Depends(get_current_user)` to
   extract JWT user details from the Request headers.
3. Schema Schematics:
   - `UpdateSubscriptionRequest`: Validates inputs for manually changing a user's subscription tier.
   - `UpdateSuperAdminRequest`: Validates inputs for promoting/demoting user administrative privileges.
4. HTTP Handlers:
   - `get_admin_stats`: Fetches aggregated platform metrics (e.g. user registrations, message metrics).
   - `get_admin_users`: Lists registered users and subscription tiers.
   - `update_user_subscription`: Overrides a user's subscription tier.
   - `update_user_super_admin`: Manages super admin status flags.
   - `get_admin_workspaces`: Lists workspaces and member counts.
"""

import logging  # Import Python logging library
from fastapi import APIRouter, Depends  # FastAPI Router object and Dependency Injection tools
from pydantic import BaseModel  # Import Pydantic models for request validation
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import admin logic handlers
from handlers.admin_handler import (
    check_super_admin,
    check_action_password,
    handle_get_admin_stats,
    handle_get_admin_users,
    handle_update_user_subscription,
    handle_update_user_super_admin,
    handle_get_admin_workspaces
)

# Instantiate a scoped file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for admin endpoints, grouping with tags
router = APIRouter(tags=["admin"])

class UpdateSubscriptionRequest(BaseModel):
    """
    Validates payload options for overriding a user's subscription plan.
    """
    plan_tier: str                  # Target subscription plan tier (e.g. 'Starter', 'Pro')
    admin_action_password: str       # Super-admin action verification password (dual-factor auth)

class UpdateSuperAdminRequest(BaseModel):
    """
    Validates payload options for promoting or demoting super admin status.
    """
    is_super_admin: bool            # Target super admin status flag (True/False)
    admin_action_password: str       # Action verification password
    

@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch platform-wide aggregated metrics.
    Restricted to Super Administrators.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing aggregated platform metrics.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(403): Raised if user is not a Super Admin.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract user UUID from JWT subject field
    return await handle_get_admin_stats(user_id)  # Route task execution to handlers layer


@router.get("/admin/users")
async def get_admin_users(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list all registered users.
    Restricted to Super Administrators.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing the list of registered users.

    Exceptions Raised:
        HTTPException(401/403): Raised if credentials check fails.
        HTTPException(500): Raised if query fails.
    """
    user_id = current_user["sub"]  # Extract requester's User ID
    return await handle_get_admin_users(user_id)  # Route task execution to handlers layer


@router.post("/admin/users/{target_user_id}/subscription")
async def update_user_subscription(target_user_id: str, req: UpdateSubscriptionRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to override a user's subscription plan.
    Restricted to Super Administrators.

    Parameters:
        target_user_id (str): The database UUID of the target user to modify.
        req (UpdateSubscriptionRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401/403): Raised for authentication or permission failures.
        HTTPException(500): Raised if update transactions crash.
    """
    data = req.dict()  # Convert Pydantic model payload to Python dictionary
    data["admin_user_id"] = current_user["sub"]  # Inject the admin user ID for authorization checks
    return await handle_update_user_subscription(target_user_id, data)  # Route to handlers layer


@router.post("/admin/users/{target_user_id}/super_admin")
async def update_user_super_admin(target_user_id: str, req: UpdateSuperAdminRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to promote/demote super admin privileges.
    Restricted to Super Administrators.

    Parameters:
        target_user_id (str): The database UUID of the target user to modify.
        req (UpdateSuperAdminRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401/403): Raised for authentication or permission failures.
        HTTPException(500): Raised if update transactions crash.
    """
    data = req.dict()  # Convert Pydantic request structure to dictionary
    data["admin_user_id"] = current_user["sub"]  # Inject the admin user ID for verification checks
    return await handle_update_user_super_admin(target_user_id, data)  # Route to handlers layer


@router.get("/admin/workspaces")
async def get_admin_workspaces(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list all workspaces and their member counts.
    Restricted to Super Administrators.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing the list of workspaces.

    Exceptions Raised:
        HTTPException(401/403): Raised for credentials or authorization failures.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract admin's User ID
    return await handle_get_admin_workspaces(user_id)  # Route task execution to handlers layer
