import logging
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from core.auth import get_current_user

from handlers.notification_handler import (
    notification_manager,
    handle_get_notifications,
    handle_mark_notification_read
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


@router.websocket("/ws/notifications/{workspace_id}")
async def notifications_ws(websocket: WebSocket, workspace_id: str):
    """
    What it does: WebSocket endpoint for real-time dashboard notifications.
    Args:
        websocket: The WebSocket connection.
        workspace_id (str): The workspace ID.
    Returns: None.
    """
    logger.info(f"🔌 WebSocket connection requested for notifications workspace: {workspace_id}")
    await notification_manager.connect(websocket, workspace_id)
    logger.info(f"✅ WebSocket connected for notifications workspace: {workspace_id}")
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, workspace_id)
        logger.info(f"❌ WebSocket disconnected for notifications workspace: {workspace_id}")


@router.get("/api/notifications")
async def get_notifications(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to fetch unread notifications for a specific workspace.
    Args:
        workspace_id (str): The workspace ID.
    Returns: A list of notifications.
    """
    return await handle_get_notifications(workspace_id)


@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to mark a notification as read.
    Args:
        notification_id (str): The notification ID.
    Returns: A success message.
    """
    return await handle_mark_notification_read(notification_id)
