"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script handles the subscription plans and Razorpay payment integration
for RAGMate users.

From top to bottom, the file performs the following tasks:
1. Imports: Loads JSON serializers, the Razorpay integration client library,
   FastAPI web exceptions, and local database repositories.
2. Logging: Scopes a department logger named "system" to audit billing activities.
3. Subscription Getter (`handle_get_subscription`): Queries the database for the 
   active plan limits, falling back to a free "Starter" plan if no subscription exists.
4. Payment Order Creation (`handle_create_razorpay_order`):
   - Computes the final transaction amount in Indian Rupees (INR) based on 
     the chosen subscription tier (Pro, Enterprise, Custom metrics) and cycle (annually/monthly).
   - Multiplies the total by 100 to convert to paisa (as required by Razorpay API).
   - Generates an order inside Razorpay and returns the order reference credentials.
5. Payment Signature Verification (`handle_verify_razorpay_payment`):
   - Uses the Razorpay cryptographic client to verify that the payment signature
     sent by the browser is authentic (preventing spoofing).
   - On success, updates/inserts the subscription tier and numerical limits 
     (messages count, agents, workspaces, storage size) in the user's database settings.
"""

import json  # Import utility to parse and format Python JSON dictionaries
import razorpay  # Import the official Razorpay SDK library to interface with payment APIs
from fastapi import HTTPException  # Import web exceptions to raise user-facing HTTP status codes
from core.dependencies import razorpay_client, RAZORPAY_KEY_ID  # Fetch global Razorpay API credentials
from db import billing_repository  # Fetch database repository layer to update subscriptions

# Logging utilities
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "system" activities
logger = get_department_logger("system")


async def handle_get_subscription(user_id: str):
    """
    Retrieves the current subscription plan details and workspace limits for a user.
    If no active plan is found in the database, falls back to the default "Starter" tier.

    Parameters:
        user_id (str): The unique database UUID identifying the target user.

    Returns:
        dict: A subscription dictionary containing 'plan_tier', 'billing_cycle', 'status', and 'limits'.

    Exceptions Raised:
        HTTPException(500): Raised if database queries fail.
    """
    # Log information indicating retrieval is initiated
    logger.info(f"Retrieving subscription details for user ID: {user_id}")
    try:
        # Query database row matching user_id in subscription table
        logger.debug("Querying subscription table in database...")
        row = await billing_repository.get_user_subscription(user_id)
        
        # If the database query returns empty (signifying a new or free user)
        if not row:
            # Fall back to free default Starter tier limits
            logger.info(f"No active subscription found. Returning default Starter limits for user {user_id}.")
            return {
                "plan_tier": "Starter",
                "billing_cycle": "monthly",
                "status": "active"
            }
            
        # Log successful retrieval
        logger.info(f"Active subscription retrieved for user {user_id}: tier={row[0]}, status={row[2]}")
        return {
            "plan_tier": row[0],         # Subscription Tier (Starter, Pro, Enterprise, Custom)
            "billing_cycle": row[1],    # Cycle (monthly or annually)
            "status": row[2],           # Payment status (active, trailing, cancelled)
            "limits": row[3]            # Numerical limits configured for the plan
        }
    except Exception as e:
        # Catch unexpected errors, log trace, and raise 500 status
        logger.error(f"Error fetching subscription for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


async def handle_create_razorpay_order(
    user_id: str,
    plan_tier: str,
    billing_cycle: str,
    workspaces_limit: int,
    agents_limit: int,
    agent_messages_limit: int,
    storage_mb_limit: int,
    chatbots_limit: int,
    chatbot_messages_limit: int
):
    """
    Computes the price based on subscription selections and generates a Razorpay Order.

    Parameters:
        user_id (str): The unique database UUID of the user.
        plan_tier (str): Target subscription tier ('Pro', 'Enterprise', or 'Custom').
        billing_cycle (str): Plan frequency ('monthly' or 'annually').
        workspaces_limit (int): Allowed workspaces (for Custom plan).
        agents_limit (int): Allowed agents (for Custom plan).
        agent_messages_limit (int): Message quota count (for Custom plan).
        storage_mb_limit (int): Vector database storage size in Megabytes (for Custom plan).
        chatbots_limit (int): Allowed widget chatbots (for Custom plan).
        chatbot_messages_limit (int): Widget message quota (for Custom plan).

    Returns:
        dict: A dictionary containing the newly registered Razorpay order ID and payment credentials.

    Exceptions Raised:
        HTTPException(500): Raised if Razorpay SDK keys are missing or order creation fails.
    """
    # Log order parameters
    logger.info(f"Initiating Razorpay payment order for user ID: {user_id} (Plan: {plan_tier}, Cycle: {billing_cycle})")
    
    # Assert Razorpay client initialized (keys configured on server env)
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    logger.debug(f"Calculating final price details. workspaces_limit={workspaces_limit}, agents_limit={agents_limit}, storage={storage_mb_limit}MB")
    
    # 1. Price calculation logic
    if plan_tier == "Pro":
        # Flat rate of 1900 INR/month
        monthly_total = 1900
        # Apply 20% discount (0.8 multiplier) for annual billing cycles
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )
    elif plan_tier == "Enterprise":
        # Flat rate of 9900 INR/month
        monthly_total = 9900
        # Apply 20% discount for annual billing cycles
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )
    else:
        # Custom plan configuration: calculate price based on user-selected metric sliders
        base_price = 800                                            # Base platform entry price
        workspaces_price = workspaces_limit * 500                   # 500 INR per workspace
        agents_price = agents_limit * 400                           # 400 INR per agent
        agent_msg_price = (agent_messages_limit / 1000.0) * 160     # 160 INR per 1000 messages
        storage_price = (storage_mb_limit / 100.0) * 50             # 50 INR per 100 MB vectors
        chatbots_price = chatbots_limit * 800                       # 800 INR per widget chatbot
        chatbot_msg_price = (chatbot_messages_limit / 1000.0) * 200 # 200 INR per 1000 widget messages

        # Add up prices
        monthly_total = (
            base_price
            + workspaces_price
            + agents_price
            + agent_msg_price
            + storage_price
            + chatbots_price
            + chatbot_msg_price
        )
        # Apply 20% discount for annual billing cycles
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )

    # Convert Rupee float amount into Integer Paisa value (Razorpay requirement: e.g. 100 paisa = 1 INR)
    amount = int(final_amount * 100) 
    logger.debug(f"Calculated billing amount: INR {final_amount} (Amount in paise: {amount})")

    try:
        # Invoke Razorpay SDK API to register payment transaction
        logger.debug("Requesting order creation from Razorpay API...")
        order = razorpay_client.order.create(
            {
                "amount": amount,                      # Amount in paisa
                "currency": "INR",                     # Currency code
                "receipt": f"receipt_{user_id[:8]}",   # Random tracking identifier string
                "notes": {                             # Pass state payload data to recover during callback verification
                    "user_id": user_id,
                    "plan_tier": plan_tier,
                    "billing_cycle": billing_cycle,
                },
            }
        )
        # Log successful creation
        logger.info(f"Razorpay order successfully created. Order ID: {order['id']}")
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key": RAZORPAY_KEY_ID,                    # Public Key returned so frontend SDK knows client ID
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_verify_razorpay_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    user_id: str,
    plan_tier: str,
    billing_cycle: str,
    workspaces_limit: int,
    agents_limit: int,
    agent_messages_limit: int,
    storage_mb_limit: int,
    chatbots_limit: int,
    chatbot_messages_limit: int
):
    """
    Verifies the cryptographic payment signature returned by the client.
    If valid, updates/upserts the target subscription tier configurations and limits in the database.

    Parameters:
        razorpay_order_id (str): The unique Razorpay Order ID created in the previous step.
        razorpay_payment_id (str): Transaction payment ID from Razorpay.
        razorpay_signature (str): SHA-256 HMAC verification signature generated by Razorpay.
        user_id (str): Target user database UUID.
        plan_tier (str): Subscribed plan tier (e.g. Pro, Custom).
        billing_cycle (str): Plan frequency ('monthly' or 'annually').
        workspaces_limit (int): Subscription workspaces count.
        agents_limit (int): Subscription agents count.
        agent_messages_limit (int): Message usage limit.
        storage_mb_limit (int): Target vector DB limits.
        chatbots_limit (int): Target chatbots limit.
        chatbot_messages_limit (int): Widget message limit.

    Returns:
        dict: Success verification payload.

    Exceptions Raised:
        HTTPException(400): Raised if the signature verification fails (tampering/unpaid).
        HTTPException(500): Raised if database queries fail.
    """
    logger.info(f"Verifying Razorpay payment signature for Order ID: {razorpay_order_id} (User ID: {user_id})")
    
    # Assert Razorpay is configured
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    try:
        # Cryptographically check that the payment signature matches the order and payment ID
        logger.debug("Executing signature verification check in razorpay utility client...")
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        logger.info("Razorpay payment signature successfully verified.")

        try:
            # Format numerical limits into a JSON string structure
            limits_json = json.dumps(
                {
                    "workspaces": workspaces_limit,
                    "agents": agents_limit,
                    "agent_messages": agent_messages_limit,
                    "storage_mb": storage_mb_limit,
                    "chatbots": chatbots_limit,
                    "chatbot_messages": chatbot_messages_limit,
                }
            )

            # Update subscription details inside the DB
            logger.debug(f"Saving updated user subscription plan parameters to database for user {user_id}...")
            await billing_repository.upsert_user_subscription(user_id, plan_tier, billing_cycle, limits_json)
            logger.info(f"Subscription plan updated successfully in database for user ID: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user subscription status in DB: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Database error during subscription update"
            )

        return {"status": "success"}
    except razorpay.errors.SignatureVerificationError:
        # Triggered if signature mismatch occurs (signifies tampering or failed transaction status)
        logger.warning(f"Razorpay payment verification rejected: Invalid payment signature for Order ID {razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Razorpay payment verification failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
