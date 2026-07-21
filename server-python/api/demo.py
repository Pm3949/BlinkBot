import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

from handlers.demo_handler import (
    handle_submit_demo_request,
    handle_get_admin_demo_requests,
    handle_update_demo_request_status,
    handle_schedule_demo_meeting,
    handle_get_scheduled_demo_requests
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demo"])

class DemoRequest(BaseModel):
    name: str
    email: str
    company: str = ""
    message: str = ""

class UpdateStatusRequest(BaseModel):
    status: str
    admin_action_password: str

class ScheduleMeetingRequest(BaseModel):
    date: str
    time: str
    meeting_link: str
    admin_action_password: str


@router.post("/api/demo-request")
async def submit_demo_request(req: DemoRequest):
    """
    What it does: HTTP endpoint called by the public landing page when someone fills out the 'Book a Demo' form.
    Args:
        req (DemoRequest): The demo request details.
    Returns: A success message.
    """
    return await handle_submit_demo_request(req.dict())

@router.get("/admin/demo-requests")
async def get_admin_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch the pipeline of all demo requests.
    Args:
        user_id (str): The user ID.
    Returns: A list of requests.
    """
    user_id = current_user["sub"]
    return await handle_get_admin_demo_requests(user_id)

@router.patch("/admin/demo-requests/{request_id}/status")
async def update_demo_request_status(request_id: int, req: UpdateStatusRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to move a lead through the pipeline.
    Args:
        request_id (int): The request ID.
        req (UpdateStatusRequest): The update payload.
    Returns: A success message.
    """
    data = req.dict()
    data["admin_user_id"] = current_user["sub"]
    return await handle_update_demo_request_status(request_id, data)

@router.post("/admin/demo-requests/{request_id}/schedule")
async def schedule_demo_meeting(request_id: int, req: ScheduleMeetingRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to manually assign a meeting link and time.
    Args:
        request_id (int): The request ID.
        req (ScheduleMeetingRequest): The schedule payload.
    Returns: A success message.
    """
    data = req.dict()
    data["admin_user_id"] = current_user["sub"]
    return await handle_schedule_demo_meeting(request_id, data)

@router.get("/admin/demo-requests/scheduled")
async def get_scheduled_demo_requests(current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch leads that have active scheduled meetings.
    Args:
        user_id (str): The user ID.
    Returns: A list of scheduled requests.
    """
    user_id = current_user["sub"]
    return await handle_get_scheduled_demo_requests(user_id)
