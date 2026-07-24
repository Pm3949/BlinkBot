"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Workspaces and Workspace
Membership management actions in the RAGMate backend. It maps inbound HTTP REST requests
directly to the underlying business logic executors defined inside the workspace
handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging libraries, FastAPI routing components, Pydantic schemas,
   and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter for 'workspaces' tag groupings.
3. Input Payload Validation Schemas:
   - `WorkspaceUpdate`: Validates name modifications.
   - `UpdateRoleRequest`: Validates member authorization title changes.
   - `UpdatePermissionsRequest`: Validates granular permission dictionary updates.
4. HTTP Routes:
   - POST `/api/workspaces/invite`: Sends invitations.
   - POST `/api/workspaces`: Creates a workspace (evaluates subscription quotas).
   - GET `/api/workspaces/primary`: Fetches default primary workspaces.
   - PUT `/api/workspaces/{workspace_id}`: Renames a workspace.
   - GET `/api/workspaces/user`: Lists workspaces a user has access to.
   - GET `/api/workspaces/{workspace_id}/members`: Lists teammates and open invites.
   - PUT `/api/workspaces/members/{member_id}/role`: Edits member role titles.
   - PUT `/api/workspaces/members/{member_id}/permissions`: Edits member permission configurations.
   - DELETE `/api/workspaces/members/{member_id}`: Removes a teammate.
   - POST `/api/workspaces/claim-invites`: Links pending invites to new user accounts.
   - POST `/api/workspaces/members/{member_id}/resend-invite`: Resends pending invitations.
"""

import logging  # Import python logging library
from fastapi import APIRouter, Depends  # FastAPI Router and Depends injection dependencies
from pydantic import BaseModel  # Pydantic BaseModels for request payload validations
from schemas import InviteRequest, WorkspaceCreate  # Import schemas
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import workspace logic handlers
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

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for workspace endpoints
router = APIRouter(tags=["workspaces"])

class WorkspaceUpdate(BaseModel):
    """
    Validates payload options when updating workspace parameters.
    """
    name: str                                  # New workspace display name

class UpdateRoleRequest(BaseModel):
    """
    Validates payload options when updating a member's role.
    """
    role: str                                  # Target role title string (e.g. 'editor', 'teammate')

class UpdatePermissionsRequest(BaseModel):
    """
    Validates payload options when updating a member's granular permissions.
    """
    permissions: dict                          # Granular permissions dictionary mapping


@router.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    """
    HTTP POST endpoint to invite a user to a workspace.
    Publicly accessible (auth checks completed internally by handler).

    Parameters:
        req (InviteRequest): The pydantic-validated request payload.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400): Raised if user already exists or has open invitations.
        HTTPException(500): Raised if database inserts or email triggers crash.
    """
    return await handle_invite_workspace_member(req.dict())  # Convert to dictionary and route to handler


@router.post("/api/workspaces")
async def create_workspace(payload: WorkspaceCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to register a new workspace.
    Checks plan limits.

    Parameters:
        payload (WorkspaceCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly created workspace details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(403): Raised if workspace quota limits are exceeded.
        HTTPException(500): Raised if SQL database writes crash.
    """
    data = payload.dict()  # Convert Pydantic request structure to dictionary
    data["owner_id"] = current_user["sub"]  # Inject the owner User ID from JWT
    return await handle_create_workspace(data)  # Route task execution to handlers layer


@router.get("/api/workspaces/primary")
async def get_primary_workspace(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch a user's primary workspace.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Default workspace details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract user UUID from JWT
    return await handle_get_primary_workspace(user_id)  # Route task execution to handlers layer


@router.put("/api/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate):
    """
    HTTP PUT endpoint to rename a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID path parameter.
        payload (WorkspaceUpdate): The pydantic-validated request payload.

    Returns:
        dict: Updated workspace details.

    Exceptions Raised:
        HTTPException(404): Raised if workspace ID is not found.
        HTTPException(500): Raised if updates crash.
    """
    return await handle_update_workspace(workspace_id, payload.name)  # Route to handlers layer


@router.get("/api/workspaces/user")
async def get_user_workspaces(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing all workspaces a user has access to.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of workspace details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries crash.
    """
    user_id = current_user["sub"]  # Extract user UUID from JWT
    return await handle_get_user_workspaces(user_id)  # Route task execution to handlers layer


@router.get("/api/workspaces/{workspace_id}/members")
async def get_workspace_members(workspace_id: str):
    """
    HTTP GET endpoint listing all members and invitations in a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID path parameter.

    Returns:
        list: A list of member details.

    Exceptions Raised:
        HTTPException(500): Raised if database queries fail.
    """
    return await handle_get_workspace_members(workspace_id)  # Route task execution to handlers layer


@router.put("/api/workspaces/members/{member_id}/role")
async def update_member_role(member_id: str, payload: UpdateRoleRequest):
    """
    HTTP PUT endpoint to update a member's role title.

    Parameters:
        member_id (str): Target member UUID path parameter.
        payload (UpdateRoleRequest): The pydantic-validated request payload.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    return await handle_update_member_role(member_id, payload.role)  # Route task execution to handlers layer


@router.put("/api/workspaces/members/{member_id}/permissions")
async def update_member_permissions(member_id: str, payload: UpdatePermissionsRequest):
    """
    HTTP PUT endpoint to update a member's granular permissions.

    Parameters:
        member_id (str): Target member UUID path parameter.
        payload (UpdatePermissionsRequest): The pydantic-validated request payload.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    return await handle_update_member_permissions(member_id, payload.permissions)  # Route task execution to handlers layer


@router.delete("/api/workspaces/members/{member_id}")
async def remove_member(member_id: str):
    """
    HTTP DELETE endpoint to remove a teammate from a workspace.

    Parameters:
        member_id (str): Target member UUID path parameter.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    return await handle_remove_member(member_id)  # Route task execution to handlers layer


@router.post("/api/workspaces/claim-invites")
async def claim_workspace_invites(current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint for new users to claim pending invitations.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database updates crash.
    """
    user_id = current_user["sub"]  # Extract user UUID from JWT
    email = current_user.get("email") or ""  # Extract user email address from JWT context (if defined)
    return await handle_claim_invites(user_id, email)  # Route task execution to handlers layer


@router.post("/api/workspaces/members/{member_id}/resend-invite")
async def resend_member_invite(member_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to resend pending invitations.

    Parameters:
        member_id (str): Target member UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates or email triggers crash.
    """
    sender_email = current_user.get("email") or ""  # Extract sender's email address from JWT context
    return await handle_resend_invite_workspace_member(member_id, sender_email)  # Route task execution to handlers layer
