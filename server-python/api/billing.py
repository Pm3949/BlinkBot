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
import io
import fitz
from utils.logger import get_department_logger
from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import StreamingResponse
from schemas import CheckoutRequest, RazorpayVerifyRequest
from core.auth import get_current_user

# Import the payment and subscription handlers.
from handlers.billing_handler import (
    handle_get_subscription,
    handle_create_razorpay_order,
    handle_verify_razorpay_payment,
    handle_create_wallet_recharge_order,
    handle_verify_wallet_recharge_payment
)

# Initialize standard module-level logger.
logger = get_department_logger("system")

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
        current_user.get("email", ""),
        req.plan_tier,
        req.billing_cycle,
        req.workspaces_limit,
        req.agents_limit,
        req.agent_messages_limit,
        req.storage_mb_limit,
        req.chatbots_limit,
        req.chatbot_messages_limit
    )


# ==========================================
# WALLET AND CREDIT ENDPOINTS
# ==========================================

from pydantic import BaseModel

class RechargeRequest(BaseModel):
    credits: int

class RechargeSettingsRequest(BaseModel):
    enabled: bool
    threshold: float
    amount_usd: float


@router.get("/api/billing/wallet")
async def get_wallet_info(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the wallet configuration, credit balance, and transaction history.
    """
    user_id = current_user["sub"]
    from db import billing_repository
    
    wallet = await billing_repository.get_wallet_details(user_id)
    history = await billing_repository.get_credit_transactions(user_id, limit=50)
    
    return {
        "status": "success",
        "wallet": wallet,
        "history": history
    }


class WalletVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    credits: int


@router.post("/api/billing/wallet/recharge/order")
async def create_wallet_recharge_order(req: RechargeRequest, current_user: dict = Depends(get_current_user)):
    """
    Creates a Razorpay Order ID for wallet recharge.
    """
    user_id = current_user["sub"]
    return await handle_create_wallet_recharge_order(user_id, req.credits)


@router.post("/api/billing/wallet/recharge/verify")
async def verify_wallet_recharge_payment(req: WalletVerifyRequest, current_user: dict = Depends(get_current_user)):
    """
    Verifies Razorpay payment signature and credits the user's wallet.
    """
    user_id = current_user["sub"]
    user_email = current_user.get("email", "")
    return await handle_verify_wallet_recharge_payment(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature,
        user_id=user_id,
        user_email=user_email,
        credits=req.credits
    )


@router.post("/api/billing/wallet/settings")
async def update_recharge_settings(req: RechargeSettingsRequest, current_user: dict = Depends(get_current_user)):
    """
    Saves automatic refill thresholds and rules.
    """
    user_id = current_user["sub"]
    from db import billing_repository
    
    await billing_repository.update_wallet_recharge_settings(
        user_id=user_id,
        enabled=req.enabled,
        threshold=req.threshold,
        amount_usd=req.amount_usd
    )
    
    return {
        "status": "success",
        "message": "Wallet recharge settings updated successfully."
    }


def generate_invoice_pdf_data(invoice: dict) -> bytes:
    """
    Generates a branded BlinkBot PDF invoice (dark theme, A4).
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # -- Color palette (matches BlinkBot UI) --------------------------------
    bg_dark     = (0.051, 0.055, 0.078)   # #0D0E14 page background
    header_dark = (0.071, 0.063, 0.196)   # #12103200 header block (deep indigo)
    primary     = (0.506, 0.435, 0.941)   # #815EF0 indigo primary
    white       = (1.0, 1.0, 1.0)
    muted       = (0.631, 0.631, 0.651)   # #A1A1A6
    card_bg     = (0.094, 0.094, 0.110)   # #18181B card
    border      = (0.153, 0.153, 0.165)   # #27272A border
    green       = (0.271, 0.761, 0.498)   # #45C27F paid green

    # -- Full page dark background ------------------------------------------
    page.draw_rect(fitz.Rect(0, 0, 595, 842), color=bg_dark, fill=bg_dark)

    # -- Header block (indigo gradient effect via rect) ---------------------
    page.draw_rect(fitz.Rect(0, 0, 595, 130), color=header_dark, fill=header_dark)

    # Brand name
    page.insert_text(fitz.Point(40, 60), "⚡ BlinkBot", fontsize=26, color=white)
    page.insert_text(fitz.Point(40, 82), "TAX INVOICE / RECEIPT", fontsize=9, color=primary)

    # Invoice meta (top-right)
    page.insert_text(fitz.Point(390, 48), f"Invoice #:", fontsize=8, color=muted)
    page.insert_text(fitz.Point(390, 60), invoice["invoice_number"], fontsize=9, color=white)
    page.insert_text(fitz.Point(390, 78), f"Date: {str(invoice['created_at'])[:10]}", fontsize=9, color=muted)
    status_color = green if invoice["status"] == "Paid" else (1.0, 0.7, 0.0)
    page.insert_text(fitz.Point(390, 96), f"Status: {invoice['status'].upper()}", fontsize=9, color=status_color)

    # -- Billed By --------------------------------------------------------
    page.insert_text(fitz.Point(40, 165), "Billed By", fontsize=9, color=muted)
    page.insert_text(fitz.Point(40, 183), "BlinkBot Technologies Private Limited", fontsize=11, color=white)
    page.insert_text(fitz.Point(40, 198), "Bengaluru, Karnataka, India", fontsize=9, color=muted)
    page.insert_text(fitz.Point(40, 212), "support@blinkbot.in  |  www.blinkbot.in", fontsize=9, color=muted)

    # -- Billed To -------------------------------------------------------
    page.insert_text(fitz.Point(350, 165), "Billed To", fontsize=9, color=muted)
    user_id_str = str(invoice.get("user_id", "—"))
    # Show only first 36 chars (UUID length) to stay in column
    page.insert_text(fitz.Point(350, 183), user_id_str[:36], fontsize=8, color=white)

    # -- Divider line ----------------------------------------------------
    page.draw_line(fitz.Point(40, 240), fitz.Point(555, 240), color=border, width=0.8)

    # -- Line-items card background --------------------------------------
    page.draw_rect(fitz.Rect(32, 252), color=card_bg, fill=card_bg, radius=8) if False else None
    # Draw card manually (fitz doesn't support border-radius easily)
    page.draw_rect(fitz.Rect(32, 252, 563, 450), color=border, fill=card_bg)

    # Table header
    page.insert_text(fitz.Point(48, 276), "Description", fontsize=9, color=muted)
    page.insert_text(fitz.Point(460, 276), "Amount", fontsize=9, color=muted)
    page.draw_line(fitz.Point(40, 285), fitz.Point(555, 285), color=border, width=0.6)

    # Main line item
    page.insert_text(fitz.Point(48, 308), invoice["description"], fontsize=11, color=white)
    page.insert_text(fitz.Point(448, 308), f"INR {invoice['amount_inr']:.2f}", fontsize=11, color=white)

    # -- Sub-items breakdown ---------------------------------------------
    meta = invoice.get("invoice_metadata", {}) or {}
    y = 332
    if meta.get("credits"):
        page.insert_text(fitz.Point(48, y), f"Credits Loaded: +{int(meta['credits']):,}", fontsize=9, color=muted)
        y += 18
    if meta.get("base_inr"):
        page.insert_text(fitz.Point(48, y), f"Base Amount: INR {float(meta['base_inr']):.2f}", fontsize=9, color=muted)
        y += 18
    if meta.get("discount_percent") and float(meta.get("discount_percent", 0)) > 0:
        page.insert_text(
            fitz.Point(48, y),
            f"Bulk Discount ({meta['discount_percent']}%): -INR {float(meta.get('discount_amount', 0)):.2f}",
            fontsize=9, color=green
        )
        y += 18
    # Razorpay payment ID if present
    if meta.get("razorpay_payment_id"):
        page.insert_text(fitz.Point(48, y), f"Transaction Ref: {meta['razorpay_payment_id']}", fontsize=8, color=muted)
        y += 18

    # -- Total section ---------------------------------------------------
    page.draw_line(fitz.Point(40, 452), fitz.Point(555, 452), color=border, width=0.8)
    page.insert_text(fitz.Point(330, 478), "Total Paid:", fontsize=13, color=muted)
    page.insert_text(fitz.Point(440, 478), f"INR {invoice['amount_inr']:.2f}", fontsize=16, color=primary)

    # -- Status badge area -----------------------------------------------
    page.draw_rect(fitz.Rect(220, 498, 375, 520), color=(0.082, 0.329, 0.176), fill=(0.082, 0.329, 0.176))
    page.insert_text(fitz.Point(240, 514), f"✓  PAYMENT {invoice['status'].upper()}", fontsize=9, color=green)

    # -- Footer ----------------------------------------------------------
    page.draw_line(fitz.Point(40, 780), fitz.Point(555, 780), color=border, width=0.6)
    page.insert_text(fitz.Point(40, 800), "Thank you for choosing BlinkBot!", fontsize=10, color=muted)
    page.insert_text(fitz.Point(40, 815), "This is an electronically generated invoice. No signature required.", fontsize=8, color=(0.4, 0.4, 0.4))
    page.insert_text(fitz.Point(40, 828), "support@blinkbot.in  ·  www.blinkbot.in", fontsize=8, color=(0.4, 0.4, 0.4))

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


@router.get("/api/billing/invoices")
async def get_invoices(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all past tax invoices / transactions for the user.
    """
    user_id = current_user["sub"]
    from db import billing_repository
    return await billing_repository.get_user_invoices(user_id)


@router.get("/api/billing/invoice/{invoice_id}/download")
async def download_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generates and downloads a custom formatted PDF invoice for the transaction.
    """
    user_id = current_user["sub"]
    from db import billing_repository
    
    invoice = await billing_repository.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Enforce authentication ownership check (unless super admin)
    if invoice["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this invoice")
        
    pdf_bytes = generate_invoice_pdf_data(invoice)
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{invoice['invoice_number']}.pdf"
        }
    )


