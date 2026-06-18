import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from database import get_db_connection
from core.dependencies import rag_engine

logger = logging.getLogger(__name__)

def background_ingestion(
    document_id: int,
    agent_id: str,
    raw_text: str,
    strategy: str,
    embed_model: str,
    file_path: str = None,
):
    """Runs chunking + embedding in the background and updates document status."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.info("⚙️ Background task started for doc id: %s", document_id)

        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the uploaded content")

        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        for text, vector in zip(chunks, vectors):
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, text, str(vector)),
            )

        cursor.execute(
            "UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,)
        )
        conn.commit()
        logger.info("✅ Background task completed for doc id: %s", document_id)

    except Exception:
        logger.exception("Background ingestion failed for doc id %s", document_id)
        if conn and cursor:
            try:
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
        # if file_path and os.path.exists(file_path):
        #     os.remove(file_path)


def send_invite_email(
    to_email: str, workspace_name: str, invited_by: str, signup_url: str
):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning("⚠️ SMTP settings are missing. Email not sent.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Invitation to join '{workspace_name}' workspace on RagMate"
        msg["From"] = f"RagMate Team <{smtp_user}>"
        msg["To"] = to_email

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <h2 style="color: #4f46e5; margin-bottom: 20px;">You are invited!</h2>
              <p>Hello,</p>
              <p><strong>{invited_by}</strong> has invited you to collaborate in the workspace <strong>{workspace_name}</strong> on RagMate.</p>
              <p>To accept this invitation and access the workspace, click the button below to sign up or log in:</p>
              <p style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" style="background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Accept Invitation</a>
              </p>
              <p style="font-size: 12px; color: #718096; margin-top: 30px;">
                If you did not expect this invitation, you can safely ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        logger.info(f"📧 Invite email sent successfully to {to_email}")
        return True
    except Exception:
        logger.exception(f"❌ Failed to send email to {to_email}")
        return False


def get_user_limits(user_id: str, cursor) -> dict:
    cursor.execute(
        "SELECT plan_tier, limits FROM user_subscriptions WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
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
