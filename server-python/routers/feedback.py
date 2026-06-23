"""
Feedback Router.
Responsibility: Manages the Human-in-the-Loop (HITL) feedback system.
When users downvote or flag an AI response in a widget, it generates a 'ticket' here.
Workspace teammates can review the bad responses, see the context, and verify fixes.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class FeedbackCreate(BaseModel):
    message_id: str
    agent_id: Optional[str] = None
    workspace_id: str
    vote_type: str # Usually 'upvote' or 'downvote'
    category: Optional[str] = None # e.g., 'hallucination', 'rude', 'unhelpful'
    comment_text: Optional[str] = None
    created_by: Optional[str] = None

class FeedbackResolve(BaseModel):
    resolved_by: str

# ==========================================
# MIGRATION / DB FIX UTILITY
# ==========================================

@router.get("/api/feedback/fix-db")
async def fix_db_constraint():
    """
    A temporary endpoint used to hot-fix a strict database constraint that was 
    preventing tickets from moving into the 'pending_verification' state.
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

# ==========================================
# FEEDBACK CREATION (From the Widget)
# ==========================================

@router.post("/api/feedback")
async def submit_feedback(payload: FeedbackCreate):
    """
    Called when an end-user clicks 'Thumbs Down' on an AI message.
    Logs the complaint and fires off a notification to the workspace owners.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Store the actual feedback
        cursor.execute(
            """
            INSERT INTO message_feedback 
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                payload.message_id, 
                payload.agent_id, 
                payload.workspace_id, 
                payload.vote_type, 
                payload.category, 
                payload.comment_text, 
                payload.created_by
            )
        )
        feedback_id = cursor.fetchone()[0]
        
        # 2. Alert the team via the in-app notification bell
        cursor.execute(
            """
            INSERT INTO notifications (workspace_id, title, message, type)
            VALUES (%s, %s, %s, 'feedback_new');
            """,
            (
                payload.workspace_id,
                "New Feedback",
                f"A user flagged a response from an agent."
            )
        )
        
        conn.commit()
        
        return {"id": feedback_id, "message": "Feedback submitted successfully"}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==========================================
# FEEDBACK DASHBOARD (For Teammates)
# ==========================================

@router.get("/api/feedback/open")
async def get_open_feedback(workspace_id: str = Query(...), user_id: str = Query(...)):
    """
    Fetches the queue of unresolved complaints for the workspace.
    Includes an Authorization Gate to ensure the requester is actually a member of the team.
    Joins with chat_messages to pull the exact bad response the AI generated.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Auth Gate: Ensure user has privileges to see the queue
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

        # Fetch the tickets
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

@router.post("/api/feedback/{feedback_id}/resolve")
async def resolve_feedback(feedback_id: str, payload: FeedbackResolve):
    """
    Called when a teammate believes they've fixed the AI's behavior (e.g. by uploading better documents).
    Moves the ticket to 'pending_verification', meaning the original complainant needs to test it.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify ticket exists and get its workspace
        cursor.execute("SELECT workspace_id FROM message_feedback WHERE id = %s", (feedback_id,))
        feedback_row = cursor.fetchone()
        if not feedback_row:
            raise HTTPException(status_code=404, detail="Feedback ticket not found")
        workspace_id = feedback_row[0]

        # Auth Gate
        cursor.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, payload.resolved_by)
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
            (payload.resolved_by, feedback_id)
        )
        
        # Alert the whole team that someone is handling the issue
        cursor.execute(
            """
            INSERT INTO notifications (workspace_id, title, message, type)
            VALUES (%s, %s, %s, 'feedback_resolved');
            """,
            (
                workspace_id,
                "Feedback Resolved",
                "A teammate has resolved a feedback ticket."
            )
        )
        
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

@router.get("/api/feedback/pending-verification")
async def get_pending_verification(workspace_id: str = Query(...), user_id: str = Query(...)):
    """
    Fetches tickets that a teammate marked as 'resolved', but need to be confirmed by the original user.
    Uses a subquery to fetch the user's ORIGINAL question so they have full context when verifying.
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
                       -- Subquery to find the last thing the user said before the AI's bad response
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

class FeedbackVerify(BaseModel):
    is_satisfied: bool
    comment: Optional[str] = None
    user_id: str

@router.post("/api/feedback/{feedback_id}/verify")
async def verify_feedback(feedback_id: str, payload: FeedbackVerify):
    """
    The final step. The user tests the AI again. 
    If satisfied, the ticket is permanently closed.
    If NOT satisfied, the ticket is re-opened, and the user's angry comments are appended.
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
        
        # Security: Only the person who created the ticket can verify it.
        if str(feedback_row[0]) != str(payload.user_id):
            raise HTTPException(status_code=403, detail="Not authorized to verify this feedback")
            
        if payload.is_satisfied:
            # All good, shut it down
            cursor.execute("UPDATE message_feedback SET status = 'closed' WHERE id = %s", (feedback_id,))
        else:
            # Reopen the ticket, keeping the old comments and adding the new ones
            new_comment = feedback_row[1] or ""
            if payload.comment:
                new_comment = f"{new_comment}\n\n[User Unsatisfied]: {payload.comment}"
                
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
