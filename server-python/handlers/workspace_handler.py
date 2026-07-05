import logging
import json
import os
from fastapi import HTTPException
from utils import send_invite_email
from database_layer import workspace_repository

logger = logging.getLogger(__name__)

async def handle_invite_workspace_member(payload: dict):
    try:
        existing = await workspace_repository.check_workspace_member_exists(
            payload.get("workspace_id"), payload.get("email")
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="User is already invited or is a member of this workspace.",
            )

        await workspace_repository.create_workspace_member(
            payload.get("workspace_id"), payload.get("email"), payload.get("role")
        )

        APP_URL = os.getenv("FRONTEND_URL", "https://blinkbot.in")
        signup_url = f"{APP_URL}/login?email={payload.get('email')}&invite=true"
        
        send_invite_email(
            to_email=payload.get("email"),
            workspace_name=payload.get("workspace_name"),
            invited_by=payload.get("invited_by_name"),
            signup_url=signup_url,
        )

        return {"message": "Invitation sent successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_workspace(payload: dict):
    try:
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
        
        owned_count = await workspace_repository.count_owned_workspaces(payload.get("owner_id"))
        
        if owned_count >= limit:
            raise HTTPException(status_code=403, detail="Workspace limit reached. Please upgrade your plan.")
            
        workspace_id = await workspace_repository.create_workspace(
            payload.get("name"), payload.get("owner_id"), payload.get("email"), payload.get("user_name")
        )
        
        return {"id": workspace_id, "name": payload.get("name"), "owner_id": payload.get("owner_id")}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workspace")


async def handle_get_primary_workspace(user_id: str):
    try:
        row = await workspace_repository.get_primary_workspace(user_id)
        
        if not row:
            return {"name": ""}
            
        return {
            "id": row[0],
            "name": row[1],
            "owner_id": row[2]
        }
    except Exception as e:
        logger.error(f"Error fetching primary workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch workspace")


async def handle_update_workspace(workspace_id: str, name: str):
    try:
        row = await workspace_repository.update_workspace_name(workspace_id, name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        return {
            "id": row[0],
            "name": row[1],
            "owner_id": row[2]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to update workspace")


async def handle_get_user_workspaces(user_id: str):
    try:
        rows = await workspace_repository.get_user_workspaces(user_id)
        
        workspaces = []
        for row in rows:
            workspaces.append({
                "id": row[0],
                "name": row[1],
                "owner_id": row[2],
                "role": row[3],
                "permissions": row[4]
            })
            
        return workspaces
    except Exception as e:
        logger.error(f"Error fetching user workspaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user workspaces")


async def handle_get_workspace_members(workspace_id: str):
    try:
        rows = await workspace_repository.get_workspace_members(workspace_id)
        
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
            
        return members
    except Exception as e:
        logger.error(f"Error fetching workspace members: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch workspace members")


async def handle_update_member_role(member_id: str, role: str):
    try:
        row = await workspace_repository.update_member_role(member_id, role)
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
            
        return {"message": "Role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role")


async def handle_update_member_permissions(member_id: str, permissions: dict):
    try:
        row = await workspace_repository.update_member_permissions(member_id, permissions)
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
            
        return {"message": "Permissions updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating permissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to update permissions")


async def handle_remove_member(member_id: str):
    try:
        row = await workspace_repository.remove_member(member_id)
        if not row:
            raise HTTPException(status_code=404, detail="Member not found")
            
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove member")
