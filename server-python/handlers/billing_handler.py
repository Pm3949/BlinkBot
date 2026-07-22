import json
import razorpay
from fastapi import HTTPException
from core.dependencies import razorpay_client, RAZORPAY_KEY_ID
from db import billing_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")


async def handle_get_subscription(user_id: str):
    logger.info(f"Retrieving subscription details for user ID: {user_id}")
    try:
        logger.debug("Querying subscription table in database...")
        row = await billing_repository.get_user_subscription(user_id)
        
        if not row:
            logger.info(f"No active subscription found. Returning default Starter limits for user {user_id}.")
            return {
                "plan_tier": "Starter",
                "billing_cycle": "monthly",
                "status": "active"
            }
            
        logger.info(f"Active subscription retrieved for user {user_id}: tier={row[0]}, status={row[2]}")
        return {
            "plan_tier": row[0],
            "billing_cycle": row[1],
            "status": row[2],
            "limits": row[3]
        }
    except Exception as e:
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
    logger.info(f"Initiating Razorpay payment order for user ID: {user_id} (Plan: {plan_tier}, Cycle: {billing_cycle})")
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    logger.debug(f"Calculating final price details. workspaces_limit={workspaces_limit}, agents_limit={agents_limit}, storage={storage_mb_limit}MB")
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
        # Custom plan metrics price accumulation
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

    amount = int(final_amount * 100) 
    logger.debug(f"Calculated billing amount: INR {final_amount} (Amount in paise: {amount})")

    try:
        logger.debug("Requesting order creation from Razorpay API...")
        order = razorpay_client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "receipt": f"receipt_{user_id[:8]}",
                "notes": {
                    "user_id": user_id,
                    "plan_tier": plan_tier,
                    "billing_cycle": billing_cycle,
                },
            }
        )
        logger.info(f"Razorpay order successfully created. Order ID: {order['id']}")
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key": RAZORPAY_KEY_ID,
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
    logger.info(f"Verifying Razorpay payment signature for Order ID: {razorpay_order_id} (User ID: {user_id})")
    if not razorpay_client:
        logger.error("Razorpay integration error: Razorpay client keys not configured in server env.")
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    try:
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
        logger.warning(f"Razorpay payment verification rejected: Invalid payment signature for Order ID {razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Razorpay payment verification failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
