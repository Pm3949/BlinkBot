import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from schemas import InviteRequest, WorkspaceCreate
from core.auth import get_current_user

from handlers.workspace_handler import (
    handle_invite_workspace_member,
    handle_create_workspace,
    handle_get_primary_workspace,
    handle_update_workspace,
    handle_get_user_workspaces,
    handle_get_workspace_members,
    handle_update_member_role,
    handle_update_member_permissions,
    handle_remove_member,
    handle_claim_invites
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])

class WorkspaceUpdate(BaseModel):
    name: str

class UpdateRoleRequest(BaseModel):
    role: str

class UpdatePermissionsRequest(BaseModel):
    permissions: dict

@router.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    """
    What it does: HTTP endpoint to invite a user to a workspace.
    Args:
        req (InviteRequest): The invitation details.
    Returns: A success message.
    """
    return await handle_invite_workspace_member(req.dict())

@router.post("/api/workspaces")
async def create_workspace(payload: WorkspaceCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create a new workspace.
    Args:
        payload (WorkspaceCreate): The new workspace details.
    Returns: The newly created workspace details.
    """
    data = payload.dict()
    data["owner_id"] = current_user["sub"]
    return await handle_create_workspace(data)

@router.get("/api/workspaces/primary")
async def get_primary_workspace(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch the user's primary workspace.
    Args:
        user_id (str): The user's ID.
    Returns: The workspace details.
    """
    user_id = current_user["sub"]
    return await handle_get_primary_workspace(user_id)

@router.put("/api/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate):
    """
    What it does: HTTP endpoint to update a workspace's name.
    Args:
        workspace_id (str): The workspace ID.
        payload (WorkspaceUpdate): The new name.
    Returns: The updated workspace details.
    """
    return await handle_update_workspace(workspace_id, payload.name)

@router.get("/api/workspaces/user")
async def get_user_workspaces(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to get all workspaces a user has access to.
    Args:
        user_id (str): The user's ID.
    Returns: A list of workspaces.
    """
    user_id = current_user["sub"]
    return await handle_get_user_workspaces(user_id)

@router.get("/api/workspaces/{workspace_id}/members")
async def get_workspace_members(workspace_id: str):
    """
    What it does: HTTP endpoint to list all members of a workspace.
    Args:
        workspace_id (str): The workspace ID.
    Returns: A list of members.
    """
    return await handle_get_workspace_members(workspace_id)

@router.put("/api/workspaces/members/{member_id}/role")
async def update_member_role(member_id: str, payload: UpdateRoleRequest):
    """
    What it does: HTTP endpoint to update a teammate's role title.
    Args:
        member_id (str): The member ID.
        payload (UpdateRoleRequest): The new role.
    Returns: A success message.
    """
    return await handle_update_member_role(member_id, payload.role)

@router.put("/api/workspaces/members/{member_id}/permissions")
async def update_member_permissions(member_id: str, payload: UpdatePermissionsRequest):
    """
    What it does: HTTP endpoint to update a teammate's granular permissions.
    Args:
        member_id (str): The member ID.
        payload (UpdatePermissionsRequest): The new permissions dictionary.
    Returns: A success message.
    """
    return await handle_update_member_permissions(member_id, payload.permissions)

@router.delete("/api/workspaces/members/{member_id}")
async def remove_member(member_id: str):
    """
    What it does: HTTP endpoint to remove a teammate from a workspace.
    Args:
        member_id (str): The member ID.
    Returns: A success message.
    """
    return await handle_remove_member(member_id)

@router.post("/api/workspaces/claim-invites")
async def claim_workspace_invites(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint for logged-in users to claim pending invitations matching their email address.
    """
    user_id = current_user["sub"]
    email = current_user.get("email") or ""
    return await handle_claim_invites(user_id, email)
