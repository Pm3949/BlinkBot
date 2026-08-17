"""
================================================================================
WORKSPACE NOTIFICATION ALERTS DATABASE REPOSITORY LAYER (notification_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database interactions for user alert notifications within a
particular workspace (such as agent build alerts, billing status updates, or document indexing updates).
It provides methods to log new alerts, retrieve unread notifications with limits to optimize
payload sizes, and toggle unread flags to read state.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `logging`: standard logging utility.
   - `get_db_cursor_async` and `run_in_threadpool`: Core DB access interfaces.

2. Repository Functions:
   - `insert_notification(...)`: Inserts a notification record (commit=True), returning the
     generated identifier and created date.
   - `fetch_unread_notifications(workspace_id)`: Fetches up to 50 unread alerts (commit=False),
     sorted chronologically descending (newest first).
   - `mark_notification_read(notification_id)`: Updates the record status (commit=True) to read
     and registers a timestamp (`read_at = now()`), returning the verified notification ID.
"""

import logging
from utils.logger import get_department_logger
from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

# Initialize standard module-level logger.
logger = get_department_logger("system")

async def insert_notification(workspace_id: str, title: str, message: str, notification_type: str):
    """
    Inserts a new notification alert entry into the database.

    Purpose:
        Creates a workspace alert, which is shown to the user on their notifications feed.

    Parameters:
        workspace_id (str): The unique ID of the target workspace.
        title (str): Header text of the notification.
        message (str): Body detail text explaining the event.
        notification_type (str): Classification tag (e.g. 'info', 'warning', 'error', 'system').

    Returns:
        tuple: (id, created_at) containing the generated UUID and timestamp.

    Side Effects / State Changes:
        - Inserts a new row into the `notifications` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database insertion errors.
    """
    # Open connection in a write transaction (commit=True).
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
    """
    Retrieves up to 50 unread notifications for a workspace.

    Purpose:
        Fetches pending alerts for display. Implements limit rules (maximum 50) to prevent
        excessive data transfers.

    Parameters:
        workspace_id (str): Unique workspace identifier.

    Returns:
        list of tuples: Rows containing (id, title, message, type, is_read, created_at),
                        sorted newest first.

    Side Effects / State Changes:
        - None. Read-only (commit=False).

    Errors / Exceptions:
        - May raise database-related errors.
    """
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
    """
    Marks a single notification alert as read.

    Purpose:
        Updates a notification's status, tracking the read time (`read_at = now()`) for auditing.

    Parameters:
        notification_id (str): Unique notification ID.

    Returns:
        tuple | None: (id,) if found and updated, or None.

    Side Effects / State Changes:
        - Updates `is_read` to true and `read_at` to the current database time.
        - Commits update (commit=True).

    Errors / Exceptions:
        - May raise database exceptions.
    """
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

