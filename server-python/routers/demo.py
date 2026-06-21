import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["demo"])

class DemoRequest(BaseModel):
    name: str
    email: str
    company: str = ""
    message: str = ""

@router.post("/api/demo-request")
async def submit_demo_request(req: DemoRequest):
    """Store demo request in DB and send email notification."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS demo_requests (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT DEFAULT '',
                message TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Ensure our new columns exist for the calendar functionality
        cur.execute("ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_date TEXT")
        cur.execute("ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_time TEXT")
        cur.execute("ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS meeting_link TEXT")


        # Insert the request
        cur.execute(
            """
            INSERT INTO demo_requests (name, email, company, message)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (req.name, req.email, req.company, req.message)
        )
        row = cur.fetchone()
        conn.commit()

        # Send email notification
        try:
            _send_demo_email(req, row[0], row[1])
        except Exception as email_err:
            logger.warning(f"Demo email notification failed (request still saved): {email_err}")

        return {"success": True, "message": "Demo request submitted successfully!", "id": row[0]}

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Demo request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


def _send_demo_email(req: DemoRequest, request_id: int, created_at):
    """Send email notification about new demo request."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    notify_email = os.getenv("NOTIFY_EMAIL") or "techmate.ed@gmail.com"
 
    if not smtp_user or not smtp_pass or not notify_email:
        logger.warning("SMTP or destination email not configured, skipping demo email notification")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 New Demo Request from {req.name} — BlinkBot"
    msg["From"] = f"BlinkBot <{smtp_user}>"
    msg["To"] = notify_email

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #f9fafb; border-radius: 16px;">
        <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 24px 32px; border-radius: 12px; margin-bottom: 24px;">
            <h1 style="color: white; margin: 0; font-size: 22px;">🚀 New Demo Request</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Someone wants to see BlinkBot in action!</p>
        </div>
        
        <div style="background: white; padding: 24px; border-radius: 12px; border: 1px solid #e5e7eb;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151; width: 120px;">Name</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;">{req.name}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151;">Email</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;"><a href="mailto:{req.email}" style="color: #6366f1;">{req.email}</a></td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151;">Company</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;">{req.company or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; font-weight: 600; color: #374151; vertical-align: top;">Message</td>
                    <td style="padding: 12px 0; color: #6b7280;">{req.message or 'No message provided'}</td>
                </tr>
            </table>
        </div>
        
        <p style="text-align: center; color: #9ca3af; font-size: 12px; margin-top: 24px;">
            Request #{request_id} • {created_at.strftime('%B %d, %Y at %I:%M %p') if created_at else 'Just now'}
        </p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, notify_email, msg.as_string())

    logger.info(f"Demo request email sent to {notify_email}")

# --- Admin Endpoints for Demo Requests ---

from routers.admin import check_super_admin, check_action_password

@router.get("/admin/demo-requests")
async def get_admin_demo_requests(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute(
            """
            SELECT id, name, email, company, message, status, created_at, scheduled_date, scheduled_time, meeting_link
            FROM demo_requests
            ORDER BY created_at DESC
            """
        )
        requests = []
        for r in cursor.fetchall():
            requests.append({
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "company": r[3],
                "message": r[4],
                "status": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "scheduled_date": r[7],
                "scheduled_time": r[8],
                "meeting_link": r[9],
            })
        return {"requests": requests}
    except Exception as e:
        logger.exception("Failed to fetch admin demo requests")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class UpdateStatusRequest(BaseModel):
    status: str
    admin_user_id: str
    admin_action_password: str

@router.patch("/admin/demo-requests/{request_id}/status")
async def update_demo_request_status(request_id: int, req: UpdateStatusRequest):
    conn = None
    cursor = None
    try:
        check_action_password(req.admin_action_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(req.admin_user_id, cursor)

        # Update status
        cursor.execute(
            "UPDATE demo_requests SET status = %s WHERE id = %s RETURNING name, email",
            (req.status, request_id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]
        conn.commit()

        # If completed, send feedback email
        if req.status == 'completed':
            try:
                _send_feedback_email(name, email)
            except Exception as email_err:
                logger.warning(f"Failed to send feedback email: {email_err}")

        return {"message": "Status updated successfully", "status": req.status}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Failed to update demo request status")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class ScheduleMeetingRequest(BaseModel):
    date: str
    time: str
    meeting_link: str
    admin_user_id: str
    admin_action_password: str

@router.post("/admin/demo-requests/{request_id}/schedule")
async def schedule_demo_meeting(request_id: int, req: ScheduleMeetingRequest):
    conn = None
    cursor = None
    try:
        check_action_password(req.admin_action_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(req.admin_user_id, cursor)

        # Get request info
        cursor.execute("SELECT name, email FROM demo_requests WHERE id = %s", (request_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]
        
        # Use manually provided meet link
        meet_link = req.meeting_link

        # Update status to processing and save scheduling details
        cursor.execute(
            """
            UPDATE demo_requests 
            SET status = 'processing', scheduled_date = %s, scheduled_time = %s, meeting_link = %s 
            WHERE id = %s
            """, 
            (req.date, req.time, meet_link, request_id)
        )
        conn.commit()

        try:
            _send_meeting_invite_email(name, email, req.date, req.time, meet_link)
        except Exception as email_err:
            logger.warning(f"Failed to send meeting invite email: {email_err}")

        return {"message": "Meeting scheduled and email sent", "link": meet_link}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Failed to schedule demo meeting")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.get("/admin/demo-requests/scheduled")
async def get_scheduled_demo_requests(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        # Fetch only requests that have a scheduled date
        cursor.execute(
            """
            SELECT id, name, email, company, status, scheduled_date, scheduled_time, meeting_link
            FROM demo_requests
            WHERE scheduled_date IS NOT NULL
            ORDER BY scheduled_date ASC
            """
        )
        requests = []
        for r in cursor.fetchall():
            requests.append({
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "company": r[3],
                "status": r[4],
                "scheduled_date": r[5],
                "scheduled_time": r[6],
                "meeting_link": r[7],
            })
        return {"requests": requests}
    except Exception as e:
        logger.exception("Failed to fetch scheduled demo requests")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def _send_meeting_invite_email(name: str, email: str, date: str, time: str, link: str):
    """Send meeting invitation email to user."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
 
    if not smtp_user or not smtp_pass:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🚀 BlinkBot Demo - Meeting Scheduled"
    msg["From"] = f"BlinkBot <{smtp_user}>"
    msg["To"] = email

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;">
        <h2 style="color: #111827; margin-top: 0;">Hi {name},</h2>
        <p style="color: #4b5563; line-height: 1.6;">
            We have reviewed your request and would love to show you a demo of BlinkBot! We have scheduled a meeting with you.
        </p>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 24px 0;">
            <p style="margin: 0 0 12px 0; color: #374151;"><strong>Date:</strong> {date}</p>
            <p style="margin: 0 0 12px 0; color: #374151;"><strong>Time:</strong> {time}</p>
            <p style="margin: 0; color: #374151;"><strong>Meeting Link:</strong> <a href="{link}" style="color: #6366f1;">{link}</a></p>
        </div>
        <p style="color: #4b5563; line-height: 1.6;">
            Looking forward to speaking with you!<br/><br/>
            Best regards,<br/>
            The BlinkBot Team
        </p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, email, msg.as_string())

def _send_feedback_email(name: str, email: str):
    """Send feedback email to user."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
 
    if not smtp_user or not smtp_pass:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "How was your BlinkBot demo?"
    msg["From"] = f"BlinkBot <{smtp_user}>"
    msg["To"] = email

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;">
        <h2 style="color: #111827; margin-top: 0;">Hi {name},</h2>
        <p style="color: #4b5563; line-height: 1.6;">
            Thank you for meeting with us! We hope you enjoyed the demo and learned how BlinkBot can help your team.
        </p>
        <p style="color: #4b5563; line-height: 1.6;">
            We are always looking to improve, and we would love to hear your thoughts. How would you rate your experience? 
            Please reply to this email with any feedback you might have.
        </p>
        <p style="color: #4b5563; line-height: 1.6;">
            Best regards,<br/>
            The BlinkBot Team
        </p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, email, msg.as_string())

