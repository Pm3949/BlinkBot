import asyncio
import os
import sys

# Add server-python to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.database import get_db_cursor_async

async def main():
    print("Applying optimized indexes to PostgreSQL...")
    async with get_db_cursor_async(commit=True) as cursor:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
            ON chat_messages(session_id, created_at DESC);
        """)
        print("Applied index: idx_chat_messages_session_created")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_user_pinned 
            ON chat_sessions(workspace_id, user_id, pinned DESC, updated_at DESC);
        """)
        print("Applied index: idx_chat_sessions_workspace_user_pinned")
        print("All database indexes applied successfully!")

if __name__ == "__main__":
    asyncio.run(main())
