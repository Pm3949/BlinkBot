"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all AI Chat Feedback Ticket
management actions in the RAGMate backend. It maps inbound HTTP REST requests
directly to the underlying business logic executors defined inside the feedback
handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard logging controllers, FastAPI routing modules (APIRouter, Query, Depends),
   Pydantic schemas, typing variables, and JWT credentials guards.
2. Routing Initialization: Declares the APIRouter for 'feedback' tag groupings.
3. Input Payload Validation Schemas:
   - `FeedbackCreate`: Validates JSON payloads when creating a message feedback ticket.
   - `FeedbackResolve`: Empty schema placeholder for resolution endpoint validations.
   - `FeedbackVerify`: Validates JSON payloads when users verify resolved feedback.
4. HTTP Routes:
   - GET `/api/feedback/fix-db`: Troubleshooting utility to check database constraints.
   - POST `/api/feedback`: Public/internal submission of user feedback complaints.
   - GET `/api/feedback/open`: Lists unresolved feedback tickets in a workspace.
   - POST `/api/feedback/{id}/resolve`: Teammates endpoint to resolve a feedback ticket.
   - GET `/api/feedback/pending-verification`: Lists resolved tickets awaiting user verification.
   - POST `/api/feedback/{id}/verify`: Original reporter endpoint to verify/close tickets.
"""

import logging  # Import python logging library
from fastapi import APIRouter, Query, Depends  # FastAPI Router, Query parameter parsing, and Depends injection
from pydantic import BaseModel  # Pydantic BaseModels for payload validations
from typing import Optional  # Import Optional type mapping for query validations
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import feedback logic handlers
from handlers.feedback_handler import (
    handle_fix_db_constraint,
    handle_submit_feedback,
    handle_get_open_feedback,
    handle_resolve_feedback,
    handle_get_pending_verification,
    handle_verify_feedback
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for feedback endpoints
router = APIRouter(tags=["feedback"])

class FeedbackCreate(BaseModel):
    """
    Validates payload options when submitting new message feedback.
    """
    message_id: str                            # The targeted message UUID being reported
    agent_id: Optional[str] = None             # The linked AI Agent ID (optional)
    workspace_id: str                          # Workspace UUID where feedback is filed
    vote_type: str                             # Feedback rating type (e.g. 'thumbs_up', 'thumbs_down')
    category: Optional[str] = None             # Complaint category label (e.g. 'inaccurate', 'rude', 'bug')
    comment_text: Optional[str] = None         # Detailed comment text details
    created_by: Optional[str] = None           # Optional submitter ID (for logged-in users)

class FeedbackResolve(BaseModel):
    """
    Empty placeholder validation schema for resolution requests.
    """
    pass

class FeedbackVerify(BaseModel):
    """
    Validates payload options when verifying/closing resolved tickets.
    """
    is_satisfied: bool                         # User verification status flag (True/False)
    comment: Optional[str] = None              # Custom verification notes details


@router.get("/api/feedback/fix-db")
async def fix_db_constraint():
    """
    HTTP GET endpoint to fix database constraint issues.
    Utility helper for maintenance tasks.

    Parameters:
        None

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(500): Raised if database queries crash.
    """
    return await handle_fix_db_constraint()  # Route task execution to handlers layer


@router.post("/api/feedback")
async def submit_feedback(payload: FeedbackCreate):
    """
    HTTP POST endpoint to submit user feedback complaint tickets.
    Publicly accessible (no authentication required) so web visitors can submit votes.

    Parameters:
        payload (FeedbackCreate): The pydantic-validated request payload.

    Returns:
        dict: The created feedback details dictionary (includes ticket ID).

    Exceptions Raised:
        HTTPException(500): Raised if database writes fail.
    """
    return await handle_submit_feedback(payload.dict())  # Convert payload to dictionary and route to handler


@router.get("/api/feedback/open")
async def get_open_feedback(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing unresolved feedback tickets in a workspace.
    Requires user authentication.

    Parameters:
        workspace_id (str): Target Workspace UUID (Query Parameter).
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of open feedback ticket dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract User ID from JWT
    return await handle_get_open_feedback(workspace_id, user_id)  # Route task execution to handlers layer


@router.post("/api/feedback/{feedback_id}/resolve")
async def resolve_feedback(feedback_id: str, payload: FeedbackResolve, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint for team members to resolve feedback tickets.
    Requires user authentication.

    Parameters:
        feedback_id (str): Target Ticket UUID path parameter.
        payload (FeedbackResolve): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if ticket ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    return await handle_resolve_feedback(feedback_id, current_user["sub"])  # Route to handlers layer, passing ticket ID and resolver User ID


@router.get("/api/feedback/pending-verification")
async def get_pending_verification(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing resolved tickets waiting for verification.
    Requires user authentication.

    Parameters:
        workspace_id (str): Target Workspace UUID (Query Parameter).
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of pending verification ticket dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract User ID from JWT
    return await handle_get_pending_verification(workspace_id, user_id)  # Route task execution to handlers layer


@router.post("/api/feedback/{feedback_id}/verify")
async def verify_feedback(feedback_id: str, payload: FeedbackVerify, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint for users to verify/close tickets.
    Requires user authentication.

    Parameters:
        feedback_id (str): Target Ticket UUID path parameter.
        payload (FeedbackVerify): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if ticket ID not found.
        HTTPException(500): Raised if updates crash.
    """
    data = payload.dict()  # Convert Pydantic request structure to dictionary
    data["user_id"] = current_user["sub"]  # Inject user ID subject from JWT
    return await handle_verify_feedback(feedback_id, data)  # Route task execution to handlers layer
