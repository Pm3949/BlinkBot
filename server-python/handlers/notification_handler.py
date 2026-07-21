import logging
from db import notification_repository
from handlers.websocket_handlers import notification_manager
logger = logging.getLogger(__name__)

async def create_notification(workspace_id: str, title: str, message: str, notification_type: str):
    """
    What it does: Creates a new notification in the database and instantly sends it to all users in that workspace.
    Args:
        workspace_id (str): The ID of the workspace getting the notification.
        title (str): The main heading of the alert.
        message (str): The detailed text of the alert.
        notification_type (str): The category of the alert (e.g. 'document_processed').
    Returns: None.
    """
    try:
        row = await notification_repository.insert_notification(workspace_id, title, message, notification_type)
        if not row:
            return
            
        notification_id = row[0]
        created_at = row[1].isoformat() if row[1] else None

        # Broadcast after successful DB commit
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
            logger.error(f"Error broadcasting notification (DB write succeeded): {b_err}")

    except Exception as e:
        logger.error(f"Error creating notification: {e}")

from fastapi import HTTPException

async def handle_get_notifications(workspace_id: str):
    """
    What it does: Fetches unread notifications for a specific workspace.
    Args:
        workspace_id (str): The ID of the workspace.
    Returns: A list of notifications.
    """
    try:
        rows = await notification_repository.fetch_unread_notifications(workspace_id)
        notifications = []
        if rows:
            for row in rows:
                notifications.append({
                    "id": row[0],
                    "title": row[1],
                    "message": row[2],
                    "type": row[3],
                    "is_read": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                })
        return notifications
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


async def handle_mark_notification_read(notification_id: str):
    """
    What it does: Marks a notification as read.
    Args:
        notification_id (str): The ID of the notification.
    Returns: A success message.
    """
    try:
        row = await notification_repository.mark_notification_read(notification_id)
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")
