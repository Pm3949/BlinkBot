import logging
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

async def insert_notification(workspace_id: str, title: str, message: str, notification_type: str):
    """Inserts a notification into the database and returns the row."""
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO notifications (workspace_id, title, message, type)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at;
            """,
            (workspace_id, title, message, notification_type)
        )
        return await run_in_threadpool(cursor.fetchone)

async def fetch_unread_notifications(workspace_id: str):
    """Fetches up to 50 unread notifications for a workspace."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, title, message, type, is_read, created_at
            FROM notifications
            WHERE workspace_id = %s AND is_read = false
            ORDER BY created_at DESC
            LIMIT 50;
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def mark_notification_read(notification_id: str):
    """Marks a single notification as read and returns its id if found."""
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE notifications
            SET is_read = true, read_at = now()
            WHERE id = %s
            RETURNING id;
            """,
            (notification_id,)
        )
        return await run_in_threadpool(cursor.fetchone)
