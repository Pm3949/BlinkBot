import logging
from fastapi import APIRouter, Depends
from schemas import CheckoutRequest, RazorpayVerifyRequest
from core.auth import get_current_user

from handlers.billing_handler import (
    handle_get_subscription,
    handle_create_razorpay_order,
    handle_verify_razorpay_payment
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


@router.get("/api/billing/subscription")
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch a user's active billing tier and resource limits.
    Args:
        user_id (str): The ID of the user.
    Returns: A dictionary with subscription status and limits.
    """
    user_id = current_user["sub"]
    return await handle_get_subscription(user_id)


@router.post("/create-razorpay-order")
async def create_razorpay_order(req: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to generate a secure Razorpay Order ID for a new purchase.
    Args:
        req (CheckoutRequest): The requested plan and limits.
    Returns: Order details needed by the frontend payment modal.
    """
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
    What it does: HTTP endpoint to securely verify a completed payment signature and upgrade the user.
    Args:
        req (RazorpayVerifyRequest): The payment IDs, cryptographic signature, and new limits.
    Returns: A success status dictionary.
    """
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
