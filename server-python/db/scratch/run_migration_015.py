import asyncio
import os
import sys

# Ensure server root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def main():
    sql = """
    CREATE TABLE IF NOT EXISTS platform_expenses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        amount_inr NUMERIC(12, 2) NOT NULL,
        description TEXT NOT NULL,
        category VARCHAR(50) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    print("Running migration to create platform_expenses table...")
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, sql)
    print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
