"""
================================================================================
DEMO REQUEST & PIPELINE CONTROLLER LAYER (demo.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for managing demo request leads.
It supports:
1. Public Lead Capture: Anyone can submit a demo request without logging in.
2. Pipeline Management: Super Admins can list leads, filter scheduled demos,
   and update lead statuses (e.g. 'contacted', 'scheduled', 'completed').
3. Scheduling Integration: Admins can assign dates, times, and meeting URLs
   (like Google Meet/Zoom links) to lead requests.

SECURITY DESIGN:
- The lead submission route `/api/demo-request` is public, enabling form submissions from public marketing sites.
- Administrative endpoints (listing, updating statuses, scheduling) are protected by the `get_current_user` JWT check,
  which verifies the caller's Super Admin status in `handlers/demo_handler.py`.
"""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

# Import the demo management handlers.
from handlers.demo_handler import (
    handle_submit_demo_request,
    handle_get_admin_demo_requests,
    handle_update_demo_request_status,
    handle_schedule_demo_meeting,
    handle_get_scheduled_demo_requests
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["demo"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class DemoRequest(BaseModel):
    """
    Validation schema for public lead form submissions.
    """
    name: str # Full name of the lead contact
    email: str # Email address
    company: str = "" # Optional organization name
    message: str = "" # Optional details or questions


class UpdateStatusRequest(BaseModel):
    """
    Validation schema for modifying lead pipeline statuses.
    """
    status: str # Target status value (e.g. 'contacted', 'completed')
    admin_action_password: str # Verification password to confirm admin identity


class ScheduleMeetingRequest(BaseModel):
    """
    Validation schema for scheduling demo calls.
    """
    date: str # Scheduled date (YYYY-MM-DD)
    time: str # Scheduled time (HH:MM)
    meeting_link: str # Video conference URL (Zoom, Google Meet, etc.)
    admin_action_password: str # Verification password to confirm admin identity


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.post("/api/demo-request")
async def submit_demo_request(req: DemoRequest):
    """
    Submits a new demo request lead.

    Purpose:
        Public endpoint used by marketing forms to capture sales leads.

    Parameters:
        req (DemoRequest): Pydantic body containing contact details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Writes a new lead row to the `demo_requests` table.

    Errors / Exceptions:
        - Raises 400 Bad Request if the input format is invalid.
    """
    # Register the lead request.
    return await handle_submit_demo_request(req.dict())


@router.get("/admin/demo-requests")
async def get_admin_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    Lists all demo requests in the lead pipeline.

    Purpose:
        Fetches the complete lead history for admin dashboards.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Registered demo request entries.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Retrieve requests using the handler.
    return await handle_get_admin_demo_requests(user_id)


@router.patch("/admin/demo-requests/{request_id}/status")
async def update_demo_request_status(request_id: int, req: UpdateStatusRequest, current_user: dict = Depends(get_current_user)):
    """
    Updates the pipeline status of a demo request lead.

    Purpose:
        Tracks lead progress (e.g., updating status to 'contacted').

    Parameters:
        request_id (int): The ID of the target lead request.
        req (UpdateStatusRequest): Target status and password verification details.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Updates the status column of the target row in `demo_requests`.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if verification fails or the status is invalid.
    """
    # Convert Pydantic fields to a dictionary.
    data = req.dict()
    # Inject the admin's user ID for verification checks.
    data["admin_user_id"] = current_user["sub"]
    # Update the status.
    return await handle_update_demo_request_status(request_id, data)


@router.post("/admin/demo-requests/{request_id}/schedule")
async def schedule_demo_meeting(request_id: int, req: ScheduleMeetingRequest, current_user: dict = Depends(get_current_user)):
    """
    Schedules a meeting for a demo request lead.

    Purpose:
        Links a scheduled date, time, and conference URL to the lead.

    Parameters:
        request_id (int): The ID of the target lead request.
        req (ScheduleMeetingRequest): Meeting date, time, link, and password verification.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates schedule columns and sets status to 'scheduled' in the `demo_requests` table.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if verification fails or details are invalid.
    """
    # Convert inputs to a dictionary.
    data = req.dict()
    # Inject the admin's ID.
    data["admin_user_id"] = current_user["sub"]
    # Schedule the meeting.
    return await handle_schedule_demo_meeting(request_id, data)


@router.get("/admin/demo-requests/scheduled")
async def get_scheduled_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    Lists leads with active scheduled meetings.

    Purpose:
        Fetches scheduled demos for calendar listings.

    Parameters:
        current_user (dict): JWT details.

    Returns:
        list of dict: Scheduled demo requests containing contact details and meeting links.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
    """
    # Extract the user's UUID.
    user_id = current_user["sub"]
    # Fetch scheduled demos using the handler.
    return await handle_get_scheduled_demo_requests(user_id)

