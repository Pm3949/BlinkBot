
"""
Utility Functions & Background Tasks.
Responsibility: Contains helper functions used across various routes, including 
background document ingestion, SMTP email sending, and subscription limit checks.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from database import get_db_connection
from core.dependencies import rag_engine
from utils.logger import get_department_logger

_logger = get_department_logger("system")

# ==========================================
# DOCUMENT INGESTION
# ==========================================

def background_ingestion(
    document_id: int,
    agent_id: str,
    raw_text: str,
    strategy: str,
    embed_model: str,
    file_path: str = None,
):
    """
    Runs chunking and vector embedding as a background task.
    Why? Embedding a large document can take several seconds to minutes. If we did this 
    synchronously in the HTTP request, the frontend would hang and eventually timeout. 
    By running it in the background, we can immediately return a "Processing" status to the user.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        _logger.info("⚙️ Background task started for doc id: %s", document_id)

        # Route to the correct chunking algorithm based on user/system preference
        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the uploaded content")

        # Convert chunks into mathematical vectors
        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        from core.security import encrypt_key
        # Save chunks and vectors to database
        for text, vector in zip(chunks, vectors):
            # Security: Encrypt the actual text chunks so that even if the database is compromised, 
            # the raw document data is unreadable without the encryption key.
            encrypted_chunk = encrypt_key(text)
            cursor.execute(
                # ::vector type casting is specific to the pgvector PostgreSQL extension
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, encrypted_chunk, str(vector)),
            )

        # Mark as completed so the frontend knows it's ready to be queried
        cursor.execute(
            "UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,)
        )
        conn.commit()
        _logger.info("✅ Background task completed for doc id: %s", document_id)

    except Exception:
        _logger.exception("Background ingestion failed for doc id %s", document_id)
        if conn and cursor:
            try:
                # If anything fails, mark the document as failed so the user isn't stuck waiting forever
                cursor.execute(
                    "UPDATE documents SET status = 'failed' WHERE id = %s",
                    (document_id,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        # Cleanup code for physical files could go here (currently commented out)
        # if file_path and os.path.exists(file_path):
        #     os.remove(file_path)

# ==========================================
# EMAIL UTILITIES
# ==========================================

def send_invite_email(
    to_email: str, workspace_name: str, invited_by: str, signup_url: str
):
    """
    Sends an HTML formatted invitation email using SMTP.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "noreply@blinkbot.in")

    if not all([smtp_host, smtp_user, smtp_pass]):
        _logger.warning("⚠️ SMTP settings are missing. Email not sent.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Invitation to join '{workspace_name}' workspace on BlinkBot"
        msg["From"] = f"BlinkBot Team <{sender_email}>"
        msg["To"] = to_email

        # Modern inline-styled HTML matching the orange brand theme
        html_content = f"""
        <html>
          <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f4f4f5; padding: 40px 0; margin: 0;">
            <div style="margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02); text-align: center; max-width: 450px;">
              <h1 style="color: #ff4d00; font-size: 28px; margin-bottom: 5px; font-weight: 800; letter-spacing: -0.5px; margin-top: 0;">BlinkBot</h1>
              <h2 style="color: #09090b; font-size: 20px; font-weight: 600; margin-bottom: 25px;">You are invited!</h2>
              
              <div style="text-align: left; background-color: #fafafa; border: 1px solid #e4e4e7; border-radius: 16px; padding: 20px; margin-bottom: 30px;">
                <p style="color: #27272a; font-size: 15px; line-height: 1.6; margin: 0 0 10px 0;">Hello,</p>
                <p style="color: #52525b; font-size: 15px; line-height: 1.6; margin: 0;">
                  <strong>{invited_by}</strong> has invited you to collaborate in the workspace <strong>{workspace_name}</strong> on BlinkBot.
                </p>
              </div>

              <p style="color: #52525b; font-size: 14px; margin-bottom: 30px; line-height: 1.5;">
                To accept this invitation and access the workspace, click the button below:
              </p>

              <div style="margin-bottom: 35px;">
                <a href="{signup_url}" style="background-color: #ff4d00; color: white; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block; font-size: 15px; box-shadow: 0 4px 12px rgba(255, 77, 0, 0.2);">Accept Invitation</a>
              </div>

              <p style="color: #a1a1aa; font-size: 12px; margin: 0; line-height: 1.5;">
                If you did not expect this invitation, you can safely ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            # Start TLS encryption for the SMTP connection
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, to_email, msg.as_string())

        _logger.info(f"📧 Invite email sent successfully to {to_email}")
        return True
    except Exception:
        _logger.exception(f"❌ Failed to send email to {to_email}")
        return False

# ==========================================
# BILLING UTILITIES
# ==========================================

def get_user_limits(user_id: str, cursor) -> dict:
    """
    Fetches the usage limits for a user based on their current subscription plan.
    Data Flow: Query `user_subscriptions` table -> Return hardcoded limits for standard plans, 
    or dynamically parse the JSON `limits` column for custom enterprise deals.
    """
    cursor.execute(
        "SELECT plan_tier, limits FROM user_subscriptions WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    
    # Fallback limits if no subscription is found (e.g., Free Tier)
    default_limits = {
        "agents": 1,
        "agent_messages": 1000,
        "storage_mb": 100,
        "chatbots": 0,
        "chatbot_messages": 0,
    }
    if not row:
        return default_limits

    plan_tier, limits = row
    if plan_tier == "Pro":
        return {
            "agents": 5,
            "agent_messages": 10000,
            "storage_mb": 500,
            "chatbots": 2,
            "chatbot_messages": 5000,
        }
    elif plan_tier == "Enterprise":
        return {
            "agents": 20,
            "agent_messages": 100000,
            "storage_mb": 5000,
            "chatbots": 10,
            "chatbot_messages": 50000,
        }
    elif plan_tier == "Custom" and limits:
        # For completely bespoke plans, read the JSON overrides from the database
        return limits
    else:
        return default_limits

async def get_user_limits_by_id(user_id: str) -> dict:
    from database import get_db_cursor_async
    from fastapi.concurrency import run_in_threadpool
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT plan_tier, limits FROM user_subscriptions WHERE user_id = %s",
            (user_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        
    default_limits = {
        "agents": 1,
        "agent_messages": 1000,
        "storage_mb": 100,
        "chatbots": 0,
        "chatbot_messages": 0,
    }
    if not row:
        return default_limits

    plan_tier, limits = row
    if plan_tier == "Pro":
        return {
            "agents": 5,
            "agent_messages": 10000,
            "storage_mb": 500,
            "chatbots": 2,
            "chatbot_messages": 5000,
        }
    elif plan_tier == "Enterprise":
        return {
            "agents": 20,
            "agent_messages": 100000,
            "storage_mb": 5000,
            "chatbots": 10,
            "chatbot_messages": 50000,
        }
    elif plan_tier == "Custom" and limits:
        return limits
    else:
        return default_limits
