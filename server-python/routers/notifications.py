"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Alerts and Notifications
management actions in the RAGMate backend. It maps inbound HTTP REST requests and
WebSocket connections directly to the underlying business logic executors defined
inside the notification handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging libraries, FastAPI routing components (APIRouter, Query, WebSocket,
   WebSocketDisconnect, Depends), and JWT credentials authentication guards.
2. Routing Initialization: Declares the APIRouter for 'notifications' tag groupings.
3. HTTP and WebSocket Routes:
   - WS `/ws/notifications/{workspace_id}`: Real-time workspace alerts channel connection.
   - GET `/api/notifications`: REST HTTP endpoint listing unread workspace notifications.
   - PUT `/api/notifications/{notification_id}/read`: REST HTTP endpoint marking alerts as read.
"""

import logging  # Import python logging library
# Import FastAPI parameters for routing, queries, websocket connections, and depends injection
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import notification logic handlers and channel broadcast manager
from handlers.notification_handler import (
    notification_manager,
    handle_get_notifications,
    handle_mark_notification_read
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for notifications endpoints
router = APIRouter(tags=["notifications"])


@router.websocket("/ws/notifications/{workspace_id}")
async def notifications_ws(websocket: WebSocket, workspace_id: str):
    """
    HTTP WebSocket endpoint opening a real-time connection to stream
    workspace alerts and notification logs to active dashboard clients.

    Parameters:
        websocket (WebSocket): The raw FastAPI WebSocket connection context.
        workspace_id (str): Target Workspace UUID path parameter.

    Returns:
        None: Pipes raw sockets traffic directly to the notification manager.

    Exceptions Raised:
        WebSocketDisconnect: Safely handled when clients sever socket connections.
    """
    logger.info(f"🔌 WebSocket connection requested for notifications workspace: {workspace_id}")
    # Establish WebSocket protocol handshake and register listener
    await notification_manager.connect(websocket, workspace_id)
    logger.info(f"✅ WebSocket connected for notifications workspace: {workspace_id}")
    try:
        # Keep connection open, listening to client input events
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Remove connection from list on disconnect
        notification_manager.disconnect(websocket, workspace_id)
        logger.info(f"❌ WebSocket disconnected for notifications workspace: {workspace_id}")


@router.get("/api/notifications")
async def get_notifications(workspace_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint listing all unread notifications for a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID (Query Parameter).
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of unread notification dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if SQL database queries crash.
    """
    # Route execution to handlers layer
    return await handle_get_notifications(workspace_id)


@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP PUT endpoint to mark a specific notification alert as read.

    Parameters:
        notification_id (str): Target Notification UUID path parameter.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if notification ID not found.
        HTTPException(500): Raised if database updates crash.
    """
    # Route execution to handlers layer
    return await handle_mark_notification_read(notification_id)
