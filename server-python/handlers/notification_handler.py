"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the business logic coordinator for managing workspace
alert notifications and real-time event broadcasts (via WebSockets) in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads local notification database access repositories, WebSocket manager interfaces,
   FastAPI HTTP exceptions, and logging controllers.
2. Logging: scopes a department logger to "system" activities.
3. Notification Creation & Broadcast (`create_notification`): Saves a new notification row in the database 
   and immediately pushes a WebSocket broadcast to all active client sockets connected to the workspace channel.
4. Notifications Query (`handle_get_notifications`): Fetches unread alert notifications.
5. Notification Read Marker (`handle_mark_notification_read`): Marks active alerts as read.
"""

import logging  # Import python logging library
from db import notification_repository  # Database access repository for notifications tables
from handlers.websocket_handlers import notification_manager  # WebSocket channel broadcast manager

# Logging utilities
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "system" activities
logger = get_department_logger("system")


async def create_notification(workspace_id: str, title: str, message: str, notification_type: str):
    """
    Creates a new notification record in the database and immediately broadcasts it 
    to all active clients connected to the workspace WebSocket channel.

    Parameters:
        workspace_id (str): The unique database UUID of the target workspace.
        title (str): Main summary heading of the notification alert.
        message (str): Detailed text content of the alert.
        notification_type (str): The category of notification (e.g., 'document_processed').

    Returns:
        None: Executes database writes and fires background WebSockets directly.

    Exceptions Handled:
        Catches and logs database insert and socket broadcast failures silently.
    """
    try:
        # Insert notification record in database repository
        row = await notification_repository.insert_notification(workspace_id, title, message, notification_type)
        if not row:
            return
            
        notification_id = row[0]
        # Format registration timestamp to ISO 8601 strings
        created_at = row[1].isoformat() if row[1] else None

        # Execute WebSocket broadcast to the workspace channel
        try:
            await notification_manager.broadcast(workspace_id, {
                "id": str(notification_id),
                "title": title,
                "message": message,
                "type": notification_type,
                "is_read": False,
                "created_at": created_at
            })
            logger.info(f"Created & broadcasted notification '{title}' to workspace {workspace_id}")
        except Exception as b_err:
            # Catch socket transmission failures separately so DB write success remains completed
            logger.error(f"Error broadcasting notification (DB write succeeded): {b_err}")

    except Exception as e:
        logger.error(f"Error creating notification: {e}")


from fastapi import HTTPException  # Import web exceptions to raise clean HTTP error status codes

async def handle_get_notifications(workspace_id: str):
    """
    Fetches the list of all unread notifications registered for a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID.

    Returns:
        list: A list of unread notification dictionaries.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database queries fail.
    """
    try:
        # Fetch unread notifications from database repository
        rows = await notification_repository.fetch_unread_notifications(workspace_id)
        notifications = []
        if rows:
            # Map raw tuples to clean dictionaries
            for row in rows:
                notifications.append({
                    "id": row[0],                                                # Notification UUID
                    "title": row[1],                                             # Title string
                    "message": row[2],                                           # Content details
                    "type": row[3],                                              # Alert type category
                    "is_read": row[4],                                           # Boolean read status flag
                    "created_at": row[5].isoformat() if row[5] else None,        # Creation ISO date string
                })
        return notifications
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


async def handle_mark_notification_read(notification_id: str):
    """
    Marks an active notification as read in the database.

    Parameters:
        notification_id (str): The unique database UUID identifying the notification.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(404): Raised if the notification ID is not found.
        HTTPException(500): Raised if database updates fail.
    """
    try:
        # Call database update repository scripts
        row = await notification_repository.mark_notification_read(notification_id)
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")
