import logging
from fastapi import APIRouter, HTTPException
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
