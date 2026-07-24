"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the backend handler for administrative actions in RAGMate.
It contains functions to perform super-admin operations, fetch usage statistics,
manage registered users, adjust subscription plans, grant/revoke admin status,
and monitor workspace registries.

From top to bottom, the file executes as follows:
1. Imports: Loads standard libraries (os), web framework utilities (FastAPI's 
   HTTPException), database access layer (admin_repository), and department-based 
   logging.
2. Helper Guards: Defines validation functions to assert if the current requester 
   is a registered Super Admin (`check_super_admin`) and if the action password 
   matches the secret key configured on the server (`check_action_password`).
3. Stats Handler: Fetches system-wide usage metrics (total users, workspaces, agents).
4. Registry Handlers: Retrieves collections of all users (`handle_get_admin_users`)
   and workspaces (`handle_get_admin_workspaces`).
5. Modification Handlers: Modifies subscription tiers (`handle_update_user_subscription`)
   and super-admin capabilities (`handle_update_user_super_admin`) for target users.
"""

import os  # Standard utility to read environment variables from the OS
from fastapi import HTTPException  # FastAPI wrapper to raise clean HTTP responses with status codes
from db import admin_repository  # Database communication layer for admin functions

# Imports the logging utility to track execution logs and system errors
from utils.logger import get_department_logger

# Initialize a department logger specifically scoped to "system" activities
logger = get_department_logger("system")


async def check_super_admin(user_id: str):
    """
    Validates whether a given user ID has Super Admin privileges.
    
    If the user has Super Admin status, this function finishes normally.
    If the user is not a Super Admin, it throws an HTTP 403 Forbidden exception.

    Parameters:
        user_id (str): The unique database UUID string identifying the user.
        
    Returns:
        None: Returns nothing if successful.
        
    Exceptions Raised:
        HTTPException(403): Raised if the user is not found or does not have super admin flags.
    """
    # Log a debugging message indicating we are starting verification
    logger.debug(f"Verifying Super Admin status for user ID: {user_id}")
    
    # Query the database repository to check the super_admin boolean column for this user ID
    row = await admin_repository.get_user_super_admin_status(user_id)
    
    # If the database returns no row, or if the first column (is_super_admin) evaluates to False
    if not row or not row[0]:
        # Log a warning to flag unauthorized access attempt
        logger.warning(f"Super Admin access denied for user ID: {user_id}")
        # Terminate execution and return a 403 Forbidden error response to the client
        raise HTTPException(status_code=403, detail="Super Admin access required")
        
    # If validation passes, print a success debug statement
    logger.debug(f"Super Admin status verified for user ID: {user_id}")


def check_action_password(password: str):
    """
    Checks if a provided password matches the master admin action password configured in the system environment.
    This acts as a second-factor validation before performing critical modifications.

    Parameters:
        password (str): The plain-text password supplied in the API payload.
        
    Returns:
        None: Returns nothing if passwords match.
        
    Exceptions Raised:
        HTTPException(500): Raised if the environment variable ADMIN_ACTION_PASSWORD is missing on the server.
        HTTPException(403): Raised if the provided password does not match the configured master password.
    """
    # Log that we are entering action password check
    logger.debug("Verifying admin action password...")
    
    # Fetch the secret token from the server's environment configurations
    expected_password = os.getenv("ADMIN_ACTION_PASSWORD")
    
    # If the system administrator did not set up the password on the server
    if not expected_password:
        # Log a critical configuration error
        logger.error("Admin configuration error: ADMIN_ACTION_PASSWORD is not configured.")
        # Return a 500 Internal Server Error notifying that the server setup is incomplete
        raise HTTPException(status_code=500, detail="Server configuration error: ADMIN_ACTION_PASSWORD not set")
        
    # If the password supplied by the requester does not match the expected secret password
    if password != expected_password:
        # Log a warning indicating password mismatch
        logger.warning("Admin verification failed: Invalid action password supplied.")
        # Return a 403 Forbidden error response
        raise HTTPException(status_code=403, detail="Invalid action password")
        
    # Log successful verification
    logger.debug("Admin action password verified successfully.")


async def handle_get_admin_stats(user_id: str):
    """
    Fetches global administrative system metrics for the dashboard.
    
    Parameters:
        user_id (str): The ID of the administrator requesting stats.
        
    Returns:
        dict: A dictionary object containing aggregated counts (users, workspaces, etc.).
        
    Exceptions Raised:
        HTTPException(403): Raised if requester is not a Super Admin.
        HTTPException(500): Raised if database queries fail.
    """
    # Log request start with the user ID initiating it
    logger.info(f"Admin request: Fetching dashboard stats by user ID: {user_id}")
    try:
        # 1. Authorize the user (ensure they are indeed a Super Admin)
        await check_super_admin(user_id)
        
        # 2. Retrieve statistics from the database
        stats = await admin_repository.get_admin_stats()
        
        # Log success
        logger.info("Successfully retrieved admin stats.")
        
        # 3. Return statistics payload
        return stats
    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve proper client status codes (403, 401)
        raise
    except Exception as e:
        # Log the unexpected system exception along with stack trace logs
        logger.error(f"Failed to fetch admin stats: {str(e)}", exc_info=True)
        # Raise 500 status code indicating database or script breakdown
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_users(user_id: str):
    """
    Fetches a listing of all registered users in the database along with their plan levels.

    Parameters:
        user_id (str): The ID of the administrator requesting the list.
        
    Returns:
        dict: A dictionary with a key "users" containing a list of user dictionaries.
        
    Exceptions Raised:
        HTTPException(403): Raised if requester is not a Super Admin.
        HTTPException(500): Raised if database queries fail.
    """
    # Log user listing request
    logger.info(f"Admin request: Fetching user registry by user ID: {user_id}")
    try:
        # 1. Verify administrative access
        await check_super_admin(user_id)
        
        # 2. Fetch raw database row tuples
        logger.debug("Querying users list from database...")
        rows = await admin_repository.get_admin_users()
        logger.debug(f"Retrieved {len(rows)} user entries.")
        
        # 3. Format raw tuple rows into structured JSON dictionary structures
        users = []
        for r in rows:
            users.append(
                {
                    "id": r[0],                            # User UUID
                    "email": r[1],                         # Email address
                    "created_at": r[2],                    # Registration timestamp
                    "plan_tier": r[3] or "Starter",        # Subscription tier
                    "limits": r[4] or {},                  # User plan thresholds limits
                    "is_super_admin": bool(r[5]),          # Super Admin flag casted to Boolean
                }
            )
        
        # Log structured results formatting count
        logger.info(f"Successfully processed {len(users)} users.")
        return {"users": users}
    except HTTPException:
        # Bubble up auth exceptions (403)
        raise
    except Exception as e:
        # Log system errors
        logger.error(f"Failed to fetch admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_subscription(target_user_id: str, req: dict):
    """
    Updates the subscription tier for a specific target user.

    Parameters:
        target_user_id (str): The user ID of the account being upgraded or downgraded.
        req (dict): Payload dictionary containing:
            - "admin_action_password": Double-factor password check.
            - "admin_user_id": Requester's super admin ID.
            - "plan_tier": String matching new target tier (e.g. 'Pro', 'Enterprise').
            
    Returns:
        dict: A success message payload.

    Exceptions Raised:
        HTTPException(403): Raised for password or role authentication failures.
        HTTPException(500): Raised if updates fail.
    """
    # Log modification request
    logger.info(f"Admin request: Updating subscription for target user ID: {target_user_id}")
    try:
        # 1. Assert action password check
        check_action_password(req.get("admin_action_password"))
        
        # 2. Assert requester is a Super Admin
        await check_super_admin(req.get("admin_user_id"))

        # 3. Extract the new tier from payload
        plan_tier = req.get("plan_tier")
        logger.debug(f"Updating user {target_user_id} subscription plan to: {plan_tier} in database...")
        
        # 4. Modify target row in the database
        await admin_repository.upsert_user_subscription(target_user_id, plan_tier)
        
        # Log transaction success
        logger.info(f"User {target_user_id} subscription plan successfully updated to {plan_tier}.")
        return {"message": "Subscription updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subscription for user {target_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_user_super_admin(target_user_id: str, req: dict):
    """
    Promotes or demotes a target user's Super Admin privileges.

    Parameters:
        target_user_id (str): The user ID of the account whose status is being changed.
        req (dict): Payload dictionary containing:
            - "admin_action_password": Double-factor password check.
            - "admin_user_id": Requester's super admin ID.
            - "is_super_admin": Boolean value to set.
            
    Returns:
        dict: A success message payload.

    Exceptions Raised:
        HTTPException(403): Raised for password or role authentication failures.
        HTTPException(500): Raised if updates fail.
    """
    # Log promotion/demotion request
    logger.info(f"Admin request: Updating super admin status for target user ID: {target_user_id}")
    try:
        # 1. Assert action password check
        check_action_password(req.get("admin_action_password"))
        
        # 2. Assert requester is a Super Admin
        await check_super_admin(req.get("admin_user_id"))
        
        # 3. Extract target privilege state
        is_super = req.get("is_super_admin")
        logger.debug(f"Updating user {target_user_id} is_super_admin flag to: {is_super}...")
        
        # 4. Save new status flag in database
        await admin_repository.update_user_super_admin(target_user_id, is_super)
        
        # Log transaction success
        logger.info(f"User {target_user_id} super admin status successfully set to {is_super}.")
        return {"message": "Super Admin status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update super admin status for user {target_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_workspaces(user_id: str):
    """
    Fetches a listing of all active workspaces in the system.

    Parameters:
        user_id (str): The ID of the administrator requesting workspaces.
        
    Returns:
        dict: A dictionary containing workspace dictionaries registry.
        
    Exceptions Raised:
        HTTPException(403): Raised if requester is not a Super Admin.
        HTTPException(500): Raised if database queries fail.
    """
    # Log workspaces listing request
    logger.info(f"Admin request: Fetching workspace registry by user ID: {user_id}")
    try:
        # 1. Verify administrative access
        await check_super_admin(user_id)

        # 2. Fetch raw workspace tuples from database
        logger.debug("Querying workspaces list from database...")
        rows = await admin_repository.get_admin_workspaces()
        logger.debug(f"Retrieved {len(rows)} workspace entries.")
        
        # 3. Map raw tuple rows into structured JSON dictionary elements
        workspaces = []
        for r in rows:
            workspaces.append(
                {
                    "id": r[0],                     # Workspace UUID
                    "name": r[1],                   # Workspace Title/Name
                    "created_at": r[2],             # Creation date
                    "owner_id": r[3],               # Owner's User ID
                    "owner_email": r[4],            # Owner's Email address
                    "member_count": r[5],           # Total active workspace members
                }
            )
            
        # Log successful completion
        logger.info(f"Successfully processed {len(workspaces)} workspaces.")
        return {"workspaces": workspaces}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch admin workspaces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
