import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import get_current_user

from handlers.admin_handler import (
    check_super_admin,
    check_action_password,
    handle_get_admin_stats,
    handle_get_admin_users,
    handle_update_user_subscription,
    handle_update_user_super_admin,
    handle_get_admin_workspaces
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

class UpdateSubscriptionRequest(BaseModel):
    plan_tier: str
    admin_action_password: str

class UpdateSuperAdminRequest(BaseModel):
    is_super_admin: bool
    admin_action_password: str

@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to aggregate platform-wide metrics for the Super Admin dashboard header.
    Args:
        current_user: Token payload.
    Returns: The aggregated stats.
    """
    user_id = current_user["sub"]
    return await handle_get_admin_stats(user_id)

@router.get("/admin/users")
async def get_admin_users(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch a list of all registered users along with their subscription plans.
    Args:
        current_user: Token payload.
    Returns: A list of users.
    """
    user_id = current_user["sub"]
    return await handle_get_admin_users(user_id)

@router.post("/admin/users/{target_user_id}/subscription")
async def update_user_subscription(target_user_id: str, req: UpdateSubscriptionRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to allow a Super Admin to manually override a user's subscription tier.
    Args:
        target_user_id (str): The target user ID.
        req (UpdateSubscriptionRequest): The update payload.
    Returns: A success message.
    """
    data = req.dict()
    data["admin_user_id"] = current_user["sub"]
    return await handle_update_user_subscription(target_user_id, data)

@router.post("/admin/users/{target_user_id}/super_admin")
async def update_user_super_admin(target_user_id: str, req: UpdateSuperAdminRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to promote or demote a user from Super Admin status.
    Args:
        target_user_id (str): The target user ID.
        req (UpdateSuperAdminRequest): The update payload.
    Returns: A success message.
    """
    data = req.dict()
    data["admin_user_id"] = current_user["sub"]
    return await handle_update_user_super_admin(target_user_id, data)

@router.get("/admin/workspaces")
async def get_admin_workspaces(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch all workspaces on the platform and count how many members are in each.
    Args:
        current_user: Token payload.
    Returns: A list of workspaces.
    """
    user_id = current_user["sub"]
    return await handle_get_admin_workspaces(user_id)
