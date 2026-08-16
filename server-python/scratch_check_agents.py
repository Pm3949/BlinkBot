import asyncio
from database import get_db_cursor_async
async def main():
    user_id = 'fd577a82-a4de-424b-8720-37af3eb52d0d'
    async with get_db_cursor_async(commit=False) as cursor:
        cursor.execute("SELECT COUNT(*) FROM agents WHERE user_id = %s;", (user_id,))
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT get_user_limit(%s, 'agents', 1);", (user_id,))
        limit = cursor.fetchone()[0]
        
        cursor.execute("SELECT (limits->>'agents') FROM user_subscriptions WHERE user_id = %s;", (user_id,))
        res = cursor.fetchone()
        raw_limit = res[0] if res else None
        
        print(f"User {user_id} has {count} agents. Limit from get_user_limit: {limit}. Raw limit in JSON: {raw_limit}")
asyncio.run(main())
