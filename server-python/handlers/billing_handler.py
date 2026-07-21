import json
import logging
import razorpay
from fastapi import HTTPException
from core.dependencies import razorpay_client, RAZORPAY_KEY_ID
from db import billing_repository

logger = logging.getLogger(__name__)


async def handle_get_subscription(user_id: str):
    try:
        row = await billing_repository.get_user_subscription(user_id)
        
        if not row:
            return {
                "plan_tier": "Starter",
                "billing_cycle": "monthly",
                "status": "active"
            }
            
        return {
            "plan_tier": row[0],
            "billing_cycle": row[1],
            "status": row[2],
            "limits": row[3]
        }
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
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
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

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

    try:
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
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key": RAZORPAY_KEY_ID,
        }
    except Exception as e:
        logger.exception("Razorpay order creation failed")
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
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    try:
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

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

            await billing_repository.upsert_user_subscription(user_id, plan_tier, billing_cycle, limits_json)
            logger.info(f"Subscription updated for user {user_id}")
        except Exception as e:
            logger.exception("Failed to update subscription in DB")
            raise HTTPException(
                status_code=500, detail="Database error during subscription update"
            )

        return {"status": "success"}
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
