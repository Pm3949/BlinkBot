import logging
from database import get_db_connection
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
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notifications (workspace_id, title, message, type)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at;
            """,
            (workspace_id, title, message, notification_type)
        )
        row = cursor.fetchone()
        conn.commit()
        
        notification_id = row[0]
        created_at = row[1].isoformat() if row[1] else None

        await notification_manager.broadcast(workspace_id, {
            "id": str(notification_id),
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": False,
            "created_at": created_at
        })
        logger.info(f"Created & broadcasted notification '{title}' to workspace {workspace_id}")
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

from fastapi import HTTPException

async def handle_get_notifications(workspace_id: str):
    """
    What it does: Fetches unread notifications for a specific workspace.
    Args:
        workspace_id (str): The ID of the workspace.
    Returns: A list of notifications.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, title, message, type, is_read, created_at
            FROM notifications
            WHERE workspace_id = %s AND is_read = false
            ORDER BY created_at DESC
            LIMIT 50;
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        notifications = []
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
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_mark_notification_read(notification_id: str):
    """
    What it does: Marks a notification as read.
    Args:
        notification_id (str): The ID of the notification.
    Returns: A success message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE notifications
            SET is_read = true, read_at = now()
            WHERE id = %s
            RETURNING id;
            """,
            (notification_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        conn.commit()
        return {"message": "Notification marked as read"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
