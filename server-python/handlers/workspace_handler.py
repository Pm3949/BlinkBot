import os
from fastapi import HTTPException
from utils import send_invite_email
from db import workspace_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")

async def handle_invite_workspace_member(payload: dict):
    logger.info(f"Inviting user '{payload.get('email')}' to workspace ID: {payload.get('workspace_id')}")
    try:
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

        logger.debug("Creating workspace membership entry in database...")
        await workspace_repository.create_workspace_member(
            payload.get("workspace_id"), payload.get("email"), payload.get("role")
        )

        APP_URL = os.getenv("FRONTEND_URL", "https://blinkbot.in")
        signup_url = f"{APP_URL}/login?email={payload.get('email')}&invite=true"
        
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
    logger.info(f"Creating a new workspace: '{payload.get('name')}' for owner user ID: {payload.get('owner_id')}")
    try:
        logger.debug("Retrieving workspace plan limits for owner...")
        sub_row = await workspace_repository.get_user_subscription_limits(payload.get("owner_id"))
        
        limit = 1 
        if sub_row:
            plan_tier = sub_row[0]
            limits = sub_row[1]
            if limits and "workspaces" in limits:
                limit = int(limits["workspaces"])
            elif plan_tier == "Pro":
                limit = 3
            elif plan_tier == "Enterprise":
                limit = 999999
        
        logger.debug("Retrieving current owned workspaces count...")
        owned_count = await workspace_repository.count_owned_workspaces(payload.get("owner_id"))
        logger.debug(f"Owned count: {owned_count}, Allowed limit: {limit}")
        
        if owned_count >= limit:
            logger.warning(f"Workspace creation rejected: User {payload.get('owner_id')} has reached their workspace limit.")
            raise HTTPException(status_code=403, detail="Workspace limit reached. Please upgrade your plan.")
            
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
    logger.info(f"Retrieving primary workspace details for user ID: {user_id}")
    try:
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
    logger.info(f"Updating workspace ID: {workspace_id} (New Name: '{name}')")
    try:
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
    logger.info(f"Retrieving user workspaces list for user ID: {user_id}")
    try:
        logger.debug("Executing user workspaces query...")
        rows = await workspace_repository.get_user_workspaces(user_id)
        logger.debug(f"Retrieved {len(rows)} workspace associations.")
        
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
    logger.info(f"Retrieving workspace members list for workspace ID: {workspace_id}")
    try:
        logger.debug("Querying workspace members from database...")
        rows = await workspace_repository.get_workspace_members(workspace_id)
        logger.debug(f"Retrieved {len(rows)} member records.")
        
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
    logger.info(f"Updating workspace member ID {member_id} role to: '{role}'")
    try:
        logger.debug("Executing database member role update...")
        row = await workspace_repository.update_member_role(member_id, role)
        if not row:
            logger.warning(f"Update role rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"Member ID {member_id} role successfully updated.")
        return {"message": "Role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role for member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update role")


async def handle_update_member_permissions(member_id: str, permissions: dict):
    logger.info(f"Updating workspace member ID {member_id} permissions payload: {permissions}")
    try:
        logger.debug("Executing database member permissions update...")
        row = await workspace_repository.update_member_permissions(member_id, permissions)
        if not row:
            logger.warning(f"Update permissions rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"Member ID {member_id} permissions successfully updated.")
        return {"message": "Permissions updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member permissions for member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update permissions")


async def handle_remove_member(member_id: str):
    logger.info(f"Removing member ID: {member_id} from workspace")
    try:
        logger.debug("Executing database member deletion query...")
        row = await workspace_repository.remove_member(member_id)
        if not row:
            logger.warning(f"Remove member rejected: Member ID {member_id} not found.")
            raise HTTPException(status_code=404, detail="Member not found")
            
        logger.info(f"Member ID {member_id} successfully removed.")
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove member")


async def handle_claim_invites(user_id: str, email: str):
    logger.info(f"Claiming pending workspace invites for user ID: {user_id}, Email: {email}")
    try:
        await workspace_repository.claim_pending_workspace_invites(user_id, email)
        return {"message": "Pending workspace invites claimed successfully"}
    except Exception as e:
        logger.error(f"Error claiming invites for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to claim invites")
