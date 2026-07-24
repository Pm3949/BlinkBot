"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Subscription Billing and 
Payment Integration (Razorpay) actions in the RAGMate backend. It maps incoming
HTTP REST requests directly to the underlying business logic executors defined
inside the billing handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging libraries, FastAPI APIRouter routing components,
   Pydantic schema validation structures, and JWT login guards (`get_current_user`).
2. Routing Initialization: Declares the APIRouter for 'billing' tag groupings.
3. HTTP Routes:
   - GET `/api/billing/subscription`: Fetches a user's active billing tier and resource limits.
   - POST `/create-razorpay-order`: Registers transaction orders with Razorpay.
   - POST `/razorpay/verify`: Validates HMAC payment signatures and updates subscription settings.
"""

import logging  # Import python logging library
from fastapi import APIRouter, Depends  # FastAPI Router object and Dependency Injection tools
from schemas import CheckoutRequest, RazorpayVerifyRequest  # Pydantic schemas validating payload bodies
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import billing handlers
from handlers.billing_handler import (
    handle_get_subscription,
    handle_create_razorpay_order,
    handle_verify_razorpay_payment
)

# Instantiate a scoped file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for billing endpoints, grouping with tags
router = APIRouter(tags=["billing"])


@router.get("/api/billing/subscription")
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to fetch a user's active billing tier and limits.
    Validates token authorizations in request headers.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing active plan limits.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract the subject (user UUID) from the validated JWT dictionary
    return await handle_get_subscription(user_id)  # Route task execution to handlers layer


@router.post("/create-razorpay-order")
async def create_razorpay_order(req: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to generate a secure Razorpay Order ID.

    Parameters:
        req (CheckoutRequest): Pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly registered Razorpay order credentials.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if order registration crashes.
    """
    # Route task execution to handlers layer, mapping payload parameters
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
    HTTP POST endpoint to verify cryptographic signature matching a completed Razorpay payment.

    Parameters:
        req (RazorpayVerifyRequest): Pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Success verification payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(400): Raised if cryptographic signature check fails.
        HTTPException(500): Raised if updates fail.
    """
    # Route task execution to handlers layer, mapping verification parameters
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
