"""
================================================================================
EMAIL SERVICE UTILITY (email_service.py)
================================================================================
Provides async-safe invoice email dispatch using Brevo SMTP relay.
Sends branded BlinkBot invoice emails with PDF attachments after every
successful Razorpay payment (subscription or wallet top-up).

Sender:   noreply@blinkbot.in
Support:  support@blinkbot.in
SMTP:     smtp-relay.brevo.com (configured in .env)
================================================================================
"""

import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from utils.logger import get_department_logger

# -- Environment credentials (already loaded in core/dependencies.py scope) ----
import os
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL  = os.getenv("SENDER_EMAIL", "noreply@blinkbot.in")
SUPPORT_EMAIL = os.getenv("NOTIFY_EMAIL", "support@blinkbot.in")

logger = get_department_logger("system")


def _build_invoice_email_html(invoice: dict) -> str:
    """
    Builds a branded BlinkBot HTML email body for an invoice notification.
    Matches the dark, premium BlinkBot aesthetic in email-safe HTML.
    """
    inv_number  = invoice.get("invoice_number", "—")
    description = invoice.get("description", "—")
    amount_inr  = invoice.get("amount_inr", 0)
    status      = invoice.get("status", "Paid")
    date_str    = str(invoice.get("created_at", ""))[:10]
    meta        = invoice.get("invoice_metadata", {}) or {}
    credits     = meta.get("credits", None)
    discount    = meta.get("discount_percent", 0)

    # Build optional extras line
    extras_html = ""
    if credits:
        extras_html += f"""
        <tr>
          <td style="padding: 10px 0; color: #a1a1aa; font-size: 13px; border-bottom: 1px solid #27272a;">Credits Added</td>
          <td style="padding: 10px 0; color: #ffffff; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #27272a;">+{credits:,} Credits</td>
        </tr>"""
    if discount and float(discount) > 0:
        extras_html += f"""
        <tr>
          <td style="padding: 10px 0; color: #a1a1aa; font-size: 13px; border-bottom: 1px solid #27272a;">Discount Applied</td>
          <td style="padding: 10px 0; color: #22c55e; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #27272a;">{discount}% Off</td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: 'Inter', Arial, sans-serif;">
  <div style="max-width: 560px; margin: 40px auto; background-color: #0d0f14; border-radius: 20px; overflow: hidden; border: 1px solid #27272a;">

    <!-- Header -->
    <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 36px 40px; text-align: center;">
      <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">
        ⚡ BlinkBot
      </h1>
      <p style="margin: 8px 0 0; color: #c7d2fe; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">
        Payment Confirmed
      </p>
    </div>

    <!-- Body -->
    <div style="padding: 36px 40px;">
      <p style="color: #e4e4e7; font-size: 15px; line-height: 1.6; margin: 0 0 28px;">
        Your payment has been successfully processed. A copy of your invoice is attached to this email as a PDF.
      </p>

      <!-- Invoice Details Card -->
      <div style="background-color: #18181b; border-radius: 14px; padding: 24px; border: 1px solid #27272a; margin-bottom: 28px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 10px 0; color: #a1a1aa; font-size: 13px; border-bottom: 1px solid #27272a;">Invoice Number</td>
            <td style="padding: 10px 0; color: #ffffff; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #27272a; font-family: monospace;">{inv_number}</td>
          </tr>
          <tr>
            <td style="padding: 10px 0; color: #a1a1aa; font-size: 13px; border-bottom: 1px solid #27272a;">Date</td>
            <td style="padding: 10px 0; color: #ffffff; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #27272a;">{date_str}</td>
          </tr>
          <tr>
            <td style="padding: 10px 0; color: #a1a1aa; font-size: 13px; border-bottom: 1px solid #27272a;">Description</td>
            <td style="padding: 10px 0; color: #ffffff; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #27272a;">{description}</td>
          </tr>
          {extras_html}
          <tr>
            <td style="padding: 14px 0 6px; color: #a1a1aa; font-size: 14px; font-weight: 700;">Total Paid</td>
            <td style="padding: 14px 0 6px; color: #818cf8; font-size: 20px; font-weight: 800; text-align: right;">&#8377;{amount_inr:.2f}</td>
          </tr>
        </table>

        <!-- Status Badge -->
        <div style="text-align: center; margin-top: 16px;">
          <span style="display: inline-block; background-color: #14532d; color: #4ade80; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 5px 16px; border-radius: 100px; border: 1px solid #166534;">
            ✓ {status}
          </span>
        </div>
      </div>

      <!-- CTA -->
      <div style="text-align: center; margin-bottom: 28px;">
        <a href="https://www.blinkbot.in/billing" style="display: inline-block; background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; padding: 14px 32px; border-radius: 12px; letter-spacing: 0.3px;">
          View Invoice History →
        </a>
      </div>

      <!-- Footer -->
      <hr style="border: none; border-top: 1px solid #27272a; margin: 0 0 20px;">
      <p style="color: #71717a; font-size: 12px; text-align: center; margin: 0; line-height: 1.7;">
        Questions? Contact us at
        <a href="mailto:{SUPPORT_EMAIL}" style="color: #818cf8; text-decoration: none;">{SUPPORT_EMAIL}</a><br>
        BlinkBot · Bengaluru, Karnataka, India<br>
        This is an automatically generated email. Please do not reply to this address.
      </p>
    </div>
  </div>
</body>
</html>
"""


def _send_invoice_email_sync(to_email: str, invoice: dict, pdf_bytes: bytes) -> None:
    """
    Synchronous SMTP dispatch of an invoice email with PDF attachment.
    Called in a thread pool via asyncio to stay non-blocking.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping invoice email dispatch.")
        return

    inv_number  = invoice.get("invoice_number", "invoice")
    description = invoice.get("description", "Payment")

    # -- Build message -------------------------------------------------------
    msg = MIMEMultipart("mixed")
    msg["From"]    = f"BlinkBot Billing <{SENDER_EMAIL}>"
    msg["To"]      = to_email
    msg["Subject"] = f"Your BlinkBot Invoice – {inv_number}"
    msg["Reply-To"] = SUPPORT_EMAIL

    # HTML body
    html_body = _build_invoice_email_html(invoice)
    msg.attach(MIMEText(html_body, "html"))

    # PDF attachment
    pdf_part = MIMEBase("application", "pdf")
    pdf_part.set_payload(pdf_bytes)
    encoders.encode_base64(pdf_part)
    pdf_part.add_header(
        "Content-Disposition",
        f'attachment; filename="{inv_number}.pdf"'
    )
    msg.attach(pdf_part)

    # -- Dispatch via Brevo SMTP --------------------------------------------
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info(f"Invoice email dispatched successfully to {to_email} [{inv_number}]")
    except Exception as e:
        logger.error(f"Failed to send invoice email to {to_email}: {e}", exc_info=True)


async def send_invoice_email(to_email: str, invoice: dict, pdf_bytes: bytes) -> None:
    """
    Async-safe wrapper — dispatches invoice email via thread pool so the
    calling coroutine (payment verify handler) is never blocked.

    Parameters:
        to_email  (str):   Recipient email address (from JWT claim).
        invoice   (dict):  Invoice record dict from billing_repository.
        pdf_bytes (bytes): Pre-generated PDF bytes from generate_invoice_pdf_data().
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _send_invoice_email_sync,
        to_email,
        invoice,
        pdf_bytes
    )
