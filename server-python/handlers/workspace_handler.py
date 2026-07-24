"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the business logic coordinator for managing workspaces and
team memberships in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard OS modules, FastAPI web exceptions, local email invitation helpers,
   and workspace database repositories.
2. Logging: Initializes a department logger named "system" to audit workspace modifications.
3. Member Invitations Handlers:
   - `handle_invite_workspace_member`: Sends email invitations to join a workspace and registers
     pending memberships in the database.
   - `handle_resend_invite_workspace_member`: Resends a pending workspace invitation email.
   - `handle_claim_invites`: Converts pending invitations to active memberships when a user signs up.
4. Workspace Configuration Handlers:
   - `handle_create_workspace`: Validates user subscription limits before creating a new workspace.
   - `handle_get_primary_workspace`: Fetches default workspace metadata details for a user.
   - `handle_update_workspace`: Modifies workspace names.
   - `handle_get_user_workspaces`: Fetches all workspaces associated with a user.
5. Workspace Team Management Handlers:
   - `handle_get_workspace_members`: Fetches members and invitations associated with a workspace.
   - `handle_update_member_role`: Updates member authorization roles (e.g., teammate vs editor).
   - `handle_update_member_permissions`: Updates workspace member permission scopes.
   - `handle_remove_member`: Removes a member from a workspace.
