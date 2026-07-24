"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the business logic coordinator for managing user feedback tickets
in RAGMate. It allows end users to flag unhelpful AI responses, allows developers/admins
to resolve these tickets, and tracks customer verification of the resolutions.

From top to bottom, the file performs the following tasks:
1. Imports: Loads FastAPI exception classes and the feedback database access repository.
2. Logging: Initializes a department logger named "system" to audit ticket submissions,
   resolutions, and verifications.
3. Constraint Repair Helper (`handle_fix_db_constraint`): Fixes Postgres constraints
   to allow resolving tickets that don't have user IDs.
4. Ticket Ingestion Handler (`handle_submit_feedback`): Optimistically validates the UUID format
   of messages, registers votes (upvote/downvote) and comment details, and broadcasts alerts.
5. Ticket List Handlers:
   - `handle_get_open_feedback`: Lists active tickets for authorized roles in the workspace.
   - `handle_resolve_feedback`: Marks tickets as resolved.
   - `handle_get_pending_verification`: Fetches tickets awaiting customer validation.
   - `handle_verify_feedback`: Records whether the user is satisfied with the resolution.
"""

from fastapi import HTTPException  # Import web exceptions to raise clean HTTP error status codes
from db import feedback_repository  # Database access layer for feedback tables

# Logging modules
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "system" activities
logger = get_department_logger("system")

async def handle_fix_db_constraint():
    """
    Updates the database schema constraint on the feedback table so that
    tickets can be resolved even if the user records have changed or been cleared.

    Parameters:
        None

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if the SQL database constraint script fails.
    """
    logger.info("Admin request: Repairing feedback database constraints...")
    try:
        # Call database repository to execute the constraint updates
        await feedback_repository.fix_feedback_db_constraint()
        logger.info("Database feedback table constraint fixed successfully.")
        return {"message": "Database constraint updated successfully! You can now resolve tickets."}
    except Exception as e:
        logger.error(f"Error updating constraint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update constraint")


async def handle_submit_feedback(payload: dict):
    """
    Records a user's feedback (thumbs up/down and text comments) on an agent's response.
    Broadcasts real-time alerts to the workspace team dashboard.

    Parameters:
        payload (dict): A dictionary payload containing:
            - 'message_id' (str): The unique ID of the message being rated.
            - 'agent_id' (str): Linked AI Agent UUID.
            - 'workspace_id' (str): Workspace UUID.
            - 'vote_type' (str): Rating vote ('upvote' or 'downvote').
            - 'category' (str): Categorical flags (e.g. Accuracy, Tone).
            - 'comment_text' (str, optional): Custom user comments.
            - 'created_by' (str): Author's User ID.

    Returns:
        dict: A dictionary containing the newly created ticket 'id' and success status.

    Exceptions Raised:
        HTTPException(500): Raised if SQL insertions crash.
    """
    logger.info(f"Submitting response feedback for agent ID: {payload.get('agent_id')} (Vote: {payload.get('vote_type')})")
    try:
        import uuid
        msg_id = payload.get("message_id")
        try:
            # Validate UUID format to prevent database syntax errors
            uuid.UUID(str(msg_id))
        except ValueError:
            logger.warning(f"Optimistic UUID validation failed for message_id '{msg_id}'. Generating fallback UUID...")
            # If the format is invalid (e.g. mock data or frontend placeholders), generate a random tracking UUID
            msg_id = str(uuid.uuid4())
            
        logger.debug("Executing feedback insertion in database...")
        feedback_id = await feedback_repository.submit_feedback(
            msg_id, 
            payload.get("agent_id"), 
            payload.get("workspace_id"), 
            payload.get("vote_type"), 
            payload.get("category"), 
            payload.get("comment_text"), 
            payload.get("created_by")
        )
        logger.info(f"Feedback successfully recorded in database. Feedback ID: {feedback_id}")
        
        # Broadcast dashboard notification alerts
        logger.debug("Creating workspace dashboard alert notification...")
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(payload.get("workspace_id")),
                title="New Feedback Received",
                message="A user flagged an unhelpful or bad response from an agent.",
                notification_type="feedback_new"
            )
            logger.info("Feedback alert notification successfully broadcast.")
        except Exception as ne:
            logger.error(f"Failed to create new feedback notification: {str(ne)}", exc_info=True)
        
        return {"id": feedback_id, "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error submitting response feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


async def handle_get_open_feedback(workspace_id: str, user_id: str):
    """
    Lists active open feedback tickets for authorized roles in the workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID.
        user_id (str): The requesting user's UUID.

    Returns:
        list: A list of open ticket dictionaries.

    Exceptions Raised:
        HTTPException(403): Raised if the user is not associated or lacks access privileges.
        HTTPException(500): Raised if SQL queries fail.
    """
    logger.info(f"Retrieving active open feedback tickets for workspace ID: {workspace_id} (User: {user_id})")
    try:
        # 1. Access validation check
        logger.debug("Checking user role permission status in workspace...")
        user_role = await feedback_repository.check_workspace_role(workspace_id, user_id)
        if not user_role:
            logger.warning(f"Access denied: User {user_id} is not associated with workspace {workspace_id}")
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        # Authorize administrative/editor roles only
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            logger.warning(f"Access denied: User {user_id} has insufficient role: {role}")
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")

        # 2. Fetch records
        logger.debug("Querying active open feedback tickets in database...")
        rows = await feedback_repository.get_open_feedback(workspace_id)
        logger.debug(f"Retrieved {len(rows)} feedback records.")
        
        # 3. Format timestamp to ISO 8601 strings
        tickets = []
        for row in rows:
            tickets.append({
                "id": row[0],
                "message_id": row[1],
                "agent_id": row[2],
                "vote_type": row[3],
                "category": row[4],
                "comment_text": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "created_by": row[7],
                "message_content": row[8],
                "role": row[9],
                "agent_name": row[10]
            })
            
        logger.info(f"Successfully processed {len(tickets)} open feedback tickets.")
        return tickets
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching open feedback dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch open feedback")


async def handle_resolve_feedback(feedback_id: str, resolved_by: str):
    """
    Marks a feedback ticket as resolved. Restricted to authorized administrators.

    Parameters:
        feedback_id (str): The feedback ticket UUID.
        resolved_by (str): The unique database UUID of the administrator.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403): Raised if the user is not associated or lacks access privileges.
        HTTPException(404): Raised if the ticket ID is not found.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"Resolving feedback ticket ID: {feedback_id} (Resolved By: {resolved_by})")
    try:
        # Find Workspace ID linked to the ticket
        logger.debug("Checking feedback details to locate workspace ID...")
        feedback_row = await feedback_repository.get_feedback_workspace_id(feedback_id)
        if not feedback_row:
            logger.warning(f"Resolution aborted: Feedback ID {feedback_id} not found.")
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        workspace_id = feedback_row[0]

        # Verify administrative roles
        logger.debug("Checking user workspace permission role details...")
        user_role = await feedback_repository.check_workspace_role(workspace_id, resolved_by)
        if not user_role:
            logger.warning(f"Resolution denied: User {resolved_by} is not associated with workspace {workspace_id}")
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            logger.warning(f"Resolution denied: User {resolved_by} has insufficient role: {role}")
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")

        # Update resolution state in database
        logger.debug("Updating feedback ticket status to resolved...")
        await feedback_repository.mark_feedback_resolved(feedback_id, resolved_by)
        logger.info(f"Feedback ticket ID {feedback_id} successfully resolved in database.")
        
        # Broadcast resolved notifications
        logger.debug("Creating resolved ticket workspace notification...")
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(workspace_id),
                title="Feedback Ticket Resolved",
                message="A teammate has resolved a feedback ticket and marked it for verification.",
                notification_type="feedback_resolved"
            )
            logger.info("Feedback resolution notification broadcast successfully.")
        except Exception as ne:
            logger.error(f"Failed to create feedback resolved notification: {str(ne)}", exc_info=True)
        
        return {"message": "Feedback resolved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving feedback ID {feedback_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resolve feedback")


