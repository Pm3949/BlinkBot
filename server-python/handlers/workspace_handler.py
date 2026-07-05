import logging
import json
import os
from fastapi import HTTPException
from database import get_db_connection
from utils import send_invite_email

logger = logging.getLogger(__name__)

async def handle_invite_workspace_member(payload: dict):
    """
    What it does: Sends an email invitation to a user to join a workspace and creates a placeholder member record in the database.
    Args:
        payload (dict): A dictionary containing workspace_id, email, role, workspace_name, and invited_by_name.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (payload.get("workspace_id"), payload.get("email")),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="User is already invited or is a member of this workspace.",
            )

        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, '{"agents": false, "database": false, "notes": false}'::jsonb)
            RETURNING id;
            """,
            (payload.get("workspace_id"), payload.get("email"), payload.get("email").split("@")[0], payload.get("role")),
        )
        conn.commit()

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


async def handle_create_workspace(payload: dict):
    """
    What it does: Creates a new workspace if the user has not exceeded their subscription tier limits.
    Args:
        payload (dict): Contains name, owner_id, email, and user_name.
    Returns: The ID, name, and owner_id of the new workspace.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT plan_tier, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (payload.get("owner_id"),)
        )
        sub_row = cursor.fetchone()
        
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
        
        cursor.execute(
            "SELECT COUNT(*) FROM workspaces WHERE owner_id = %s", 
            (payload.get("owner_id"),)
        )
        owned_count = cursor.fetchone()[0]
        
        if owned_count >= limit:
            raise HTTPException(status_code=403, detail="Workspace limit reached. Please upgrade your plan.")
            
        cursor.execute(
            """
            INSERT INTO workspaces (name, owner_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (payload.get("name"), payload.get("owner_id"))
        )
        workspace_id = cursor.fetchone()[0]
        
        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Admin', '{"agents": true, "database": true, "notes": true}'::jsonb)
            """,
            (workspace_id, payload.get("owner_id"), payload.get("email"), payload.get("user_name"))
        )
        conn.commit()
        
        return {"id": workspace_id, "name": payload.get("name"), "owner_id": payload.get("owner_id")}
        
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


async def handle_get_primary_workspace(user_id: str):
    """
    What it does: Fetches the primary (first owned) workspace for a user to load their default dashboard on login.
    Args:
        user_id (str): The user ID.
    Returns: The workspace ID, name, and owner ID.
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


async def handle_update_workspace(workspace_id: str, name: str):
    """
    What it does: Updates the name of a workspace.
    Args:
        workspace_id (str): The workspace ID.
        name (str): The new name.
    Returns: The updated workspace data.
    """
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
            (name, workspace_id)
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


async def handle_get_user_workspaces(user_id: str):
    """
    What it does: Gets a list of all workspaces (owned and invited) that a user has access to.
    Args:
        user_id (str): The user ID.
    Returns: A list of workspace dictionaries.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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


async def handle_get_workspace_members(workspace_id: str):
    """
    What it does: Fetches a list of all teammates in a given workspace.
    Args:
        workspace_id (str): The workspace ID.
    Returns: A list of member dictionaries.
    """
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


async def handle_update_member_role(member_id: str, role: str):
    """
    What it does: Updates the high-level title/role of a teammate (e.g., 'Admin', 'Viewer').
    Args:
        member_id (str): The member's database row ID.
        role (str): The new role name.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE workspace_members SET role = %s WHERE id = %s RETURNING id;",
            (role, member_id)
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


async def handle_update_member_permissions(member_id: str, permissions: dict):
    """
    What it does: Performs granular Role-Based Access Control by updating specific feature flags in the member's JSONB column.
    Args:
        member_id (str): The member's database row ID.
        permissions (dict): A dictionary of permission flags (e.g. {"agents": True}).
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE workspace_members SET permissions = %s::jsonb WHERE id = %s RETURNING id;",
            (json.dumps(permissions), member_id)
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


async def handle_remove_member(member_id: str):
    """
    What it does: Deletes a member from a workspace.
    Args:
        member_id (str): The member's database row ID.
    Returns: A success message.
    """
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
