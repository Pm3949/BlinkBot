import logging
import os
from fastapi import HTTPException
from db import admin_repository

logger = logging.getLogger(__name__)

async def check_super_admin(user_id: str):
    row = await admin_repository.get_user_super_admin_status(user_id)
    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="Super Admin access required")

def check_action_password(password: str):
    expected_password = os.getenv("ADMIN_ACTION_PASSWORD")
    if not expected_password:
        raise HTTPException(status_code=500, detail="Server configuration error: ADMIN_ACTION_PASSWORD not set")
    if password != expected_password:
        raise HTTPException(status_code=403, detail="Invalid action password")


async def handle_get_admin_stats(user_id: str):
    try:
        await check_super_admin(user_id)
        return await admin_repository.get_admin_stats()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch admin stats")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_users(user_id: str):
    try:
        await check_super_admin(user_id)
        
        rows = await admin_repository.get_admin_users()
        users = []
        for r in rows:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch admin users")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_subscription(target_user_id: str, req: dict):
    try:
        check_action_password(req.get("admin_action_password"))
        await check_super_admin(req.get("admin_user_id"))

        await admin_repository.upsert_user_subscription(target_user_id, req.get("plan_tier"))
        return {"message": "Subscription updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update user subscription")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_super_admin(target_user_id: str, req: dict):
    try:
        check_action_password(req.get("admin_action_password"))
        await check_super_admin(req.get("admin_user_id"))
        
        await admin_repository.update_user_super_admin(target_user_id, req.get("is_super_admin"))
        return {"message": "Super Admin status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update super admin status")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_workspaces(user_id: str):
    try:
        await check_super_admin(user_id)

        rows = await admin_repository.get_admin_workspaces()
        workspaces = []
        for r in rows:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch admin workspaces")
        raise HTTPException(status_code=500, detail=str(e))
