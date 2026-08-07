"""
================================================================================
WORKSPACE NOTIFICATIONS ROUTER LAYER (notifications.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for managing workspace notifications.
It supports:
1. Real-time Notifications: Provides a WebSocket endpoint (`/ws/notifications/{workspace_id}`)
   where clients connect to receive instant notifications (e.g. upload complete, team invites).
2. Historical Listings: Retrieves past notifications (read and unread) for a specific workspace.
3. Notification Acknowledgment: Marks notifications as read to update counts.

DATA FLOW & CONCURRENCY:
- Connections are grouped by `workspace_id` in `notification_manager` connection pools.
  When a workspace event occurs, the handler broadcasts the alert to all connected sockets.
- Database listings and update actions are protected by the `get_current_user` JWT check.
"""

import logging
from utils.logger import get_department_logger
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from core.auth import get_current_user

# Import the notification manager and database handlers.
from handlers.notification_handler import (
    notification_manager,
    handle_get_notifications,
    handle_mark_notification_read
)

# Initialize standard module logger.
logger = get_department_logger("system")

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(tags=["notifications"])


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.websocket("/ws/notifications/{workspace_id}")
async def notifications_ws(websocket: WebSocket, workspace_id: str):
    """
    Establishes a WebSocket connection for real-time workspace alerts.

    Purpose:
        Enables real-time, low-latency notification delivery to clients
        connected to a workspace.

    Parameters:
        websocket (WebSocket): The connection object.
        workspace_id (str): UUID of the target workspace.

    Returns:
        None.

    Side Effects / State Changes:
        - Upgrades connection to WebSocket.
        - Adds connection to the `notification_manager` pool.

    Errors / Exceptions:
        - Handles `WebSocketDisconnect` gracefully, cleaning up the connection pool.
    """
    logger.info(f"🔌 WebSocket connection requested for notifications workspace: {workspace_id}")
    # Register the connection.
    await notification_manager.connect(websocket, workspace_id)
    logger.info(f"✅ WebSocket connected for notifications workspace: {workspace_id}")
    try:
        # Keep the connection alive by waiting for client messages.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Disconnect and clean up from the connection pool.
        notification_manager.disconnect(websocket, workspace_id)
        logger.info(f"❌ WebSocket disconnected for notifications workspace: {workspace_id}")


@router.get("/api/notifications")
async def get_notifications(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    Retrieves unread notifications for a workspace.

    Parameters:
        workspace_id (str): UUID of the target workspace.
        current_user (dict): JWT details.

    Returns:
        list of dict: Unread notifications list.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Fetch notifications.
    return await handle_get_notifications(workspace_id)


@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """
    Marks a notification as read.

    Purpose:
        Removes the notification from the user's unread badge counts.

    Parameters:
        notification_id (str): UUID of the target notification.
        current_user (dict): JWT details.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the read flag and timestamp in the database.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the notification is not found.
    """
    # Update the notification status.
    return await handle_mark_notification_read(notification_id)

