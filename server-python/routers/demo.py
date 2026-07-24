"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Client Demo Request and
Admin scheduling actions in the RAGMate backend. It maps incoming HTTP REST requests
directly to the underlying business logic executors defined inside the demo handler
modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging libraries, Pydantic schemas, FastAPI routers, and authentication guards.
2. Routing Initialization: Declares the APIRouter for 'demo' tag groupings.
3. Input Payload Validation Schemas:
   - `DemoRequest`: Validates JSON payloads submitted on the public landing page.
   - `UpdateStatusRequest`: Validates payload for modifying leads pipeline status (requires password).
   - `ScheduleMeetingRequest`: Validates payload when scheduling a call (requires password).
4. HTTP Routes:
   - POST `/api/demo-request`: Public endpoint to submit a booking form (no authentication required).
   - GET `/admin/demo-requests`: Lists all demo requests (requires admin login).
   - PATCH `/admin/demo-requests/{id}/status`: Moves a lead through status pipelines.
   - POST `/admin/demo-requests/{id}/schedule`: Assigns meeting times and sends invitations.
   - GET `/admin/demo-requests/scheduled`: Lists leads that have scheduled meetings.
"""

import logging  # Import python logging library
from pydantic import BaseModel  # Pydantic BaseModels for request validations
from fastapi import APIRouter, Depends  # FastAPI Router and Dependency Injection components
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import demo logic handlers
from handlers.demo_handler import (
    handle_submit_demo_request,
    handle_get_admin_demo_requests,
    handle_update_demo_request_status,
    handle_schedule_demo_meeting,
    handle_get_scheduled_demo_requests
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for demo endpoints
router = APIRouter(tags=["demo"])

class DemoRequest(BaseModel):
    """
    Validates payload options when submitting a booking demo form.
    """
    name: str                                  # Client name display
    email: str                                 # Client email address
    company: str = ""                          # Company name (optional)
    message: str = ""                          # Custom request details (optional)

class UpdateStatusRequest(BaseModel):
    """
    Validates payload options for updating a lead status pipeline.
    """
    status: str                                # Target status ('pending', 'scheduled', 'completed')
    admin_action_password: str                 # Admin action validation password

class ScheduleMeetingRequest(BaseModel):
    """
    Validates payload options when scheduling a demo call.
    """
    date: str                                  # Target meeting date
    time: str                                  # Target meeting time
    meeting_link: str                          # Target video call link
    admin_action_password: str                 # Admin action validation password


@router.post("/api/demo-request")
async def submit_demo_request(req: DemoRequest):
    """
    HTTP POST public endpoint to record demo requests from landing pages.
    Does not require user authentication.

    Parameters:
        req (DemoRequest): The pydantic-validated request payload.

    Returns:
        dict: Success status and created request ID.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database writes crash.
    """
    return await handle_submit_demo_request(req.dict())  # Convert to dictionary and route to handlers layer


@router.get("/admin/demo-requests")
async def get_admin_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing all registered demo requests.
    Restricted to Super Administrators.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing the list of requests.

    Exceptions Raised:
        HTTPException(401/403): Raised if credentials check fails.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract admin's User ID from JWT
    return await handle_get_admin_demo_requests(user_id)  # Route task execution to handlers layer


@router.patch("/admin/demo-requests/{request_id}/status")
async def update_demo_request_status(request_id: int, req: UpdateStatusRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP PATCH endpoint to update a lead status pipeline.
    Restricted to Super Administrators.

    Parameters:
        request_id (int): Target request ID path parameter.
        req (UpdateStatusRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401/403): Raised for authentication or permission failures.
        HTTPException(404): Raised if request ID not found.
        HTTPException(500): Raised if update transactions crash.
    """
    data = req.dict()  # Convert Pydantic request structure to dictionary
    data["admin_user_id"] = current_user["sub"]  # Inject the admin user ID for authorization checks
    return await handle_update_demo_request_status(request_id, data)  # Route to handlers layer


@router.post("/admin/demo-requests/{request_id}/schedule")
async def schedule_demo_meeting(request_id: int, req: ScheduleMeetingRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to schedule a video call for a demo request.
    Restricted to Super Administrators.

    Parameters:
        request_id (int): Target request ID path parameter.
        req (ScheduleMeetingRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401/403): Raised for authentication or permission failures.
        HTTPException(404): Raised if request ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    data = req.dict()  # Convert Pydantic request structure to dictionary
    data["admin_user_id"] = current_user["sub"]  # Inject the admin user ID for verification checks
    return await handle_schedule_demo_meeting(request_id, data)  # Route to handlers layer


@router.get("/admin/demo-requests/scheduled")
async def get_scheduled_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing all scheduled demo requests.
    Restricted to Super Administrators.

    Parameters:
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: A dictionary containing the list of scheduled requests.

    Exceptions Raised:
        HTTPException(401/403): Raised if credentials check fails.
        HTTPException(500): Raised if database queries fail.
    """
    user_id = current_user["sub"]  # Extract admin's User ID from JWT
    return await handle_get_scheduled_demo_requests(user_id)  # Route task execution to handlers layer
