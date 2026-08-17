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
            """
            SELECT id, provider, api_key_required, base_url, is_active FROM system_ai_models WHERE id = 'openai/gpt-oss-120b'
            """
        )
        row = cursor.fetchone()
        if row:
            print(f"ID: {row[0]}")
            print(f"Provider: {row[1]}")
            print(f"Key Required: {row[2]}")
            print(f"Base URL: {row[3]}")
            print(f"Is Active: {row[4]}")
        else:
            print("Model not found")

if __name__ == "__main__":
    asyncio.run(main())
