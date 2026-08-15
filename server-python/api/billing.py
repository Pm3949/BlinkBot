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
    return await handle_verify_wallet_recharge_payment(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature,
        user_id=user_id,
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
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4 size
    
    primary_color = (0.31, 0.27, 0.90) # Indigo 600 tint
    text_color = (0.1, 0.1, 0.1)
    muted_color = (0.4, 0.4, 0.4)
    
    # Header Accent Rect
    page.draw_rect(fitz.Rect(0, 0, 595, 120), color=primary_color, fill=primary_color)
    
    # Titles
    page.insert_text(fitz.Point(40, 70), "RAGMate", fontsize=24, color=(1, 1, 1))
    page.insert_text(fitz.Point(40, 95), "TAX INVOICE / TRANSACTION RECEIPT", fontsize=10, color=(0.8, 0.8, 1))
    
    # Invoice Metadata
    page.insert_text(fitz.Point(380, 50), f"Invoice #: {invoice['invoice_number']}", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(380, 70), f"Date: {invoice['created_at'][:10]}", fontsize=10, color=(1, 1, 1))
    page.insert_text(fitz.Point(380, 90), f"Status: {invoice['status'].upper()}", fontsize=10, color=(0.2, 1, 0.2) if invoice['status'] == 'Paid' else (1, 0.2, 0.2))
    
    # Business Info
    page.insert_text(fitz.Point(40, 160), "Billed By:", fontsize=11, color=muted_color)
    page.insert_text(fitz.Point(40, 180), "RAGMate Technologies Private Limited", fontsize=11, color=text_color)
    page.insert_text(fitz.Point(40, 195), "Bengaluru, Karnataka, India", fontsize=9, color=muted_color)
    page.insert_text(fitz.Point(40, 210), "Email: support@ragmate.ai", fontsize=9, color=muted_color)
    
    # Customer Details
    page.insert_text(fitz.Point(380, 160), "Billed To (User ID):", fontsize=11, color=muted_color)
    page.insert_text(fitz.Point(380, 180), str(invoice['user_id']), fontsize=9, color=text_color)
    
    # Table Header Line
    page.draw_line(fitz.Point(40, 260), fitz.Point(555, 260), color=(0.8, 0.8, 0.8), width=1)
    page.insert_text(fitz.Point(45, 275), "Description", fontsize=10, color=muted_color)
    page.insert_text(fitz.Point(450, 275), "Amount", fontsize=10, color=muted_color)
    page.draw_line(fitz.Point(40, 290), fitz.Point(555, 290), color=(0.8, 0.8, 0.8), width=1)
    
    # Table Content
    page.insert_text(fitz.Point(45, 315), invoice['description'], fontsize=11, color=text_color)
    page.insert_text(fitz.Point(450, 315), f"INR {invoice['amount_inr']:.2f}", fontsize=11, color=text_color)
    
    # Sub-item breakdown
    meta = invoice.get('invoice_metadata', {})
    y_offset = 340
    if meta:
        if 'base_inr' in meta:
            page.insert_text(fitz.Point(45, y_offset), f"Base Amount: INR {meta['base_inr']:.2f}", fontsize=9, color=muted_color)
            y_offset += 20
        if 'discount_amount' in meta and float(meta.get('discount_amount', 0)) > 0:
            page.insert_text(fitz.Point(45, y_offset), f"Discount Applied ({meta.get('discount_percent', 0)}%): -INR {meta['discount_amount']:.2f}", fontsize=9, color=(0.2, 0.8, 0.2))
            y_offset += 20
            
    page.draw_line(fitz.Point(40, y_offset + 10), fitz.Point(555, y_offset + 10), color=(0.8, 0.8, 0.8), width=1)
    
    page.insert_text(fitz.Point(340, y_offset + 30), "Total Paid:", fontsize=12, color=text_color)
    page.insert_text(fitz.Point(450, y_offset + 30), f"INR {invoice['amount_inr']:.2f}", fontsize=14, color=primary_color)
    
    # Footer Notice
    page.draw_line(fitz.Point(40, 750), fitz.Point(555, 750), color=(0.9, 0.9, 0.9), width=1)
    page.insert_text(fitz.Point(40, 770), "Thank you for using RAGMate!", fontsize=10, color=muted_color)
    page.insert_text(fitz.Point(40, 785), "This is an electronically generated receipt. No signature is required.", fontsize=8, color=muted_color)
    
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


