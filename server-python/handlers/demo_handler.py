import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from handlers.admin_handler import check_super_admin, check_action_password
from db import demo_repository

logger = logging.getLogger(__name__)

def _send_demo_email(req: dict, request_id: int, created_at):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    notify_email = os.getenv("NOTIFY_EMAIL") or "techmate.ed@gmail.com"
 
    if not smtp_user or not smtp_pass or not notify_email:
        logger.warning("SMTP or destination email not configured, skipping demo email notification")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 New Demo Request from {req.get('name')} — BlinkBot"
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
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;">{req.get('name')}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151;">Email</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;"><a href="mailto:{req.get('email')}" style="color: #6366f1;">{req.get('email')}</a></td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; font-weight: 600; color: #374151;">Company</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #6b7280;">{req.get('company') or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; font-weight: 600; color: #374151; vertical-align: top;">Message</td>
                    <td style="padding: 12px 0; color: #6b7280;">{req.get('message') or 'No message provided'}</td>
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

def _send_meeting_invite_email(name: str, email: str, date: str, time: str, link: str):
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


async def handle_submit_demo_request(req: dict):
    try:
        row = await demo_repository.submit_demo_request(
            req.get('name'), req.get('email'), req.get('company'), req.get('message')
        )
        try:
            _send_demo_email(req, row[0], row[1])
        except Exception as email_err:
            logger.warning(f"Demo email notification failed: {email_err}")

        return {"success": True, "message": "Demo request submitted successfully!", "id": row[0]}
    except Exception as e:
        logger.error(f"Demo request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_demo_requests(user_id: str):
    try:
        await check_super_admin(user_id)
        rows = await demo_repository.get_admin_demo_requests()
        requests = []
        for r in rows:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch admin demo requests")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_demo_request_status(request_id: int, req: dict):
    try:
        check_action_password(req.get('admin_action_password'))
        await check_super_admin(req.get('admin_user_id'))

        row = await demo_repository.update_demo_request_status(request_id, req.get('status'))
        if not row:
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]

        if req.get('status') == 'completed':
            try:
                _send_feedback_email(name, email)
            except Exception as email_err:
                logger.warning(f"Failed to send feedback email: {email_err}")

        return {"message": "Status updated successfully", "status": req.get('status')}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update demo request status")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_schedule_demo_meeting(request_id: int, req: dict):
    try:
        check_action_password(req.get('admin_action_password'))
        await check_super_admin(req.get('admin_user_id'))

        row = await demo_repository.get_demo_request_contact(request_id)
        if not row:
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]
        meet_link = req.get('meeting_link')

        await demo_repository.schedule_demo_meeting(
            request_id, req.get('date'), req.get('time'), meet_link
        )

        try:
            _send_meeting_invite_email(name, email, req.get('date'), req.get('time'), meet_link)
        except Exception as email_err:
            logger.warning(f"Failed to send meeting invite email: {email_err}")

        return {"message": "Meeting scheduled and email sent", "link": meet_link}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to schedule demo meeting")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_scheduled_demo_requests(user_id: str):
    try:
        await check_super_admin(user_id)
        rows = await demo_repository.get_scheduled_demo_requests()
        requests = []
        for r in rows:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch scheduled demo requests")
        raise HTTPException(status_code=500, detail=str(e))
