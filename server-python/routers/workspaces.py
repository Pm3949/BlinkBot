import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection
from schemas import InviteRequest
from utils import send_invite_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])

@router.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if member already exists in the workspace
        cursor.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (req.workspace_id, req.email),
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="User is already invited or is a member of this workspace.",
            )

        # Insert placeholder record
        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, '{"agents": false, "database": false, "notes": false}'::jsonb)
            RETURNING id;
            """,
            (req.workspace_id, req.email, req.email.split("@")[0], req.role),
        )
        conn.commit()

        APP_URL = "https://rag-mate-ashen.vercel.app"
        # Send Real Email (Redirect user to local frontend dashboard or login page)
        signup_url = f"{APP_URL}/login?email={req.email}&invite=true"
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

@router.get("/api/workspaces/primary/{user_id}")
async def get_primary_workspace(user_id: str):
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