async def handle_get_pending_verification(workspace_id: str, user_id: str):
    """
    Fetches tickets resolved by administrators that are awaiting user validation.

    Parameters:
        workspace_id (str): Target Workspace UUID.
        user_id (str): Target User UUID.

    Returns:
        list: A list of pending validation ticket dictionaries.

    Exceptions Raised:
        HTTPException(500): Raised if database queries fail.
    """
    logger.info(f"Fetching tickets awaiting customer verification in workspace: {workspace_id} (User ID: {user_id})")
    try:
        # Fetch pending entries from database
        logger.debug("Querying database feedback pending verification...")
        rows = await feedback_repository.get_pending_verification(workspace_id, user_id)
        logger.debug(f"Retrieved {len(rows)} pending verification tickets.")
        
        tickets = []
        for row in rows:
            tickets.append({
                "id": row[0],
                "message_id": row[1],
                "agent_id": row[2],
                "category": row[3],
                "comment_text": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "message_content": row[6],
                "agent_name": row[7],
                "user_message": row[8]
            })
            
        logger.info(f"Successfully processed {len(tickets)} pending verification tickets.")
        return tickets
    except Exception as e:
        logger.error(f"Error fetching pending verification feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch pending verifications")


async def handle_verify_feedback(feedback_id: str, payload: dict):
    """
    Records customer verification of a resolved ticket.

    Parameters:
        feedback_id (str): The unique database feedback UUID.
        payload (dict): Contains:
            - 'user_id' (str): Owner validating resolution.
            - 'is_satisfied' (bool): Rating satisfaction flag.
            - 'comment' (str): Custom verification feedback remarks.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(403): Raised if the user is not the owner of the feedback.
        HTTPException(404): Raised if the feedback ticket ID is not found.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"Submitting customer verification for feedback ticket ID: {feedback_id} (Satisfied: {payload.get('is_satisfied')})")
    try:
        # Fetch target ticket details
        logger.debug("Retrieving feedback ticket metadata from database...")
        feedback_row = await feedback_repository.get_feedback_for_verification(feedback_id)
        if not feedback_row:
            logger.warning(f"Verification aborted: Feedback ID {feedback_id} not found.")
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        
        # Verify ownership before updating
        if str(feedback_row[0]) != str(payload.get("user_id")):
            logger.warning(f"Verification rejected: User ID {payload.get('user_id')} does not own feedback ID {feedback_id}")
            raise HTTPException(status_code=403, detail="Not authorized to verify this feedback")
            
        # Update verification details in database
        logger.debug("Updating database verification details...")
        await feedback_repository.verify_feedback(
            feedback_id, 
            payload.get("is_satisfied"), 
            payload.get("comment"), 
            feedback_row[1]
        )
        logger.info(f"Feedback ID {feedback_id} verification successfully recorded.")
        return {"message": "Feedback verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying feedback ID {feedback_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify feedback")
