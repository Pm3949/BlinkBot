"""
================================================================================
USER FEEDBACK & TICKETING ROUTER LAYER (feedback.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for the platform's user feedback and ticketing system.
It supports a feedback lifecycle:
1. Ticket Submission: End-users upvote or downvote AI responses, creating a feedback ticket containing the message
   reference, category, and comments.
2. Administrative Review: Workspace members view unresolved tickets.
3. Resolution: Team members mark tickets as resolved, moving them to a 'pending verification' state.
4. User Verification: The original user verifies the fix, closing the ticket or reopening it.

DATABASE RECOVERY PATH:
- Includes a utility route `/api/feedback/fix-db` to programmatically update database table constraints,
  ensuring smooth transitions between ticket states.
"""

import logging
from utils.logger import get_department_logger
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user

# Import the feedback management handlers.
from handlers.feedback_handler import (
    handle_fix_db_constraint,
    handle_submit_feedback,
    handle_get_open_feedback,
    handle_resolve_feedback,
    handle_get_pending_verification,
    handle_verify_feedback
)

# Initialize standard module-level logger.
logger = get_department_logger("system")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["feedback"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class FeedbackCreate(BaseModel):
    """
    Validation schema for submitting a user feedback ticket.
    """
    message_id: str # UUID of the target chat message being reported
    agent_id: Optional[str] = None # UUID of the backing agent
    workspace_id: str # Parent workspace UUID
    vote_type: str # Vote type (e.g. 'upvote', 'downvote')
    category: Optional[str] = None # Issue category (e.g., 'incorrect', 'slow')
    comment_text: Optional[str] = None # Optional user description of the issue
    created_by: Optional[str] = None # Optional reporter ID override


class FeedbackResolve(BaseModel):
    """
    Validation schema for resolving feedback tickets.
    """
    pass


class FeedbackVerify(BaseModel):
    """
    Validation schema for verifying ticket resolutions.
    """
    is_satisfied: bool # True if the user approves the fix, False to reopen the ticket
    comment: Optional[str] = None # Optional comments explaining the verdict


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/api/feedback/fix-db")
async def fix_db_constraint():
    """
    Applies updates to database table constraints.

    Purpose:
        Helper endpoint that resolves constraints on the feedback table
        to allow status transitions.

    Parameters:
        None.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Modifies constraints on database tables.

    Errors / Exceptions:
        - Throws database errors if schema migrations fail.
    """
    # Execute constraint adjustments using the handler.
    return await handle_fix_db_constraint()


@router.post("/api/feedback")
async def submit_feedback(payload: FeedbackCreate):
    """
    Submits a new feedback ticket.

    Purpose:
        Public route that allows users to rate or report messages.

    Parameters:
        payload (FeedbackCreate): Pydantic body containing message references and vote parameters.

    Returns:
        dict: Success confirmation containing the new ticket ID.

    Side Effects / State Changes:
        - Writes a new row to the `feedback_tickets` table.

    Errors / Exceptions:
        - Raises 400 Bad Request if the target message ID is invalid.
    """
    # Create the ticket.
    return await handle_submit_feedback(payload.dict())


@router.get("/api/feedback/open")
async def get_open_feedback(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    Lists unresolved feedback tickets for a workspace.

    Purpose:
        Populates management lists for workspace administrators to review reported issues.

    Parameters:
        workspace_id (str): Target workspace UUID.
        current_user (dict): JWT details.

    Returns:
        list of dict: Open feedback ticket records.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Fetch open tickets.
    return await handle_get_open_feedback(workspace_id, user_id)


@router.post("/api/feedback/{feedback_id}/resolve")
async def resolve_feedback(feedback_id: str, payload: FeedbackResolve, current_user: dict = Depends(get_current_user)):
    """
    Marks a feedback ticket as resolved.

    Purpose:
        Moves a ticket to a resolved status, waiting for user verification.

    Parameters:
        feedback_id (str): UUID of the target ticket.
        payload (FeedbackResolve): Empty body schema.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the status column of the target row in the database.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the ticket is not found.
    """
    # Resolve the ticket.
    return await handle_resolve_feedback(feedback_id, current_user["sub"])


@router.get("/api/feedback/pending-verification")
async def get_pending_verification(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    Lists resolved tickets waiting for verification.

    Purpose:
        Shows the original reporter their tickets that have been fixed by the team.

    Parameters:
        workspace_id (str): Target workspace UUID.
        current_user (dict): JWT details.

    Returns:
        list of dict: Pending verification ticket records.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Fetch pending tickets.
    return await handle_get_pending_verification(workspace_id, user_id)


@router.post("/api/feedback/{feedback_id}/verify")
async def verify_feedback(feedback_id: str, payload: FeedbackVerify, current_user: dict = Depends(get_current_user)):
    """
    Verifies a ticket resolution.

    Purpose:
        Logs the user's verdict, closing the ticket or returning it to the open queue.

    Parameters:
        feedback_id (str): UUID of the target ticket.
        payload (FeedbackVerify): Contains the verdict and comments.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the status column to 'closed' or 'reopened' in the database.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the ticket is not found.
    """
    # Convert Pydantic fields to a dictionary.
    data = payload.dict()
    # Inject the user's UUID.
    data["user_id"] = current_user["sub"]
    # Verify the resolution.
    return await handle_verify_feedback(feedback_id, data)


@router.get("/api/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves all open feedback memory logs for a specific agent.
    """
    from handlers.feedback_handler import handle_get_agent_feedback
    return await handle_get_agent_feedback(agent_id)


@router.delete("/api/agents/{agent_id}/memory")
async def clear_agent_memory(agent_id: str, current_user: dict = Depends(get_current_user)):
    """
    Clears all open feedback memory logs for a specific agent.
    """
    from handlers.feedback_handler import handle_clear_agent_feedback
    return await handle_clear_agent_feedback(agent_id)


@router.delete("/api/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, current_user: dict = Depends(get_current_user)):
    """
    Deletes a specific feedback memory log entry.
    """
    from handlers.feedback_handler import handle_delete_feedback
    return await handle_delete_feedback(feedback_id)
