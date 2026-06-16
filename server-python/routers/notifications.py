import logging
from fastapi import APIRouter, HTTPException, Query
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])

@router.get("/api/notifications")
async def get_notifications(workspace_id: str = Query(...)):
    """Fetch unread notifications for a workspace."""
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

@router.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
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
