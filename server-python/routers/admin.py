import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

def check_super_admin(user_id: str, cursor):
    cursor.execute(
        "SELECT is_super_admin FROM users WHERE id = %s", (user_id,)
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="Super Admin access required")

def check_action_password(password: str):
    expected_password = os.getenv("ADMIN_ACTION_PASSWORD")
    if not expected_password:
        raise HTTPException(status_code=500, detail="Server configuration error: ADMIN_ACTION_PASSWORD not set")
    if password != expected_password:
        raise HTTPException(status_code=403, detail="Invalid action password")


@router.get("/admin/stats")
async def get_admin_stats(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM workspaces")
        total_workspaces = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agents")
        total_agents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chatbots")
        total_chatbots = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM documents")
        total_storage_mb = (cursor.fetchone()[0] or 0) / (1024 * 1024)

        return {
            "totalUsers": total_users,
            "totalWorkspaces": total_workspaces,
            "totalAgents": total_agents,
            "totalChatbots": total_chatbots,
            "totalStorageMB": round(total_storage_mb, 2),
        }
    except Exception as e:
        logger.exception("Failed to fetch admin stats")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/admin/users")
async def get_admin_users(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute(
            """
            SELECT u.id, u.email, u.created_at, s.plan_tier, s.limits, u.is_super_admin
            FROM users u
            LEFT JOIN user_subscriptions s ON u.id = s.user_id
            ORDER BY u.created_at DESC
        """
        )
        users = []
        for r in cursor.fetchall():
            users.append(
                {
                    "id": r[0],
                    "email": r[1],
                    "created_at": r[2],
                    "plan_tier": r[3] or "Starter",
                    "limits": r[4] or {},
                    "is_super_admin": bool(r[5]),
                }
            )
        return {"users": users}
    except Exception as e:
        logger.exception("Failed to fetch admin users")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


class UpdateSubscriptionRequest(BaseModel):
    plan_tier: str
    admin_user_id: str
    admin_action_password: str


@router.post("/admin/users/{target_user_id}/subscription")
async def update_user_subscription(target_user_id: str, req: UpdateSubscriptionRequest):
    conn = None
    cursor = None
    try:
        check_action_password(req.admin_action_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(req.admin_user_id, cursor)

        cursor.execute(
            """
            INSERT INTO user_subscriptions (user_id, plan_tier)
            VALUES (%s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET plan_tier = EXCLUDED.plan_tier, updated_at = now()
        """,
            (target_user_id, req.plan_tier),
        )
        conn.commit()
        return {"message": "Subscription updated successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        if not isinstance(e, HTTPException):
            logger.exception("Failed to update user subscription")
            raise HTTPException(status_code=500, detail=str(e))
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class UpdateSuperAdminRequest(BaseModel):
    is_super_admin: bool
    admin_user_id: str
    admin_action_password: str

@router.post("/admin/users/{target_user_id}/super_admin")
async def update_user_super_admin(target_user_id: str, req: UpdateSuperAdminRequest):
    conn = None
    cursor = None
    try:
        check_action_password(req.admin_action_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(req.admin_user_id, cursor)
        cursor.execute(
            """
            UPDATE users SET is_super_admin = %s WHERE id = %s
            """,
            (req.is_super_admin, target_user_id)
        )
        conn.commit()
        return {"message": "Super Admin status updated successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        if not isinstance(e, HTTPException):
            logger.exception("Failed to update super admin status")
            raise HTTPException(status_code=500, detail=str(e))
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.get("/admin/workspaces")
async def get_admin_workspaces(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute(
            """
            SELECT 
                w.id, w.name, w.created_at, w.owner_id,
                u.email as owner_email,
                (SELECT COUNT(*) FROM workspace_members wm WHERE wm.workspace_id = w.id) as member_count
            FROM workspaces w
            LEFT JOIN users u ON w.owner_id = u.id
            ORDER BY w.created_at DESC
        """
        )
        workspaces = []
        for r in cursor.fetchall():
            workspaces.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "created_at": r[2],
                    "owner_id": r[3],
                    "owner_email": r[4],
                    "member_count": r[5],
                }
            )
        return {"workspaces": workspaces}
    except Exception as e:
        logger.exception("Failed to fetch admin workspaces")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
