"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the business logic coordinator for managing client
Demo Requests, scheduling demo meetings, and sending out transactional emails
for BlinkBot (RAGMate).

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard SMTP client libraries (smtplib), MIME multipart email formatter
   utilities (MIMEText, MIMEMultipart), os parameters, FastAPI HTTP exception handling, 
   admin validator helper checks, and database repositories.
2. Logging: Scopes a department logger named "system" to record demo booking transactions.
3. Private Email Dispatchers:
   - `_send_demo_email`: Formats a rich HTML email template and sends it to the platform owners
     notifying them that a user has submitted a new demo request.
   - `_send_meeting_invite_email`: Emails scheduled meeting links and dates to clients.
   - `_send_feedback_email`: Sends post-demo follow-up emails asking users for feedback.
4. Client Request Handler:
   - `handle_submit_demo_request`: Records submissions in the database and triggers internal emails.
5. Admin Registry & Management Handlers:
   - `handle_get_admin_demo_requests`: Lists all demo requests.
   - `handle_update_demo_request_status`: Updates status flags (triggering feedback email if 'completed').
   - `handle_schedule_demo_meeting`: Updates meeting details and sends invitation emails to clients.
   - `handle_get_scheduled_demo_requests`: Filters and lists meetings that have already been scheduled.
