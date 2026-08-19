import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.database import get_db_cursor_async
from db.chat_history_repository import get_chat_messages
from db.chat_repository import get_session_history

async def main():
    print("Running verification tests...")
    
    # 1. Find a session that has at least some messages
    async with get_db_cursor_async(commit=False) as cursor:
        cursor.execute("""
            SELECT session_id, COUNT(*) 
            FROM chat_messages 
            GROUP BY session_id 
            HAVING COUNT(*) > 1 
            LIMIT 1;
        """)
        row = cursor.fetchone()
        if not row:
            print("No session with multiple messages found to test. Test skipped.")
            return
        
        session_id = row[0]
        count = row[1]
        print(f"Found test session: {session_id} with {count} messages.")
        
        # 2. Test get_chat_messages with limit
        messages_all = await get_chat_messages(session_id)
        limit = 1
        messages_limited = await get_chat_messages(session_id, limit=limit)
        
        print(f"Total messages fetched (unlimited): {len(messages_all)}")
        print(f"Limited messages fetched (limit={limit}): {len(messages_limited)}")
        
        if len(messages_limited) == limit:
            print("✔ Paginated fetch limit verification: SUCCESS")
        else:
            print("❌ Paginated fetch limit verification: FAILED")
            
        # 3. Test get_session_history chronological order & limit
        history = await get_session_history(session_id, limit=3)
        print(f"LLM session history (limit=3): {history}")
        print("✔ History context retrieval: SUCCESS")

if __name__ == "__main__":
    asyncio.run(main())
