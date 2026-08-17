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

async def main():
    async with get_db_cursor_async(commit=False) as cursor:
        cursor.execute(
            "SELECT id, session_id, role, content, latency, created_at, steps FROM chat_messages WHERE id IN ('088edd09-76fd-475b-958b-a729cf6aa515', 'a2d6fd70-0847-4d46-b6b2-d2078daf7484')"
        )
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Session ID: {row[1]}")
            print(f"Role: {row[2]}")
            print(f"Content: {secure_unpack(row[3])}")
            print(f"Latency: {row[4]}")
            print(f"Created At: {row[5]}")
            print(f"Steps: {secure_unpack(row[6]) if row[6] else 'None'}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
