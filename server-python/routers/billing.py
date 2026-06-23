"""
Billing Router.
Responsibility: Integrates with Razorpay to handle payment processing, subscription 
upgrades, and dynamic pricing for Custom Enterprise plans. Validates payment signatures 
securely on the backend.
"""
import json
import logging
import razorpay
from fastapi import APIRouter, HTTPException
from database import get_db_connection
from schemas import CheckoutRequest, RazorpayVerifyRequest
from core.dependencies import razorpay_client, RAZORPAY_KEY_ID

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])

# ==========================================
# SUBSCRIPTION FETCHING
# ==========================================

@router.get("/api/billing/subscription/{user_id}")
async def get_subscription(user_id: str):
    """
    Fetches the user's active billing tier and resource limits.
    If they haven't bought anything, it safely falls back to the Free 'Starter' tier.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT plan_tier, billing_cycle, status, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            # Default Starter plan for users without a subscription row
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ==========================================
# RAZORPAY CHECKOUT SESSION
# ==========================================

@router.post("/create-razorpay-order")
async def create_razorpay_order(req: CheckoutRequest):
    """
    Step 1 of the Payment Flow: Calculates the correct price based on the selected plan 
    and generates a secure Razorpay Order ID. The frontend uses this Order ID to open 
    the payment modal.
    """
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    # Fixed Pricing Tiers
    if req.plan_tier == "Pro":
        monthly_total = 1900
        # Offer a 20% discount if they commit to an annual billing cycle
        final_amount = (
            (monthly_total * 12) * 0.8
            if req.billing_cycle == "annually"
            else monthly_total
        )
    elif req.plan_tier == "Enterprise":
        monthly_total = 9900
        final_amount = (
            (monthly_total * 12) * 0.8
            if req.billing_cycle == "annually"
            else monthly_total
        )
    else:
        # Dynamic Pricing Formula for the "Custom" slider tier
        # Users pay per specific unit of resource they need
        base_price = 800
        workspaces_price = req.workspaces_limit * 500
        agents_price = req.agents_limit * 400
        agent_msg_price = (req.agent_messages_limit / 1000.0) * 160
        storage_price = (req.storage_mb_limit / 100.0) * 50
        chatbots_price = req.chatbots_limit * 800
        chatbot_msg_price = (req.chatbot_messages_limit / 1000.0) * 200

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
            if req.billing_cycle == "annually"
            else monthly_total
        )

    # Razorpay API expects amounts in the smallest currency unit (paise instead of Rupees)
    amount = int(final_amount * 100) 

    try:
        order = razorpay_client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "receipt": f"receipt_{req.user_id[:8]}",
                "notes": {
                    "user_id": req.user_id,
                    "plan_tier": req.plan_tier,
                    "billing_cycle": req.billing_cycle,
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


# ==========================================
# PAYMENT VERIFICATION
# ==========================================

@router.post("/razorpay/verify")
async def verify_razorpay_payment(req: RazorpayVerifyRequest):
    """
    Step 2 of the Payment Flow: Once the frontend completes payment, it sends the 
    cryptographic signature here. We verify it to ensure the user didn't just spoof 
    a success message, then we provision their upgraded account limits in the database.
    """
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")

    try:
        # Verify Signature - This throws SignatureVerificationError if someone tries to hack the payment
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": req.razorpay_order_id,
                "razorpay_payment_id": req.razorpay_payment_id,
                "razorpay_signature": req.razorpay_signature,
            }
        )

        # If no exception thrown, signature is valid. Grant the resources!
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Pack their new capacity limits into a JSONB column
            limits_json = json.dumps(
                {
                    "workspaces": req.workspaces_limit,
                    "agents": req.agents_limit,
                    "agent_messages": req.agent_messages_limit,
                    "storage_mb": req.storage_mb_limit,
                    "chatbots": req.chatbots_limit,
                    "chatbot_messages": req.chatbot_messages_limit,
                }
            )

            # Insert or update their subscription row using ON CONFLICT DO UPDATE (Upsert)
            cursor.execute(
                """
                INSERT INTO user_subscriptions (user_id, plan_tier, billing_cycle, status, limits, updated_at)
                VALUES (%s, %s, %s, 'active', %s::jsonb, now())
                ON CONFLICT (user_id) DO UPDATE 
                SET plan_tier = EXCLUDED.plan_tier,
                    billing_cycle = EXCLUDED.billing_cycle,
                    status = 'active',
                    limits = EXCLUDED.limits,
                    updated_at = now();
            """,
                (req.user_id, req.plan_tier, req.billing_cycle, limits_json),
            )
            conn.commit()
            logger.info(f"Subscription updated for user {req.user_id}")
        except Exception as e:
            logger.exception("Failed to update subscription in DB")
            raise HTTPException(
                status_code=500, detail="Database error during subscription update"
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return {"status": "success"}
    except razorpay.errors.SignatureVerificationError:
        # Caught a hacker trying to bypass payment!
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
