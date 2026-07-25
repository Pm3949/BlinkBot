"""
================================================================================
WORKSPACE & TEAM MEMBERSHIP ROUTER LAYER (workspaces.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for the platform's multi-tenant workspaces.
Workspaces group documents, agents, settings, and team members together.
This module manages:
1. Workspace Management: Creating workspaces, listing user workspaces, and renaming workspaces.
2. Team Management: Inviting members, updating member roles ('owner', 'admin', 'member'), and removing members.
3. Access Controls: Updating granular workspace permissions (e.g. read/write files, edit agents).
4. Invitation Lifecycle: Claims pending invitations matching the user's email address, and resends invite emails.

DATA ROUTING:
- Most endpoints are protected by the `get_current_user` JWT check.
- Processing is delegated to `handlers/workspace_handler.py` for transaction validation and database execution.
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from schemas import InviteRequest, WorkspaceCreate
from core.auth import get_current_user

# Import workspace and team management handlers.
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
    handle_claim_invites,
    handle_resend_invite_workspace_member
)

# Initialize standard module logger.
logger = logging.getLogger(__name__)

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["workspaces"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class WorkspaceUpdate(BaseModel):
    """
    Validation schema for renaming a workspace.
    """
    name: str # The new workspace name


class UpdateRoleRequest(BaseModel):
    """
    Validation schema for modifying team roles.
    """
    role: str # The target role ('owner', 'admin', 'member')


class UpdatePermissionsRequest(BaseModel):
    """
    Validation schema for updating granular permissions.
    """
    permissions: dict # Dict mapping action identifiers to boolean toggles


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    """
    Invites a user to a workspace.

    Purpose:
        Creates a pending workspace membership and sends an invitation email.

    Parameters:
        req (InviteRequest): Contains the target workspace ID, email, and roles.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Writes a pending row to the `workspace_members` table.
        - Sends an invitation email.

    Errors / Exceptions:
        - Raises 400 Bad Request if the user is already a member.
    """
    # Send the invitation.
    return await handle_invite_workspace_member(req.dict())


@router.post("/api/workspaces")
async def create_workspace(payload: WorkspaceCreate, current_user: dict = Depends(get_current_user)):
    """
    Creates a new workspace.

    Purpose:
        Initializes a workspace and registers the creator as the owner.

    Parameters:
        payload (WorkspaceCreate): Contains the workspace name.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created workspace details.

    Side Effects / State Changes:
        - Writes a new row to the `workspaces` table.
        - Adds an owner row to the `workspace_members` table.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification checks fail.
    """
    # Convert Pydantic fields to a dictionary.
    data = payload.dict()
    # Inject the owner's user ID.
    data["owner_id"] = current_user["sub"]
    # Initialize the workspace.
    return await handle_create_workspace(data)


@router.get("/api/workspaces/primary")
async def get_primary_workspace(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the user's primary workspace.

    Purpose:
        Fetches the primary workspace to select it by default on login.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Workspace configuration details.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract user ID.
    user_id = current_user["sub"]
    # Retrieve the primary workspace.
    return await handle_get_primary_workspace(user_id)


@router.get("/api/workspaces/user")
async def get_user_workspaces(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all workspaces the user has access to.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Workspaces list.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract user ID.
    user_id = current_user["sub"]
    # Fetch user workspaces.
    return await handle_get_user_workspaces(user_id)


@router.put("/api/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate):
    """
    Updates the workspace name.

    Parameters:
        workspace_id (str): UUID of the target workspace.
        payload (WorkspaceUpdate): Contains the new name.

    Returns:
        dict: The updated workspace details.

    Side Effects / State Changes:
        - Updates the name column in the `workspaces` table.

    Errors / Exceptions:
        - Raises 404 Not Found if the workspace is not found.
    """
    # Update the workspace.
    return await handle_update_workspace(workspace_id, payload.name)


@router.get("/api/workspaces/{workspace_id}/members")
async def get_workspace_members(workspace_id: str):
    """
    Lists all members of a workspace.

    Parameters:
        workspace_id (str): UUID of the target workspace.

    Returns:
        list of dict: Workspace members and roles.

    Side Effects / State Changes:
        - None. Read-only query.
    """
    # Retrieve members.
    return await handle_get_workspace_members(workspace_id)


@router.put("/api/workspaces/members/{member_id}/role")
async def update_member_role(member_id: str, payload: UpdateRoleRequest):
    """
    Updates a member's role.

    Parameters:
        member_id (str): The unique member ID.
        payload (UpdateRoleRequest): Contains the new role.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the role column in the `workspace_members` table.

    Errors / Exceptions:
        - Raises 404 if the membership row does not exist.
    """
    # Update the role.
    return await handle_update_member_role(member_id, payload.role)


@router.put("/api/workspaces/members/{member_id}/permissions")
async def update_member_permissions(member_id: str, payload: UpdatePermissionsRequest):
    """
    Updates granular permissions for a workspace member.

    Parameters:
        member_id (str): The unique member ID.
        payload (UpdatePermissionsRequest): Contains the permissions dictionary.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the permissions column in `workspace_members`.

    Errors / Exceptions:
        - Raises 404 if the membership row is not found.
    """
    # Update permissions.
    return await handle_update_member_permissions(member_id, payload.permissions)


@router.delete("/api/workspaces/members/{member_id}")
async def remove_member(member_id: str):
    """
    Removes a member from a workspace.

    Parameters:
        member_id (str): The unique member ID.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Deletes the membership row in `workspace_members`.

    Errors / Exceptions:
        - Raises 404 if the member is not found.
    """
    # Remove the member.
    return await handle_remove_member(member_id)


@router.post("/api/workspaces/claim-invites")
async def claim_workspace_invites(current_user: dict = Depends(get_current_user)):
    """
    Claims pending workspace invitations matching the user's email.

    Purpose:
        Links pending invitations to the user's account after registration.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Links pending memberships to the user's ID.
    """
    # Extract details and claim invitations.
    user_id = current_user["sub"]
    email = current_user.get("email") or ""
    return await handle_claim_invites(user_id, email)


@router.post("/api/workspaces/members/{member_id}/resend-invite")
async def resend_member_invite(member_id: str, current_user: dict = Depends(get_current_user)):
    """
    Resends an invitation email to a pending workspace member.

    Parameters:
        member_id (str): The unique member ID.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Resends the invitation email.
    """
    # Extract sender details and resend.
    sender_email = current_user.get("email") or ""
    return await handle_resend_invite_workspace_member(member_id, sender_email)

