import os
from fastapi import HTTPException
from db import admin_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")

async def check_super_admin(user_id: str):
    logger.debug(f"Verifying Super Admin status for user ID: {user_id}")
    row = await admin_repository.get_user_super_admin_status(user_id)
    if not row or not row[0]:
        logger.warning(f"Super Admin access denied for user ID: {user_id}")
        raise HTTPException(status_code=403, detail="Super Admin access required")
    logger.debug(f"Super Admin status verified for user ID: {user_id}")

def check_action_password(password: str):
    logger.debug("Verifying admin action password...")
    expected_password = os.getenv("ADMIN_ACTION_PASSWORD")
    if not expected_password:
        logger.error("Admin configuration error: ADMIN_ACTION_PASSWORD is not configured.")
        raise HTTPException(status_code=500, detail="Server configuration error: ADMIN_ACTION_PASSWORD not set")
    if password != expected_password:
        logger.warning("Admin verification failed: Invalid action password supplied.")
        raise HTTPException(status_code=403, detail="Invalid action password")
    logger.debug("Admin action password verified successfully.")


async def handle_get_admin_stats(user_id: str):
    logger.info(f"Admin request: Fetching dashboard stats by user ID: {user_id}")
    try:
        await check_super_admin(user_id)
        stats = await admin_repository.get_admin_stats()
        logger.info("Successfully retrieved admin stats.")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch admin stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_users(user_id: str):
    logger.info(f"Admin request: Fetching user registry by user ID: {user_id}")
    try:
        await check_super_admin(user_id)
        
        logger.debug("Querying users list from database...")
        rows = await admin_repository.get_admin_users()
        logger.debug(f"Retrieved {len(rows)} user entries.")
        
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
        logger.info(f"Successfully processed {len(users)} users.")
        return {"users": users}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_subscription(target_user_id: str, req: dict):
    logger.info(f"Admin request: Updating subscription for target user ID: {target_user_id}")
    try:
        check_action_password(req.get("admin_action_password"))
        await check_super_admin(req.get("admin_user_id"))

        plan_tier = req.get("plan_tier")
        logger.debug(f"Updating user {target_user_id} subscription plan to: {plan_tier} in database...")
        await admin_repository.upsert_user_subscription(target_user_id, plan_tier)
        
        logger.info(f"User {target_user_id} subscription plan successfully updated to {plan_tier}.")
        return {"message": "Subscription updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription for user {target_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_super_admin(target_user_id: str, req: dict):
    logger.info(f"Admin request: Updating super admin status for target user ID: {target_user_id}")
    try:
        check_action_password(req.get("admin_action_password"))
        await check_super_admin(req.get("admin_user_id"))
        
        is_super = req.get("is_super_admin")
        logger.debug(f"Updating user {target_user_id} is_super_admin flag to: {is_super}...")
        await admin_repository.update_user_super_admin(target_user_id, is_super)
        
        logger.info(f"User {target_user_id} super admin status successfully set to {is_super}.")
        return {"message": "Super Admin status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update super admin status for user {target_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_workspaces(user_id: str):
    logger.info(f"Admin request: Fetching workspace registry by user ID: {user_id}")
    try:
        await check_super_admin(user_id)

        logger.debug("Querying workspaces list from database...")
        rows = await admin_repository.get_admin_workspaces()
        logger.debug(f"Retrieved {len(rows)} workspace entries.")
        
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
        logger.info(f"Successfully processed {len(workspaces)} workspaces.")
        return {"workspaces": workspaces}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch admin workspaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