"""

import os  # Read system environment parameters (FRONTEND_URL endpoints)
from fastapi import HTTPException  # Raise clean HTTP error status codes to client
from utils import send_invite_email  # Transactional email helper
from db import workspace_repository  # Database access repository for workspace tables

# Logging utilities
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "system" activities
logger = get_department_logger("system")


async def handle_invite_workspace_member(payload: dict):
    """
    Invites a user to a workspace.
    Checks if the user is already a member, inserts a pending record, and emails the invitation.

    Parameters:
        payload (dict): Payload containing:
            - 'email' (str): Target email address.
            - 'workspace_id' (str): Workspace UUID.
            - 'role' (str): Member role.
            - 'workspace_name' (str): Workspace name.
            - 'invited_by_name' (str): Requester's display name.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400): Raised if the user is already associated with the workspace.
        HTTPException(500): Raised if database queries or emails fail.
    """
    logger.info(f"Inviting user '{payload.get('email')}' to workspace ID: {payload.get('workspace_id')}")
    try:
        # Check if the user is already invited or a member
        logger.debug("Checking if user is already a member or invited...")
        existing = await workspace_repository.check_workspace_member_exists(
            payload.get("workspace_id"), payload.get("email")
        )
        if existing:
            logger.warning(f"Invitation rejected: User {payload.get('email')} is already a member or has an open invitation.")
            raise HTTPException(
                status_code=400,
                detail="User is already invited or is a member of this workspace.",
            )

        # Insert pending member record in database
        logger.debug("Creating workspace membership entry in database...")
        await workspace_repository.create_workspace_member(
            payload.get("workspace_id"), payload.get("email"), payload.get("role")
        )

        # Generate signup callback URL redirection link
        APP_URL = os.getenv("FRONTEND_URL", "https://blinkbot.in")
        signup_url = f"{APP_URL}/login?email={payload.get('email')}&invite=true"
        
        # Dispatch invitation email
        logger.info(f"Sending invitation email to {payload.get('email')}...")
        send_invite_email(
            to_email=payload.get("email"),
            workspace_name=payload.get("workspace_name"),
            invited_by=payload.get("invited_by_name"),
            signup_url=signup_url,
        )

        logger.info(f"User {payload.get('email')} successfully invited.")
        return {"message": "Invitation sent successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invite workspace member: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_workspace(payload: dict):
    """
    Creates a new workspace record.
    Checks subscription plan limits to prevent exceeding allowed workspaces quota.

    Parameters:
        payload (dict): Payload containing:
            - 'name' (str): Desired workspace name.
            - 'owner_id' (str): User UUID of the owner.
            - 'email' (str): Owner's email.
            - 'user_name' (str): Owner's display name.

    Returns:
        dict: A dictionary containing the created workspace 'id', 'name', and 'owner_id'.

    Exceptions Raised:
        HTTPException(403): Raised if the workspace quota is reached.
        HTTPException(500): Raised if database inserts crash.
    """
    logger.info(f"Creating a new workspace: '{payload.get('name')}' for owner user ID: {payload.get('owner_id')}")
    try:
        # Fetch subscription plan workspace limits
        logger.debug("Retrieving workspace plan limits for owner...")
        sub_row = await workspace_repository.get_user_subscription_limits(payload.get("owner_id"))
        
        limit = 1  # Default fallback limit
        if sub_row:
            plan_tier = sub_row[0]
            limits = sub_row[1]
            if limits and "workspaces" in limits:
                limit = int(limits["workspaces"])
            elif plan_tier == "Pro":
                limit = 3
            elif plan_tier == "Enterprise":
                limit = 999999
        
        # Fetch current count of owned workspaces
        logger.debug("Retrieving current owned workspaces count...")
        owned_count = await workspace_repository.count_owned_workspaces(payload.get("owner_id"))
        logger.debug(f"Owned count: {owned_count}, Allowed limit: {limit}")
        
        # Prevent creation if quota is reached
        if owned_count >= limit:
            logger.warning(f"Workspace creation rejected: User {payload.get('owner_id')} has reached their workspace limit.")
            raise HTTPException(status_code=403, detail="Workspace limit reached. Please upgrade your plan.")
            
        # Create workspace record in database
        logger.debug("Executing workspace database creation query...")
        workspace_id = await workspace_repository.create_workspace(
            payload.get("name"), payload.get("owner_id"), payload.get("email"), payload.get("user_name")
        )
        
        logger.info(f"Workspace successfully created. ID: {workspace_id}")
        return {"id": workspace_id, "name": payload.get("name"), "owner_id": payload.get("owner_id")}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create workspace")


async def handle_get_primary_workspace(user_id: str):
    """
    Retrieves the primary workspace details for a user.

    Parameters:
        user_id (str): The unique user UUID.

    Returns:
        dict: Workspace details ('id', 'name', 'owner_id').

    Exceptions Raised:
        HTTPException(500): Raised if SQL queries fail.
    """
    logger.info(f"Retrieving primary workspace details for user ID: {user_id}")
    try:
        # Fetch primary workspace from repository
        logger.debug("Executing primary workspace fetch query...")
        row = await workspace_repository.get_primary_workspace(user_id)
        
        if not row:
            logger.info(f"No workspace registry record found for user {user_id}.")
            return {"name": ""}
            
        logger.info(f"Successfully retrieved primary workspace for user {user_id}. ID: {row[0]}")
        return {
            "id": row[0],
            "name": row[1],
            "owner_id": row[2]
        }
    except Exception as e:
        logger.error(f"Error fetching primary workspace for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch workspace")


async def handle_update_workspace(workspace_id: str, name: str):
    """
    Updates the name of a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID.
        name (str): New workspace name.

    Returns:
        dict: The updated workspace details.

    Exceptions Raised:
        HTTPException(404): Raised if the workspace ID is not found.
        HTTPException(500): Raised if updates fail.
    """
    logger.info(f"Updating workspace ID: {workspace_id} (New Name: '{name}')")
    try:
        # Update workspace name in database repository
        logger.debug("Executing workspace name update query...")
        row = await workspace_repository.update_workspace_name(workspace_id, name)
        
        if not row:
            logger.warning(f"Update workspace aborted: Workspace ID {workspace_id} not found.")
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        logger.info(f"Workspace ID {workspace_id} successfully updated.")
        return {
            "id": row[0],
            "name": row[1],
            "owner_id": row[2]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workspace ID {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update workspace")


async def handle_get_user_workspaces(user_id: str):
    """
    Retrieves all workspaces associated with a user.

    Parameters:
        user_id (str): The unique user UUID.

    Returns:
        list: A list of workspace details.

    Exceptions Raised:
        HTTPException(500): Raised if database queries fail.
    """
    logger.info(f"Retrieving user workspaces list for user ID: {user_id}")
    try:
        # Fetch workspaces from repository
        logger.debug("Executing user workspaces query...")
        rows = await workspace_repository.get_user_workspaces(user_id)
        logger.debug(f"Retrieved {len(rows)} workspace associations.")
        
        # Map raw database tuples to dictionaries
        workspaces = []
        for row in rows:
            workspaces.append({
                "id": row[0],
                "name": row[1],
                "owner_id": row[2],
                "role": row[3],
                "permissions": row[4]
            })
            
        logger.info(f"Successfully returned {len(workspaces)} workspaces.")
        return workspaces
    except Exception as e:
        logger.error(f"Error fetching user workspaces for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user workspaces")


async def handle_get_workspace_members(workspace_id: str):
    """
    Retrieves the list of members and invitations associated with a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID.

    Returns:
        list: A list of member details.

    Exceptions Raised:
        HTTPException(500): Raised if database queries fail.
    """
    logger.info(f"Retrieving workspace members list for workspace ID: {workspace_id}")
    try:
        # Fetch members from repository
        logger.debug("Querying workspace members from database...")
        rows = await workspace_repository.get_workspace_members(workspace_id)
        logger.debug(f"Retrieved {len(rows)} member records.")
        
        # Map raw database tuples to dictionaries
        members = []
        for row in rows:
            members.append({
                "id": row[0],
                "user_id": row[1],
                "email": row[2],
                "name": row[3],
                "role": row[4],
                "permissions": row[5],
                "joined_at": row[6].isoformat() if row[6] else None
            })
            
        logger.info(f"Successfully processed {len(members)} workspace members.")
        return members
    except Exception as e:
        logger.error(f"Error fetching workspace members for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch workspace members")


async def handle_update_member_role(member_id: str, role: str):
    """
    Updates the role of a workspace member.

    Parameters:
        member_id (str): Member record UUID.
        role (str): Target role (e.g., 'teammate', 'editor', 'admin').

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"[AUDIT LOG] Updating workspace member ID {member_id} role to: '{role}'")
    try:
        # Update member role in database repository
        logger.debug("Executing database member role update...")
        row = await workspace_repository.update_member_role(member_id, role)
        if not row:
            logger.warning(f"Update role rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"[AUDIT LOG] Member ID {member_id} role successfully updated to '{role}'.")
        return {"message": "Role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role for member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update role")


async def handle_update_member_permissions(member_id: str, permissions: dict):
    """
    Updates the permissions scope configuration for a workspace member.

    Parameters:
        member_id (str): Member record UUID.
        permissions (dict): Target permissions mapping.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"[AUDIT LOG] Updating workspace member ID {member_id} permissions: {permissions}")
    try:
        # Update member permissions in database repository
        logger.debug("Executing database member permissions update...")
        row = await workspace_repository.update_member_permissions(member_id, permissions)
        if not row:
            logger.warning(f"Update permissions rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"[AUDIT LOG] Member ID {member_id} permissions successfully updated.")
        return {"message": "Permissions updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member permissions for member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update permissions")


async def handle_remove_member(member_id: str):
    """
    Removes a member from a workspace.

    Parameters:
        member_id (str): Member record UUID to delete.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"[AUDIT LOG] Removing member ID: {member_id} from workspace")
    try:
        # Delete member record in database repository
        logger.debug("Executing database member deletion query...")
        row = await workspace_repository.remove_member(member_id)
        if not row:
            logger.warning(f"Remove member rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"[AUDIT LOG] Member ID {member_id} successfully removed.")
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove member")


async def handle_resend_invite_workspace_member(member_id: str, sender_email: str = None):
    """
    Resends a pending workspace invitation email to a user.

    Parameters:
        member_id (str): Member record UUID.
        sender_email (str, optional): Requester's email.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if member ID not found.
        HTTPException(500): Raised if database queries or emails fail.
    """
    logger.info(f"Resending workspace invitation for member ID: {member_id}")
    try:
        # Retrieve member details
        member = await workspace_repository.get_member_by_id(member_id)
        if not member:
            logger.warning(f"Resend invite rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        email = member[2]
        workspace_name = member[5] or "Workspace"
        invited_by = sender_email or "Workspace Admin"
        
        APP_URL = os.getenv("FRONTEND_URL", "https://blinkbot.in")
        signup_url = f"{APP_URL}/login?email={email}&invite=true"
        
        # Resend invitation email
        logger.info(f"Resending invitation email to {email}...")
        send_invite_email(
            to_email=email,
            workspace_name=workspace_name,
            invited_by=invited_by,
            signup_url=signup_url,
        )
        logger.info(f"[AUDIT LOG] Invitation email resent to '{email}' for workspace '{workspace_name}' by '{invited_by}'")
        return {"message": "Invitation resent successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resend workspace invite for member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resend invitation")


async def handle_claim_invites(user_id: str, email: str):
    """
    Converts pending workspace invitations into active memberships for a newly signed-up user.

    Parameters:
        user_id (str): The newly created user's UUID.
        email (str): The user's email address.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"Claiming pending workspace invites for user ID: {user_id}, Email: {email}")
    try:
        # Update pending invites in database repository
        await workspace_repository.claim_pending_workspace_invites(user_id, email)
        return {"message": "Pending workspace invites claimed successfully"}
    except Exception as e:
        logger.error(f"Error claiming invites for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to claim invites")
