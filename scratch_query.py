import asyncio
import os
import sys

# Add server-python to path
sys.path.append("/home/mp3949/Documents/RAGMate/server-python")

# Load environment variables
from dotenv import load_dotenv
load_dotenv("/home/mp3949/Documents/RAGMate/server-python/dev.env")

from core.database import get_db_cursor_async
from utils.data_vault import secure_unpack
from fastapi.concurrency import run_in_threadpool

async def main():
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, system_prompt FROM agents
            """
        )
        rows = await run_in_threadpool(cursor.fetchall)
        for r in rows:
            print(f"ID: {r[0]} | Name: {r[1]}")

if __name__ == "__main__":
    asyncio.run(main())
