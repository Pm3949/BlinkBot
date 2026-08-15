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


def calculate_subscription_price(
    plan_tier: str,
    billing_cycle: str,
    workspaces_limit: int,
    agents_limit: int,
    agent_messages_limit: int,
    storage_mb_limit: int,
    chatbots_limit: int,
    chatbot_messages_limit: int
) -> float:
    """
    Computes subscription prices based on tier and active resource quotas.
    """
    if plan_tier == "Pro":
        monthly_total = 1900
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )
    elif plan_tier == "Enterprise":
        monthly_total = 9900
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )
    else:
        # Custom plan configuration
        base_price = 800
        workspaces_price = workspaces_limit * 500
        agents_price = agents_limit * 400
        agent_msg_price = (agent_messages_limit / 1000.0) * 160
        storage_price = (storage_mb_limit / 100.0) * 50
        chatbots_price = chatbots_limit * 800
        chatbot_msg_price = (chatbot_messages_limit / 1000.0) * 200

        monthly_total = (
            base_price
            + workspaces_price
            + agents_price
            + agent_msg_price
            + storage_price
            + chatbots_price
            + chatbot_msg_price
        )
        final_amount = (
            (monthly_total * 12) * 0.8
            if billing_cycle == "annually"
            else monthly_total
        )
    return float(final_amount)


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
    """
    # Log order parameters
    logger.info(f"Initiating Razorpay payment order for user ID: {user_id} (Plan: {plan_tier}, Cycle: {billing_cycle})")
    
    # Assert Razorpay client initialized (keys configured on server env)
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    logger.debug(f"Calculating final price details. workspaces_limit={workspaces_limit}, agents_limit={agents_limit}, storage={storage_mb_limit}MB")
    
    # Calculate price using utility
    final_amount = calculate_subscription_price(
        plan_tier, billing_cycle, workspaces_limit, agents_limit,
        agent_messages_limit, storage_mb_limit, chatbots_limit, chatbot_messages_limit
    )

    # Convert Rupee float amount into Integer Paisa value
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

            # Generate invoice records in database
            final_amount = calculate_subscription_price(
                plan_tier, billing_cycle, workspaces_limit, agents_limit,
                agent_messages_limit, storage_mb_limit, chatbots_limit, chatbot_messages_limit
            )
            import time
            import random
            inv_num = f"INV-SUB-{int(time.time())}-{random.randint(100, 999)}"
            await billing_repository.create_invoice(
                user_id=user_id,
                invoice_number=inv_num,
                amount_inr=final_amount,
                description=f"{plan_tier} Plan Subscription ({billing_cycle.capitalize()})",
                invoice_metadata={
                    "item": f"{plan_tier} Plan Subscription",
                    "billing_cycle": billing_cycle,
                    "limits": {
                        "workspaces": workspaces_limit,
                        "agents": agents_limit,
                        "agent_messages": agent_messages_limit,
                        "storage_mb": storage_mb_limit,
                        "chatbots": chatbots_limit,
                        "chatbot_messages": chatbot_messages_limit
                    }
                }
            )
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


async def handle_create_wallet_recharge_order(user_id: str, credits: int):
    """
    Creates a Razorpay order for wallet credits topup.
    """
    logger.info(f"Initiating Razorpay recharge order for user ID: {user_id} (Credits: {credits})")
    
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    if credits < 1000:
        raise HTTPException(status_code=400, detail="Minimum top-up is 1,000 credits")

    # Secure server-side calculation
    base_inr = credits / 10.0
    discount_pct = 0.0
    if 500.0 <= base_inr < 1000.0:
        discount_pct = 5.0
    elif base_inr >= 1000.0:
        discount_pct = 10.0
        
    final_payable_inr = base_inr * (1.0 - (discount_pct / 100.0))
    amount_paise = int(final_payable_inr * 100)

    try:
        order = razorpay_client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": "1"
            }
        )
        return {
            "id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": RAZORPAY_KEY_ID,
            "credits": credits,
            "base_inr": base_inr,
            "discount_percent": discount_pct,
            "final_payable_inr": final_payable_inr
        }
    except Exception as e:
        logger.error(f"Razorpay wallet recharge order creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Razorpay order creation failed")


async def handle_verify_wallet_recharge_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    user_id: str,
    credits: int
):
    """
    Verifies Razorpay wallet recharge signature and updates DB.
    """
    logger.info(f"Verifying Razorpay wallet payment signature for Order ID: {razorpay_order_id} (User ID: {user_id})")
    
    if not razorpay_client:
        logger.error("Razorpay client is not initialized.")
        raise HTTPException(status_code=500, detail="Razorpay integration disabled")

    try:
        # Cryptographic check
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        
        # Credit the prepaid wallet in the database
        await billing_repository.topup_wallet_credits(user_id, credits)

        # Calculate pricing securely and save to invoices table
        base_inr = credits / 10.0
        discount_pct = 0.0
        if 500.0 <= base_inr < 1000.0:
            discount_pct = 5.0
        elif base_inr >= 1000.0:
            discount_pct = 10.0
        final_payable_inr = base_inr * (1.0 - (discount_pct / 100.0))

        import time
        import random
        inv_num = f"INV-WL-{int(time.time())}-{random.randint(100, 999)}"
        invoice = await billing_repository.create_invoice(
            user_id=user_id,
            invoice_number=inv_num,
            amount_inr=final_payable_inr,
            description=f"Wallet top-up (+{credits:,} Credits)",
            invoice_metadata={
                "item": "Prepaid AI Model Credits",
                "credits": credits,
                "base_inr": base_inr,
                "discount_percent": discount_pct,
                "discount_amount": base_inr * (discount_pct / 100.0)
            }
        )
        
        # Create credit transaction log linked to the invoice
        invoice_id = invoice["id"] if invoice else None
        await billing_repository.create_credit_transaction(
            user_id=user_id,
            agent_id=None,
            amount_credits=credits,
            transaction_type="topup",
            model_used=None,
            invoice_id=invoice_id
        )
        
        return {"status": "success", "message": f"Successfully recharged wallet with {credits} credits."}
    except razorpay.errors.SignatureVerificationError:
        logger.warning(f"Razorpay wallet verification rejected: Invalid signature for Order ID {razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Razorpay wallet verification failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
