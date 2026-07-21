from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def create_demo_requests_table():
    async with get_db_cursor_async(commit=True) as cursor:
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
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_date TEXT")
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS scheduled_time TEXT")
        await run_in_threadpool(cursor.execute, "ALTER TABLE demo_requests ADD COLUMN IF NOT EXISTS meeting_link TEXT")

async def submit_demo_request(name: str, email: str, company: str, message: str):
    await create_demo_requests_table()
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
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE demo_requests SET status = %s WHERE id = %s RETURNING name, email",
            (status, request_id)
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_demo_request_contact(request_id: int):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT name, email FROM demo_requests WHERE id = %s",
            (request_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def schedule_demo_meeting(request_id: int, scheduled_date: str, scheduled_time: str, meeting_link: str):
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
