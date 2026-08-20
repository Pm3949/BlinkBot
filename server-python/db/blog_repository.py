from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def create_blog(title: str, content: str, summary: str = None, author: str = "BlinkBot Team", read_time: str = "5 min read", cover_image: str = None, is_published: bool = True):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO blogs (title, content, summary, author, read_time, cover_image, is_published)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, title, content, summary, author, read_time, cover_image, is_published, created_at
            """,
            (title, content, summary, author, read_time, cover_image, is_published)
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": str(r[0]),
                "title": r[1],
                "content": r[2],
                "summary": r[3],
                "author": r[4],
                "read_time": r[5],
                "cover_image": r[6],
                "is_published": r[7],
                "created_at": r[8].isoformat() if r[8] else None
            }
        return None

async def get_all_blogs(only_published: bool = True):
    async with get_db_cursor_async(commit=False) as cursor:
        if only_published:
            await run_in_threadpool(
                cursor.execute,
                "SELECT id, title, content, summary, author, read_time, cover_image, is_published, created_at FROM blogs WHERE is_published = TRUE ORDER BY created_at DESC"
            )
        else:
            await run_in_threadpool(
                cursor.execute,
                "SELECT id, title, content, summary, author, read_time, cover_image, is_published, created_at FROM blogs ORDER BY created_at DESC"
            )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "content": r[2],
                "summary": r[3],
                "author": r[4],
                "read_time": r[5],
                "cover_image": r[6],
                "is_published": r[7],
                "created_at": r[8].isoformat() if r[8] else None
            }
            for r in rows
        ]

async def get_blog_by_id(blog_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id, title, content, summary, author, read_time, cover_image, is_published, created_at FROM blogs WHERE id = %s",
            (blog_id,)
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": str(r[0]),
                "title": r[1],
                "content": r[2],
                "summary": r[3],
                "author": r[4],
                "read_time": r[5],
                "cover_image": r[6],
                "is_published": r[7],
                "created_at": r[8].isoformat() if r[8] else None
            }
        return None

async def update_blog(blog_id: str, title: str, content: str, summary: str = None, author: str = "BlinkBot Team", read_time: str = "5 min read", cover_image: str = None, is_published: bool = True):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE blogs
            SET title = %s, content = %s, summary = %s, author = %s, read_time = %s, cover_image = %s, is_published = %s
            WHERE id = %s
            RETURNING id, title, content, summary, author, read_time, cover_image, is_published, created_at
            """,
            (title, content, summary, author, read_time, cover_image, is_published, blog_id)
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": str(r[0]),
                "title": r[1],
                "content": r[2],
                "summary": r[3],
                "author": r[4],
                "read_time": r[5],
                "cover_image": r[6],
                "is_published": r[7],
                "created_at": r[8].isoformat() if r[8] else None
            }
        return None

async def delete_blog(blog_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM blogs WHERE id = %s RETURNING id",
            (blog_id,)
        )
        r = await run_in_threadpool(cursor.fetchone)
        return r is not None
