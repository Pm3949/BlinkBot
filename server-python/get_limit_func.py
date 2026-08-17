import asyncio
from core.database import get_db_cursor_async
async def main():
    async with get_db_cursor_async(commit=False) as cursor:
        cursor.execute("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'get_user_limit';")
        res = cursor.fetchone()
        print(res[0] if res else "Not found")
asyncio.run(main())
