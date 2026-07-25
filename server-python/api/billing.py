"""
================================================================================
BILLING AND SUBSCRIPTION ROUTER LAYER (billing.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for the platform's payment integration
(Razorpay) and subscription management. It handles:
1. Subscription details: Retrieves users' active subscription status, billing periods, and workspace/agent limits.
2. Razorpay Order Generation: Creates secure orders with Razorpay, generating Order IDs for checkout modals.
3. Cryptographic Verification: Processes payment verification requests by validating HMAC-SHA256 signatures
   returned by Razorpay before upgrading accounts.

DATA FLOW:
- Clients query billing endpoints, authenticated by the `get_current_user` JWT dependency.
- Request payloads are validated using Pydantic models (`CheckoutRequest`, `RazorpayVerifyRequest`).
- Functions extract the user's UUID from the JWT subject (`sub`) and delegate operations to
  `handlers/billing_handler.py`.
"""

import logging
from fastapi import APIRouter, Depends
from schemas import CheckoutRequest, RazorpayVerifyRequest
from core.auth import get_current_user

# Import the payment and subscription handlers.
from handlers.billing_handler import (
    handle_get_subscription,
    handle_create_razorpay_order,
    handle_verify_razorpay_payment
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["billing"])


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/billing/subscription")
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the active subscription tier and resource limits of the authenticated user.

    Purpose:
        Fetches subscription info to verify quotas on the frontend.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        dict: Subscription details containing active limits (workspaces, agents, storage, chatbots, messages).

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Delegate the database query to the handler.
    return await handle_get_subscription(user_id)


@router.post("/create-razorpay-order")
async def create_razorpay_order(req: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates a secure Razorpay Order ID for checkouts.

    Purpose:
        Creates a payment order registered on Razorpay servers to initiate checkouts.

    Parameters:
        req (CheckoutRequest): Pydantic body containing requested plan tiers and resource limits.
        current_user (dict): JWT details.

    Returns:
        dict: Order details (id, currency, amount) returned by Razorpay.

    Side Effects / State Changes:
        - Registers a pending order on Razorpay servers.

    Errors / Exceptions:
        - Raises 400 Bad Request if the payment client fails to contact Razorpay APIs.
    """
    # Request order generation using the billing handler.
    return await handle_create_razorpay_order(
        current_user["sub"],
        req.plan_tier,
        req.billing_cycle,
        req.workspaces_limit,
        req.agents_limit,
        req.agent_messages_limit,
        req.storage_mb_limit,
        req.chatbots_limit,
        req.chatbot_messages_limit
    )


@router.post("/razorpay/verify")
async def verify_razorpay_payment(req: RazorpayVerifyRequest, current_user: dict = Depends(get_current_user)):
    """
    Verifies payment signatures and updates user subscriptions.

    Purpose:
        Validates the transaction's HMAC-SHA256 signature and upgrades user limits in the database.

    Parameters:
        req (RazorpayVerifyRequest): Contains Razorpay transaction IDs, signature, and target plan specifications.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates rows in `subscriptions` and `user_limits` database tables upon successful signature verification.

    Errors / Exceptions:
        - Raises 400 Bad Request if signature verification fails or if the transaction details are invalid.
    """
    # Delegate cryptographic checks and database modifications to the verification handler.
    return await handle_verify_razorpay_payment(
        req.razorpay_order_id,
        req.razorpay_payment_id,
        req.razorpay_signature,
        current_user["sub"],
        req.plan_tier,
        req.billing_cycle,
        req.workspaces_limit,
        req.agents_limit,
        req.agent_messages_limit,
        req.storage_mb_limit,
        req.chatbots_limit,
        req.chatbot_messages_limit
    )