"""

import smtplib  # Standard Python library for sending emails using Simple Mail Transfer Protocol (SMTP)
import os  # System utility to read environment settings (SMTP credentials)
from email.mime.text import MIMEText  # Helper to create HTML or plain text email bodies
from email.mime.multipart import MIMEMultipart  # Helper to combine multiple parts (e.g. HTML and plain text) in one email
from fastapi import HTTPException  # Raise clean HTTP errors to the client
from handlers.admin_handler import check_super_admin, check_action_password  # Auth guard helpers
from db import demo_repository  # Database access layer for demo tables

# Logging utility
from utils.logger import get_department_logger

# Scope a department logger specifically to "system" actions
logger = get_department_logger("system")

def _send_demo_email(req: dict, request_id: int, created_at):
    """
    Sends an internal notification email to the administrator when a new demo is requested.

    Parameters:
        req (dict): A dictionary containing 'name', 'email', 'company', and 'message'.
        request_id (int): The unique database row ID of the registered request.
        created_at (datetime): Timestamp when the request was submitted.

    Returns:
        None: Sends email directly via SMTP client.
    """
    logger.debug(f"Compiling demo request notification email for: {req.get('email')}")
    # Read mail credentials from server environment settings
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    notify_email = os.getenv("NOTIFY_EMAIL") or "techmate.ed@gmail.com"
 
    # Skip email notification if credentials are not configured in environment
    if not smtp_user or not smtp_pass or not notify_email:
        logger.warning("SMTP or destination email not configured in environment, skipping demo email notification.")
        return

    # Build the multipart container to hold HTML layouts
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 New Demo Request from {req.get('name')} — BlinkBot"
    msg["From"] = f"BlinkBot <{smtp_user}>"
    msg["To"] = notify_email

    # HTML body template for the notification email
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

    try:
        # Establish network connection to SMTP server
        logger.debug(f"Connecting to SMTP server at {smtp_host}:{smtp_port}...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()                        # Start Transport Layer Security (TLS) encryption
            server.login(smtp_user, smtp_pass)       # Authenticate with credentials
            server.sendmail(smtp_user, notify_email, msg.as_string())  # Dispatch email
        logger.info(f"Demo request notification email successfully sent to {notify_email}")
    except Exception as smtp_err:
        logger.error(f"Failed to send demo notification email: {str(smtp_err)}", exc_info=True)


def _send_meeting_invite_email(name: str, email: str, date: str, time: str, link: str):
    """
    Sends a meeting invite confirmation email containing the scheduled date, time, 
    and connection link to a user.

    Parameters:
        name (str): Recipient's display name.
        email (str): Recipient's destination email address.
        date (str): Scheduled meeting date string.
        time (str): Scheduled meeting time string.
        link (str): Video call link (e.g. Google Meet link).

    Returns:
        None: Sends email directly via SMTP client.
    """
    logger.debug(f"Compiling demo meeting invite email for: {email}")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
 
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured in environment, skipping demo meeting invite email.")
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

    try:
        logger.debug(f"Connecting to SMTP server to send meeting invite...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email, msg.as_string())
        logger.info(f"Demo meeting scheduled invitation successfully sent to {email}")
    except Exception as smtp_err:
        logger.error(f"Failed to send demo meeting invitation email: {str(smtp_err)}", exc_info=True)


def _send_feedback_email(name: str, email: str):
    """
    Emails a follow-up feedback request to a user after their demo meeting is marked complete.

    Parameters:
        name (str): Recipient's display name.
        email (str): Recipient's destination email address.

    Returns:
        None: Sends email directly via SMTP client.
    """
    logger.debug(f"Compiling demo feedback email for: {email}")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
 
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP not configured in environment, skipping demo feedback follow-up email.")
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

    try:
        logger.debug("Connecting to SMTP server to send feedback follow-up...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email, msg.as_string())
        logger.info(f"Demo feedback follow-up email successfully sent to {email}")
    except Exception as smtp_err:
        logger.error(f"Failed to send demo feedback email: {str(smtp_err)}", exc_info=True)


async def handle_submit_demo_request(req: dict):
    """
    Records a user's demo request in the database and triggers internal notification email.

    Parameters:
        req (dict): The client submission form containing 'name', 'email', 'company', and 'message'.

    Returns:
        dict: A confirmation dictionary indicating database sync success and containing the request ID.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database insert crashes.
    """
    logger.info(f"Submitting a new demo request from '{req.get('name')}' (Email: {req.get('email')})")
    try:
        # Call repository method to insert demo request in database
        logger.debug("Executing demo request database insert query...")
        row = await demo_repository.submit_demo_request(
            req.get('name'), req.get('email'), req.get('company'), req.get('message')
        )
        logger.info(f"Demo request recorded in database. ID: {row[0]}")
        
        # Fire off notification email to BlinkBot administrators
        try:
            _send_demo_email(req, row[0], row[1])
        except Exception as email_err:
            # We catch email errors separately so a failure in the SMTP module doesn't block request submission confirmation
            logger.warning(f"Demo email notification failed: {email_err}")

        return {"success": True, "message": "Demo request submitted successfully!", "id": row[0]}
    except Exception as e:
        logger.error(f"Demo request submission failed for {req.get('email')}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_admin_demo_requests(user_id: str):
    """
    Fetches all demo requests submitted to the system. Restricted to Super Administrators.

    Parameters:
        user_id (str): The unique database UUID identifying the administrator making request.

    Returns:
        dict: A dictionary with a key "requests" containing a list of request dictionaries.

    Exceptions Raised:
        HTTPException(403): Raised if the user is not a Super Admin.
        HTTPException(500): Raised if SQL query fails.
    """
    logger.info(f"Admin request: Fetching all demo requests list. Requested by user ID: {user_id}")
    try:
        # Verify requester has admin credentials
        await check_super_admin(user_id)
        
        # Query database rows
        logger.debug("Querying demo requests list from database...")
        rows = await demo_repository.get_admin_demo_requests()
        logger.debug(f"Retrieved {len(rows)} demo request records.")
        
        # Format database tuples into a list of clean dictionaries
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
        logger.info(f"Successfully processed {len(requests)} demo requests.")
        return {"requests": requests}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch admin demo requests: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_demo_request_status(request_id: int, req: dict):
    """
    Updates the status flag of a demo request.
    If status is set to 'completed', automatically sends a feedback follow-up email.

    Parameters:
        request_id (int): The unique database row ID of the demo request.
        req (dict): Payload containing:
            - 'admin_action_password' (str): Second-factor validation password.
            - 'admin_user_id' (str): Requester's super admin ID.
            - 'status' (str): New target status (e.g. 'pending', 'scheduled', 'completed').

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403): Raised for password or role authentication failures.
        HTTPException(404): Raised if the target request ID is not found.
        HTTPException(500): Raised if updates fail.
    """
    logger.info(f"Admin request: Updating status for demo request ID: {request_id}")
    try:
        # Verify dual-factor admin authorizations
        check_action_password(req.get('admin_action_password'))
        await check_super_admin(req.get('admin_user_id'))

        status = req.get('status')
        logger.debug(f"Updating status for demo request ID {request_id} to '{status}'...")
        row = await demo_repository.update_demo_request_status(request_id, status)
        if not row:
            logger.warning(f"Update status rejected: Demo request ID {request_id} not found.")
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]

        # Trigger follow-up email if set to 'completed'
        if status == 'completed':
            logger.info(f"Demo request ID {request_id} marked as completed. Triggering demo feedback email...")
            try:
                _send_feedback_email(name, email)
            except Exception as email_err:
                logger.warning(f"Failed to send feedback email: {email_err}")

        logger.info(f"Demo request ID {request_id} status updated successfully to '{status}'.")
        return {"message": "Status updated successfully", "status": status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update status for demo request ID {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_schedule_demo_meeting(request_id: int, req: dict):
    """
    Saves scheduled meeting details in the database and sends a meeting invitation email to the user.

    Parameters:
        request_id (int): The unique database row ID of the target request.
        req (dict): Payload containing:
            - 'admin_action_password' (str): Second-factor validation password.
            - 'admin_user_id' (str): Requester's super admin ID.
            - 'meeting_link' (str): Video call link (e.g. Google Meet link).
            - 'date' (str): Scheduled meeting date string.
            - 'time' (str): Scheduled meeting time string.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403): Raised for password or role authentication failures.
        HTTPException(404): Raised if the target request ID is not found.
        HTTPException(500): Raised if database queries fail.
    """
    logger.info(f"Admin request: Scheduling demo meeting for request ID: {request_id}")
    try:
        # Verify dual-factor admin authorizations
        check_action_password(req.get('admin_action_password'))
        await check_super_admin(req.get('admin_user_id'))

        logger.debug("Retrieving demo request details from database...")
        row = await demo_repository.get_demo_request_contact(request_id)
        if not row:
            logger.warning(f"Meeting schedule rejected: Demo request ID {request_id} not found.")
            raise HTTPException(status_code=404, detail="Demo request not found")
        
        name, email = row[0], row[1]
        meet_link = req.get('meeting_link')
        date_str = req.get('date')
        time_str = req.get('time')

        # Save scheduled parameters in database
        logger.debug(f"Updating meeting scheduling parameters for request ID {request_id} in database...")
        await demo_repository.schedule_demo_meeting(request_id, date_str, time_str, meet_link)

        # Trigger client invitation email
        logger.info(f"Demo meeting successfully scheduled in database for request ID: {request_id}. Triggering invitation email...")
        try:
            _send_meeting_invite_email(name, email, date_str, time_str, meet_link)
        except Exception as email_err:
            logger.warning(f"Failed to send meeting invite email: {email_err}")

        return {"message": "Meeting scheduled and email sent", "link": meet_link}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule meeting for request ID {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_scheduled_demo_requests(user_id: str):
    """
    Fetches all demo requests that have been scheduled. Restricted to Super Administrators.

    Parameters:
        user_id (str): The unique database UUID identifying the administrator making request.

    Returns:
        dict: A dictionary with a key "requests" containing a list of scheduled request dictionaries.

    Exceptions Raised:
        HTTPException(403): Raised if the user is not a Super Admin.
        HTTPException(500): Raised if SQL database queries fail.
    """
    logger.info(f"Admin request: Fetching all scheduled demo requests. Requested by user ID: {user_id}")
    try:
        # Verify administrative privileges
        await check_super_admin(user_id)
        
        # Query database rows
        logger.debug("Querying database scheduled demo requests...")
        rows = await demo_repository.get_scheduled_demo_requests()
        logger.debug(f"Retrieved {len(rows)} scheduled demo requests.")
        
        # Format rows
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
        logger.info(f"Successfully processed {len(requests)} scheduled demo requests.")
        return {"requests": requests}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch scheduled admin requests: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
