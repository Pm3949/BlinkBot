import asyncio
import os
import sys

# Ensure server-python root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from utils.logger import get_db_logger

logger = get_db_logger("migrations")

async def main():
    migration_file = os.path.join(os.path.dirname(__file__), "migrations", "009_checkpointer_and_tokens.sql")
    with open(migration_file, "r") as f:
        sql = f.read()
    
    logger.info("Running migration 009...")
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, sql)
    logger.info("Migration 009 completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
