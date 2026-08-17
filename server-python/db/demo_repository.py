"""
================================================================================
DEMO REQUEST AND MEETING DATABASE REPOSITORY LAYER (demo_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database tables and records for client-submitted demo requests
and meeting scheduling. It handles self-healing database table initialization
and schema migrations (creating columns dynamically if they do not exist) and provides
methods to insert, update, and fetch scheduling entries.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: The custom async database connection context manager.
   - `run_in_threadpool`: FastAPI utility that runs blocking database calls in a background thread pool.

2. Repository Functions:
   - `create_demo_requests_table()`: Creates the `demo_requests` table if it is missing
     and alters columns dynamically to handle schema updates safely.
   - `submit_demo_request(...)`: Automatically ensures the table is created, then inserts
     a user's inquiry, returning registration metadata.
   - `get_admin_demo_requests()`: Retrieves all inquiries sorted newest first for administrator review.
   - `update_demo_request_status(...)`: Updates statuses (e.g. pending, approved, canceled) and returns contacts.
   - `get_demo_request_contact(...)`: Queries contact name and email properties.
   - `schedule_demo_meeting(...)`: Sets status to 'processing' and logs dates, times, and meeting URLs.
   - `get_scheduled_demo_requests()`: Fetches meetings scheduled for future dates.

SCHEMA MIGRATIONS PATTERN:
- To allow easy setup on clean installations without manual migration scripts,
  `create_demo_requests_table()` is executed prior to demo submissions. It uses
  `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to ensure
  the schema is always up to date.
"""

from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def create_demo_requests_table():
    """
    Creates the demo requests table and executes database schema updates if necessary.

    Purpose:
        Initializes the schema for tracking customer demo requests. Safely adds meeting columns
        without losing existing table records.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Creates the `demo_requests` table in the database if it is missing.
        - Appends schema columns (`scheduled_date`, `scheduled_time`, `meeting_link`) if missing.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection in a write transaction.
    async with get_db_cursor_async(commit=True) as cursor:
        # Create core table structure if it does not exist.
        await run_in_threadpool(
            cursor.execute,
            """
            CREATE TABLE IF NOT EXISTS demo_requests (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT DEFAULT '',
                message TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        # Safely migrate older database schemas: add scheduling columns if they are not already present.
        # ADD COLUMN IF NOT EXISTS is a PostgreSQL 9.6+ feature preventing crash on duplicate columns.
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_date TEXT")
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_time TEXT")
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS meeting_link TEXT")


async def submit_demo_request(name: str, email: str, company: str, message: str):
    """
    Submits a new demo inquiry from the customer landing page.

    Purpose:
        Saves user inquiry metadata. Guarantees table schema initialization.

    Parameters:
        name (str): The customer's name.
        email (str): The customer's email address.
        company (str): The company name.
        message (str): A custom description message detailing customer goals.

    Returns:
        tuple: (id, created_at) tuple of the newly created database entry.

    Side Effects / State Changes:
        - Automatically creates/updates the database schema if needed.
        - Writes a new record to `demo_requests`.
        - Commits changes.

    Errors / Exceptions:
        - May raise database insertion errors.
    """
    # Self-heal schema before insertion to prevent errors.
    await create_demo_requests_table()
    # Open database connection to write details.
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO demo_requests (name, email, company, message)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (name, email, company, message)
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_admin_demo_requests():
    """
    Retrieves all demo inquiries for administrative management review.

    Purpose:
        Queries demo details for admin listing displays.

    Parameters:
        None.

    Returns:
        list of tuples: A list of all inquiry entries, sorted newest first (created_at DESC).

    Side Effects / State Changes:
        - None. Read-only query (commit=False).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, email, company, message, status, created_at, scheduled_date, scheduled_time, meeting_link
            FROM demo_requests
            ORDER BY created_at DESC
            """
        )
        return await run_in_threadpool(cursor.fetchall)


async def update_demo_request_status(request_id: int, status: str):
    """
    Updates the verification or processing status of an inquiry.

    Purpose:
        Sets new state flags (e.g., 'completed', 'cancelled') and fetches contact data
        to trigger email confirmations.

    Parameters:
        request_id (int): Database key ID of the target request.
        status (str): The new status flag.

    Returns:
        tuple | None: Returns (name, email) of the requester, or None.

    Side Effects / State Changes:
        - Modifies status column in `demo_requests`.
        - Commits updates.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Update status and return contact details.
        await run_in_threadpool(
            cursor.execute,
            "UPDATE demo_requests SET status = %s WHERE id = %s RETURNING name, email",
            (status, request_id)
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_demo_request_contact(request_id: int):
    """
    Retrieves contact email details for a request.

    Purpose:
        Fetches contact parameters to execute calendar invitations or emails.

    Parameters:
        request_id (int): Database key ID of the request.

    Returns:
        tuple | None: Returns (name, email), or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT name, email FROM demo_requests WHERE id = %s",
            (request_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def schedule_demo_meeting(request_id: int, scheduled_date: str, scheduled_time: str, meeting_link: str):
    """
    Links a scheduled meeting event to a demo request.

    Purpose:
        Sets the status to 'processing' and registers the meeting coordinates (date, time, link).

    Parameters:
        request_id (int): Database key ID of the target request.
        scheduled_date (str): The date string (e.g. '2026-08-01').
        scheduled_time (str): The time string (e.g. '14:00').
        meeting_link (str): The video conference URL.

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies `status`, `scheduled_date`, `scheduled_time`, and `meeting_link` variables in `demo_requests`.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE demo_requests 
            SET status = 'processing', scheduled_date = %s, scheduled_time = %s, meeting_link = %s 
            WHERE id = %s
            """, 
            (scheduled_date, scheduled_time, meeting_link, request_id)
        )


async def get_scheduled_demo_requests():
    """
    Retrieves all scheduled demo requests.

    Purpose:
        Fetches inquiries that have a valid scheduled date, sorting them chronologically to build calendar views.

    Parameters:
        None.

    Returns:
        list of tuples: A list of scheduled inquiries sorted by date ascending.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, email, company, status, scheduled_date, scheduled_time, meeting_link
            FROM demo_requests
            WHERE scheduled_date IS NOT NULL
            ORDER BY scheduled_date ASC
            """
        )
        return await run_in_threadpool(cursor.fetchall)

