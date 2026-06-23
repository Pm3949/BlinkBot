"""
Workspaces Router.
Responsibility: Manages multi-tenant Workspaces, allowing users to collaborate on Agents.
Handles inviting members via email, Role-Based Access Control (RBAC), and managing 
workspace configurations.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection
from schemas import InviteRequest
from utils import send_invite_email
import os

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])

# ==========================================
# INVITATION SYSTEM
# ==========================================

@router.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    """
    Invites a user to a workspace.
    Data Flow: Check if exists -> Insert Placeholder Member -> Send Email -> 
    User clicks link -> Registration maps their email to this workspace automatically.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if member already exists in the workspace to prevent duplicate invites
        cursor.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (req.workspace_id, req.email),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="User is already invited or is a member of this workspace.",
            )

        # Insert placeholder record with default restricted permissions
        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, '{"agents": false, "database": false, "notes": false}'::jsonb)
            RETURNING id;
            """,
            (req.workspace_id, req.email, req.email.split("@")[0], req.role),
        )
        conn.commit()

        # Generate a magic link for signup
        APP_URL = os.getenv("FRONTEND_URL", "https://blinkbot.in")
        signup_url = f"{APP_URL}/login?email={req.email}&invite=true"
        
        # Send Real Email using the utility function
        send_invite_email(
            to_email=req.email,
            workspace_name=req.workspace_name,
            invited_by=req.invited_by_name,
            signup_url=signup_url,
        )

        return {"message": "Invitation sent successfully!"}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class WorkspaceUpdate(BaseModel):
    name: str

# ==========================================
# WORKSPACE FETCHING & UPDATING
# ==========================================
from schemas import WorkspaceCreate

@router.post("/api/workspaces")
async def create_workspace(payload: WorkspaceCreate):
    """
    Creates a new workspace if the user hasn't exceeded their subscription limit.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fetch Subscription Limit
        cursor.execute(
            """
            SELECT plan_tier, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (payload.owner_id,)
        )
        sub_row = cursor.fetchone()
        
        # Default limits based on plan, or 1 if no sub exists
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
        
        # 2. Count current owned workspaces
        cursor.execute(
            "SELECT COUNT(*) FROM workspaces WHERE owner_id = %s", 
            (payload.owner_id,)
        )
        owned_count = cursor.fetchone()[0]
        
        # 3. Paywall check
        if owned_count >= limit:
            raise HTTPException(status_code=403, detail="Workspace limit reached. Please upgrade your plan.")
            
        # 4. Create Workspace
        cursor.execute(
            """
            INSERT INTO workspaces (name, owner_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (payload.name, payload.owner_id)
        )
        workspace_id = cursor.fetchone()[0]
        
        # 5. Add user as Admin
        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Admin', '{"agents": true, "database": true, "notes": true}'::jsonb)
            """,
            (workspace_id, payload.owner_id, payload.email, payload.user_name)
        )
        conn.commit()
        
        return {"id": workspace_id, "name": payload.name, "owner_id": payload.owner_id}
        
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workspace")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/api/workspaces/primary/{user_id}")
async def get_primary_workspace(user_id: str):
    """
    Fetches the user's primary (owned) workspace. 
    Usually called right after login to load their default dashboard.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, name, owner_id
            FROM workspaces
            WHERE owner_id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.put("/api/workspaces/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate):
    """Updates the workspace name."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE workspaces
            SET name = %s, updated_at = now()
            WHERE id = %s
            RETURNING id, name, owner_id;
            """,
            (payload.name, workspace_id)
        )
        row = cursor.fetchone()
        conn.commit()
        
        if not row:
            raise HTTPException(status_code=404, detail="Workspace not found")
            
        return {
            "id": row[0],
            "name": row[1],
            "owner_id": row[2]
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to update workspace")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/api/workspaces/user/{user_id}")
async def get_user_workspaces(user_id: str):
    """
    Gets ALL workspaces a user belongs to (both owned and invited).
    Used to populate the Workspace Switcher dropdown in the UI.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Join workspace_members with workspaces to get the names alongside the roles
        cursor.execute(
            """
            SELECT w.id, w.name, w.owner_id, wm.role, wm.permissions
            FROM workspace_members wm
            JOIN workspaces w ON wm.workspace_id = w.id
            WHERE wm.user_id = %s
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ==========================================
# MEMBER MANAGEMENT (RBAC)
# ==========================================

@router.get("/api/workspaces/{workspace_id}/members")
async def get_workspace_members(workspace_id: str):
    """Lists all members in a specific workspace. Used for the Settings -> Team page."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, user_id, email, name, role, permissions, created_at
            FROM workspace_members
            WHERE workspace_id = %s
            ORDER BY created_at ASC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

import json

class UpdateRoleRequest(BaseModel):
    role: str

@router.put("/api/workspaces/members/{member_id}/role")
async def update_member_role(member_id: str, payload: UpdateRoleRequest):
    """Updates high-level role titles like 'Admin' or 'Viewer'."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE workspace_members SET role = %s WHERE id = %s RETURNING id;",
            (payload.role, member_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")
            
        conn.commit()
        return {"message": "Role updated successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class UpdatePermissionsRequest(BaseModel):
    permissions: dict

@router.put("/api/workspaces/members/{member_id}/permissions")
async def update_member_permissions(member_id: str, payload: UpdatePermissionsRequest):
    """
    Granular Role-Based Access Control (RBAC). 
    Updates specific feature flags in the JSONB column (e.g., {"agents": true, "billing": false}).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Postgres requires explicit type casting (::jsonb) when updating JSON columns
        cursor.execute(
            "UPDATE workspace_members SET permissions = %s::jsonb WHERE id = %s RETURNING id;",
            (json.dumps(payload.permissions), member_id)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")
            
        conn.commit()
        return {"message": "Permissions updated successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating permissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to update permissions")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.delete("/api/workspaces/members/{member_id}")
async def remove_member(member_id: str):
    """Kicks a member out of the workspace."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM workspace_members WHERE id = %s RETURNING id;",
            (member_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Member not found")
            
        conn.commit()
        return {"message": "Member removed successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error removing member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove member")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
