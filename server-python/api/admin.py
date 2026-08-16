"""
================================================================================
SUPER ADMIN CONTROLLER LAYER (admin.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for administrative dashboard features.
It manages requests restricted to Super Administrators, handling platform-wide analytics
and status parameters:
1. Platform Metrics aggregation.
2. User and Subscription catalog retrieval.
3. Subscription Tier overrides.
4. Promotion/Demotion of administrative privileges.
5. Workspace mapping and count listings.

SECURITY PATTERN:
- Access to all paths mapped here is protected by the `get_current_user` JWT dependency injection check.
- The endpoints pass the subject identifier `sub` (representing the authenticated user's ID) to
  `handlers/admin_handler.py` functions, which query permissions roles to verify Super Admin status
  before executing queries.
- Operations that modify data (updating tiers, modifying admin status) require verification using
  the `admin_action_password` parameter.
"""

import logging
from utils.logger import get_department_logger
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import get_current_user

# Import system handlers that contain the business logic.
from handlers.admin_handler import (
    check_super_admin,
    check_action_password,
    handle_get_admin_stats,
    handle_get_admin_users,
    handle_update_user_subscription,
    handle_update_user_super_admin,
    handle_get_admin_workspaces,
    handle_get_admin_transactions,
    handle_get_financial_report,
    handle_create_platform_expense
)

# Set standard module-level logger.
logger = get_department_logger("system")

# Initialize APIRouter instance for admin routes.
# The 'tags' grouping tags these endpoints as "admin" in Swagger API documentation docs.
router = APIRouter(tags=["admin"])

# ==========================================
# PYDANTIC INPUT SCHEMAS
# ==========================================

from typing import Optional

class UpdateSubscriptionRequest(BaseModel):
    """
    Validation schema for manual user subscription overrides.
    """
    plan_tier: str # Target billing tier (e.g. 'Pro', 'Enterprise')
    admin_action_password: str # Verification password to confirm admin identity
    limits: Optional[dict] = None # Optional custom limits


class UpdateSuperAdminRequest(BaseModel):
    """
    Validation schema for promoting/demoting platform administrators.
    """
    is_super_admin: bool # Target administrative flag
    admin_action_password: str # Verification password to confirm admin identity


class CreateExpenseRequest(BaseModel):
    """
    Validation schema for creating a manual platform expense.
    """
    amount_inr: float
    description: str
    category: str



# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """
    Retrieves platform-wide system performance metrics.

    Purpose:
        Aggregates stats (e.g., total active users, workspaces, message metrics)
        for display on the admin landing dashboard header.

    Parameters:
        current_user (dict): JWT payload details injected by the auth dependency middleware.

    Returns:
        dict: High-level system statistics (totals, active counts, metrics).

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if the token is invalid or missing.
        - Raises 403 Forbidden if the calling user is not a Super Administrator.
    """
    # Extract the authenticated user's UUID from the JWT subject ("sub") claim.
    user_id = current_user["sub"]
    # Delegate query execution to the admin handler module.
    return await handle_get_admin_stats(user_id)


@router.get("/admin/users")
async def get_admin_users(current_user: dict = Depends(get_current_user)):
    """
    Retrieves a list of all registered users on the platform.

    Purpose:
        Queries users and active plan descriptions for list rendering.

    Parameters:
        current_user (dict): JWT payload details injected by the auth dependency.

    Returns:
        list of dict: Registered users list containing profiles, subscription tiers, and sign-up dates.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 Unauthorized if credentials verification fails.
        - Raises 403 Forbidden if the user is not a Super Admin.
    """
    # Extract the authenticated user's UUID.
    user_id = current_user["sub"]
    # Delegate database query tasks to handlers.
    return await handle_get_admin_users(user_id)


@router.post("/admin/users/{target_user_id}/subscription")
async def update_user_subscription(target_user_id: str, req: UpdateSubscriptionRequest, current_user: dict = Depends(get_current_user)):
    """
    Updates a user's subscription tier.

    Purpose:
        Enables administrators to manually modify subscription tiers (e.g. comping accounts).

    Parameters:
        target_user_id (str): The UUID of the user being modified.
        req (UpdateSubscriptionRequest): Pydantic validated body containing `plan_tier` and verification password.
        current_user (dict): JWT details.

    Returns:
        dict: Success message status payload.

    Side Effects / State Changes:
        - Modifies the subscription tier record in the database.

    Errors / Exceptions:
        - Raises 401/403 for authentication/permission issues.
        - Raises 400 Bad Request if the action password check fails or the plan is invalid.
    """
    # Convert Pydantic request attributes into a standard dictionary.
    data = req.dict()
    # Inject the calling administrator's user ID for logging and permissions verification.
    data["admin_user_id"] = current_user["sub"]
    # Delegate execution to the subscription updater handler.
    return await handle_update_user_subscription(target_user_id, data)


@router.post("/admin/users/{target_user_id}/super_admin")
async def update_user_super_admin(target_user_id: str, req: UpdateSuperAdminRequest, current_user: dict = Depends(get_current_user)):
    """
    Toggles a user's Super Administrator status.

    Purpose:
        Promotes or demotes an administrator.

    Parameters:
        target_user_id (str): The UUID of the user being modified.
        req (UpdateSuperAdminRequest): Pydantic body containing `is_super_admin` flag and verification password.
        current_user (dict): JWT details.

    Returns:
        dict: Success status payload.

    Side Effects / State Changes:
        - Modifies administrative flags on user profile records.

    Errors / Exceptions:
        - Raises 401/403 for auth errors.
        - Raises 400 if verification fails.
    """
    # Convert parameters to dictionary format.
    data = req.dict()
    # Log the calling admin's ID.
    data["admin_user_id"] = current_user["sub"]
    # Delegate role modifications to the handler.
    return await handle_update_user_super_admin(target_user_id, data)


@router.get("/admin/workspaces")
async def get_admin_workspaces(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all workspaces configured on the platform.

    Purpose:
        Lists workspaces and membership counts for management dashboards.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Workspaces entries containing title metadata and member totals.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401/403 on permission issues.
    """
    # Retrieve user ID.
    user_id = current_user["sub"]
    # Query workspaces data using the handler.
    return await handle_get_admin_workspaces(user_id)


@router.get("/admin/transactions")
async def get_admin_transactions(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all invoices / payments across all users.
    """
    user_id = current_user["sub"]
    return await handle_get_admin_transactions(user_id)


@router.get("/admin/finances")
async def get_admin_finances(interval: str = "monthly", current_user: dict = Depends(get_current_user)):
    """
    Retrieves a platform financial summary (revenue vs expenses).
    """
    user_id = current_user["sub"]
    return await handle_get_financial_report(user_id, interval)


@router.post("/admin/expenses")
async def create_admin_expense(req: CreateExpenseRequest, current_user: dict = Depends(get_current_user)):
    """
    Records a manual platform spend/cost transaction.
    """
    user_id = current_user["sub"]
    return await handle_create_platform_expense(user_id, req.amount_inr, req.description, req.category)


@router.post("/admin/invoice/{invoice_id}/send")
async def send_invoice_email_admin(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """
    Manually sends/emails the invoice receipt PDF to the customer.
    """
    from fastapi import HTTPException
    user_id = current_user["sub"]
    
    # 1. Verify super admin permissions
    await check_super_admin(user_id)
    
    # 2. Fetch full invoice details
    from db import billing_repository
    invoice = await billing_repository.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # 3. Generate PDF bytes
    from api.billing import generate_invoice_pdf_data
    pdf_bytes = generate_invoice_pdf_data(invoice)
    
    # 4. Dispatch Email
    from utils.email_service import send_invoice_email
    recipient_email = invoice.get("user_email")
    if recipient_email and recipient_email != "Unknown User":
        await send_invoice_email(recipient_email, invoice, pdf_bytes)
        return {
            "status": "success",
            "message": f"Invoice successfully emailed to {recipient_email}."
        }
    else:
        raise HTTPException(status_code=400, detail="User email not linked to this invoice. Cannot send email.")



