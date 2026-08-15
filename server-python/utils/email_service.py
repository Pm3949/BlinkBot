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

from utils.logo_resolver import get_logo_path
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
          <td style="padding: 10px 0; color: #757d91; font-size: 13px; border-bottom: 1px solid #e0e3e9;">Credits Added</td>
          <td style="padding: 10px 0; color: #18181b; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #e0e3e9;">+{credits:,} Credits</td>
        </tr>"""
    if discount and float(discount) > 0:
        extras_html += f"""
        <tr>
          <td style="padding: 10px 0; color: #757d91; font-size: 13px; border-bottom: 1px solid #e0e3e9;">Discount Applied</td>
          <td style="padding: 10px 0; color: #159d47; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #e0e3e9;">{discount}% Off</td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background-color: #f4f5f8; font-family: 'Inter', Arial, sans-serif;">
  <div style="max-width: 560px; margin: 40px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e5e7ec; box-shadow: 0 2px 10px rgba(9, 39, 195, 0.05);">

    <!-- Top accent bar -->
    <div style="height: 4px; background-color: #0927c3;"></div>

    <!-- Header -->
    <div style="background-color: #ffffff; padding: 32px 40px 24px; text-align: center;">
      <div style="display: inline-flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 4px;">
        <img src="cid:logo_image" width="32" height="32" style="vertical-align: middle; border-radius: 6px;" alt="BlinkBot Logo" />
        <span style="color: #14152b; font-size: 22px; font-weight: 800; letter-spacing: -0.4px; font-family: 'Inter', Arial, sans-serif; vertical-align: middle; line-height: 32px;">BlinkBot</span>
      </div>
      <p style="margin: 10px 0 0; color: #757d91; font-size: 13px; font-weight: 500;">
        Payment receipt for your records
      </p>
    </div>

    <div style="padding: 0 40px;">
      <hr style="border: none; border-top: 1px solid #eceef2; margin: 8px 0 28px;">
    </div>

    <!-- Body -->
    <div style="padding: 0 40px 36px;">

      <!-- Status row -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <p style="color: #14152b; font-size: 15px; line-height: 1.6; margin: 0; max-width: 340px;">
          Your payment has been successfully processed. The invoice PDF is attached to this email.
        </p>
      </div>
      <div style="margin-bottom: 24px;">
        <span style="display: inline-block; background-color: #eef1ff; color: #0927c3; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; padding: 6px 14px; border-radius: 6px; border: 1px solid #d6dcff;">
          ● {status}
        </span>
      </div>

      <!-- Invoice Details Card -->
      <div style="background-color: #f8f9fc; border-radius: 12px; padding: 4px 24px; border: 1px solid #e5e7ec; margin-bottom: 28px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 14px 0; color: #757d91; font-size: 13px; border-bottom: 1px solid #e5e7ec;">Invoice Number</td>
            <td style="padding: 14px 0; color: #14152b; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #e5e7ec; font-family: 'SFMono-Regular', Menlo, monospace;">{inv_number}</td>
          </tr>
          <tr>
            <td style="padding: 14px 0; color: #757d91; font-size: 13px; border-bottom: 1px solid #e5e7ec;">Date</td>
            <td style="padding: 14px 0; color: #14152b; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #e5e7ec;">{date_str}</td>
          </tr>
          <tr>
            <td style="padding: 14px 0; color: #757d91; font-size: 13px; border-bottom: 1px solid #e5e7ec;">Description</td>
            <td style="padding: 14px 0; color: #14152b; font-size: 13px; font-weight: 600; text-align: right; border-bottom: 1px solid #e5e7ec;">{description}</td>
          </tr>
          {extras_html}
          <tr>
            <td style="padding: 18px 0 12px; color: #14152b; font-size: 14px; font-weight: 700;">Total Paid</td>
            <td style="padding: 18px 0 12px; color: #0927c3; font-size: 22px; font-weight: 800; text-align: right;">&#8377;{amount_inr:.2f}</td>
          </tr>
        </table>
      </div>

      <!-- CTA -->
      <div style="text-align: center; margin-bottom: 4px;">
        <a href="https://www.blinkbot.in/billing" style="display: inline-block; background-color: #0927c3; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; padding: 13px 34px; border-radius: 10px; letter-spacing: 0.2px;">
          View Invoice History →
        </a>
      </div>
      <p style="text-align: center; margin: 14px 0 0; color: #a3a9b8; font-size: 12px;">
        Powered by BlinkBot Billing
      </p>
    </div>

    <!-- Footer -->
    <div style="background-color: #f8f9fc; border-top: 1px solid #eceef2; padding: 24px 40px;">
      <p style="color: #757d91; font-size: 12px; text-align: center; margin: 0; line-height: 1.7;">
        Questions about this invoice? Contact us at
        <a href="mailto:{SUPPORT_EMAIL}" style="color: #0927c3; text-decoration: none; font-weight: 600;">{SUPPORT_EMAIL}</a><br>
        BlinkBot · Bengaluru, Karnataka, India<br>
        <span style="color: #a3a9b8;">This is an automatically generated email. Please do not reply to this address.</span>
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

    # Inline Logo Image attachment
    logo_path = get_logo_path()
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                img_data = f.read()
            img_part = MIMEBase("image", "png")
            img_part.set_payload(img_data)
            encoders.encode_base64(img_part)
            img_part.add_header("Content-ID", "<logo_image>")
            img_part.add_header("Content-Disposition", 'inline; filename="logo.png"')
            msg.attach(img_part)
        except Exception as logo_err:
            logger.warning(f"Failed to attach inline logo to invoice email: {logo_err}")

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