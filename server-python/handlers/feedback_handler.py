import logging
from fastapi import HTTPException
from db import feedback_repository

logger = logging.getLogger(__name__)

async def handle_fix_db_constraint():
    try:
        await feedback_repository.fix_feedback_db_constraint()
        return {"message": "Database constraint updated successfully! You can now resolve tickets."}
    except Exception as e:
        logger.error(f"Error updating constraint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update constraint")


async def handle_submit_feedback(payload: dict):
    try:
        import uuid
        msg_id = payload.get("message_id")
        try:
            uuid.UUID(str(msg_id))
        except ValueError:
            # If the frontend sent an optimistic ID, generate a random UUID so Postgres doesn't crash on type: uuid
            msg_id = str(uuid.uuid4())
            
        feedback_id = await feedback_repository.submit_feedback(
            msg_id, 
            payload.get("agent_id"), 
            payload.get("workspace_id"), 
            payload.get("vote_type"), 
            payload.get("category"), 
            payload.get("comment_text"), 
            payload.get("created_by")
        )
        
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(payload.get("workspace_id")),
                title="New Feedback Received",
                message="A user flagged an unhelpful or bad response from an agent.",
                notification_type="feedback_new"
            )
        except Exception as ne:
            logger.error(f"Failed to create new feedback notification: {ne}")
        
        return {"id": feedback_id, "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


async def handle_get_open_feedback(workspace_id: str, user_id: str):
    try:
        user_role = await feedback_repository.check_workspace_role(workspace_id, user_id)
        if not user_role:
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")

        rows = await feedback_repository.get_open_feedback(workspace_id)
        
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
            
        return tickets
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching open feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch open feedback")


async def handle_resolve_feedback(feedback_id: str, resolved_by: str):
    try:
        feedback_row = await feedback_repository.get_feedback_workspace_id(feedback_id)
        if not feedback_row:
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        workspace_id = feedback_row[0]

        user_role = await feedback_repository.check_workspace_role(workspace_id, resolved_by)
        if not user_role:
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")

        await feedback_repository.mark_feedback_resolved(feedback_id, resolved_by)
        
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(workspace_id),
                title="Feedback Ticket Resolved",
                message="A teammate has resolved a feedback ticket and marked it for verification.",
                notification_type="feedback_resolved"
            )
        except Exception as ne:
            logger.error(f"Failed to create feedback resolved notification: {ne}")
        
        return {"message": "Feedback resolved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve feedback")


async def handle_get_pending_verification(workspace_id: str, user_id: str):
    try:
        rows = await feedback_repository.get_pending_verification(workspace_id, user_id)
        
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
            
        return tickets
    except Exception as e:
        logger.error(f"Error fetching pending verification feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending verifications")


async def handle_verify_feedback(feedback_id: str, payload: dict):
    try:
        feedback_row = await feedback_repository.get_feedback_for_verification(feedback_id)
        if not feedback_row:
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        
        if str(feedback_row[0]) != str(payload.get("user_id")):
            raise HTTPException(status_code=403, detail="Not authorized to verify this feedback")
            
        await feedback_repository.verify_feedback(
            feedback_id, 
            payload.get("is_satisfied"), 
            payload.get("comment"), 
            feedback_row[1]
        )
        return {"message": "Feedback verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify feedback")
