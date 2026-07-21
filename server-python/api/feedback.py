import logging
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user

from handlers.feedback_handler import (
    handle_fix_db_constraint,
    handle_submit_feedback,
    handle_get_open_feedback,
    handle_resolve_feedback,
    handle_get_pending_verification,
    handle_verify_feedback
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

class FeedbackCreate(BaseModel):
    message_id: str
    agent_id: Optional[str] = None
    workspace_id: str
    vote_type: str
    category: Optional[str] = None
    comment_text: Optional[str] = None
    created_by: Optional[str] = None

class FeedbackResolve(BaseModel):
    pass

class FeedbackVerify(BaseModel):
    is_satisfied: bool
    comment: Optional[str] = None

@router.get("/api/feedback/fix-db")
async def fix_db_constraint():
    """
    What it does: HTTP endpoint to fix a broken database constraint preventing ticket resolution.
    Args: None.
    Returns: A success message.
    """
    return await handle_fix_db_constraint()

@router.post("/api/feedback")
async def submit_feedback(payload: FeedbackCreate):
    """
    What it does: HTTP endpoint for end-users to submit a complaint about an AI message.
    Args:
        payload (FeedbackCreate): The feedback details.
    Returns: The ID of the created feedback ticket.
    """
    return await handle_submit_feedback(payload.dict())

@router.get("/api/feedback/open")
async def get_open_feedback(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint for workspace members to view unresolved feedback tickets.
    Args:
        workspace_id (str): The workspace to query.
        user_id (str): The requesting user.
    Returns: A list of open feedback tickets.
    """
    user_id = current_user["sub"]
    return await handle_get_open_feedback(workspace_id, user_id)

@router.post("/api/feedback/{feedback_id}/resolve")
async def resolve_feedback(feedback_id: str, payload: FeedbackResolve, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint for teammates to mark a ticket as resolved and ready for verification.
    Args:
        feedback_id (str): The ticket ID.
        payload (FeedbackResolve): The user ID resolving the ticket.
    Returns: A success message.
    """
    return await handle_resolve_feedback(feedback_id, current_user["sub"])

@router.get("/api/feedback/pending-verification")
async def get_pending_verification(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint for users to view their tickets that have been fixed by the team.
    Args:
        workspace_id (str): The workspace ID.
        user_id (str): The original user's ID.
    Returns: A list of pending tickets.
    """
    user_id = current_user["sub"]
    return await handle_get_pending_verification(workspace_id, user_id)

@router.post("/api/feedback/{feedback_id}/verify")
async def verify_feedback(feedback_id: str, payload: FeedbackVerify, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint for the original user to approve or reject the team's fix.
    Args:
        feedback_id (str): The ticket ID.
        payload (FeedbackVerify): The verdict and optional comments.
    Returns: A success message.
    """
    data = payload.dict()
    data["user_id"] = current_user["sub"]
    return await handle_verify_feedback(feedback_id, data)
