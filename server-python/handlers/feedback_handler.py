import logging
from fastapi import HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

async def handle_fix_db_constraint():
    """
    What it does: Hot-fixes a strict database constraint preventing tickets from moving into the 'pending_verification' state.
    Args: None.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE message_feedback DROP CONSTRAINT IF EXISTS message_feedback_status_check;")
        cursor.execute("ALTER TABLE message_feedback ADD CONSTRAINT message_feedback_status_check CHECK (status IN ('open', 'resolved', 'pending_verification', 'closed'));")
        conn.commit()
        return {"message": "Database constraint updated successfully! You can now resolve tickets."}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_submit_feedback(payload: dict):
    """
    What it does: Logs a user complaint about an AI message and sends a real-time notification to the workspace owners.
    Args:
        payload (dict): The feedback data containing message_id, agent_id, workspace_id, vote_type, category, comment_text, and created_by.
    Returns: The ID of the newly created feedback ticket.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO message_feedback 
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                payload.get("message_id"), 
                payload.get("agent_id"), 
                payload.get("workspace_id"), 
                payload.get("vote_type"), 
                payload.get("category"), 
                payload.get("comment_text"), 
                payload.get("created_by")
            )
        )
        feedback_id = cursor.fetchone()[0]
        
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
        
        conn.commit()
        return {"id": feedback_id, "message": "Feedback submitted successfully"}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_open_feedback(workspace_id: str, user_id: str):
    """
    What it does: Fetches the queue of unresolved complaints for the workspace, after verifying the user has adequate permissions.
    Args:
        workspace_id (str): The workspace to fetch tickets for.
        user_id (str): The ID of the requesting user.
    Returns: A list of open feedback tickets including the bad AI response.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id)
        )
        user_role = cursor.fetchone()
        if not user_role:
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            raise HTTPException(status_code=403, detail="Not authorized to view feedback dashboard")

        cursor.execute(
            """
            SELECT f.id, f.message_id, f.agent_id, f.vote_type, f.category, 
                   f.comment_text, f.created_at, f.created_by,
                   m.content as message_content, m.role,
                   a.name as agent_name
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.status = 'open'
            ORDER BY f.created_at DESC;
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
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
        if conn: conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Error fetching open feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch open feedback")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_resolve_feedback(feedback_id: str, resolved_by: str):
    """
    What it does: Moves a ticket to 'pending_verification' status and notifies the team.
    Args:
        feedback_id (str): The ID of the feedback ticket.
        resolved_by (str): The ID of the user resolving it.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT workspace_id FROM message_feedback WHERE id = %s", (feedback_id,))
        feedback_row = cursor.fetchone()
        if not feedback_row:
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        workspace_id = feedback_row[0]

        cursor.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, resolved_by)
        )
        user_role = cursor.fetchone()
        if not user_role:
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")
            
        role = str(user_role[0]).lower() if user_role[0] else ""
        if role not in ['admin', 'teammate', 'editor', 'owner']:
            raise HTTPException(status_code=403, detail="Not authorized to resolve feedback")

        cursor.execute(
            """
            UPDATE message_feedback
            SET status = 'pending_verification', resolved_at = now(), resolved_by = %s
            WHERE id = %s
            RETURNING id;
            """,
            (resolved_by, feedback_id)
        )
        
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
        
        conn.commit()
        return {"message": "Feedback resolved successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error resolving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve feedback")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_pending_verification(workspace_id: str, user_id: str):
    """
    What it does: Fetches tickets marked 'resolved' by the team that await the original user's verification.
    Args:
        workspace_id (str): The workspace to query.
        user_id (str): The ID of the original user who filed the ticket.
    Returns: A list of pending tickets, including the user's original question for context.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT f.id, f.message_id, f.agent_id, f.category, 
                   f.comment_text, f.created_at,
                   m.content as message_content,
                   a.name as agent_name,
                   (
                       SELECT content 
                       FROM chat_messages um 
                       WHERE um.session_id = m.session_id 
                         AND um.role = 'user' 
                         AND um.created_at < m.created_at 
                       ORDER BY created_at DESC 
                       LIMIT 1
                   ) as user_message
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.created_by = %s AND f.status = 'pending_verification'
            ORDER BY f.resolved_at DESC;
            """,
            (workspace_id, user_id)
        )
        rows = cursor.fetchall()
        
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_verify_feedback(feedback_id: str, payload: dict):
    """
    What it does: Processes the final step in the HITL loop. If the user is satisfied, closes the ticket. Otherwise, reopens it and appends their new comment.
    Args:
        feedback_id (str): The ticket ID.
        payload (dict): The user's verdict (is_satisfied) and optional comments.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT created_by, comment_text FROM message_feedback WHERE id = %s", (feedback_id,))
        feedback_row = cursor.fetchone()
        if not feedback_row:
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        
        if str(feedback_row[0]) != str(payload.get("user_id")):
            raise HTTPException(status_code=403, detail="Not authorized to verify this feedback")
            
        if payload.get("is_satisfied"):
            cursor.execute("UPDATE message_feedback SET status = 'closed' WHERE id = %s", (feedback_id,))
        else:
            new_comment = feedback_row[1] or ""
            if payload.get("comment"):
                new_comment = f"{new_comment}\\n\\n[User Unsatisfied]: {payload.get('comment')}"
                
            cursor.execute(
                """
                UPDATE message_feedback
                SET status = 'open', comment_text = %s
                WHERE id = %s
                """,
                (new_comment, feedback_id)
            )
            
        conn.commit()
        return {"message": "Feedback verified successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error verifying feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify feedback")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
