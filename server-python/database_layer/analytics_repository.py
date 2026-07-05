from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_analytics_metrics(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM agents WHERE user_id = %s", (user_id,))
        total_agents = (await run_in_threadpool(cursor.fetchone))[0] or 0

        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) 
            FROM documents d JOIN agents a ON d.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        doc_stats = await run_in_threadpool(cursor.fetchone)
        total_docs = doc_stats[0] or 0
        total_storage_mb = (doc_stats[1] or 0) / (1024 * 1024)

        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(message_count), 0) FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        total_widget_msgs = (await run_in_threadpool(cursor.fetchone))[0] or 0
        
        return total_agents, total_docs, total_storage_mb, total_widget_msgs

async def get_analytics_series(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT date_trunc('day', m.created_at)::date AS day, count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND m.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        internal_series = await run_in_threadpool(cursor.fetchall)

        await run_in_threadpool(
            cursor.execute,
            """
            SELECT date_trunc('day', l.created_at)::date AS day, count(*) 
            FROM widget_message_logs l
            JOIN chatbots c ON l.chatbot_id = c.id
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s 
            AND l.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        widget_series = await run_in_threadpool(cursor.fetchall)
        
        return internal_series, widget_series

async def get_analytics_top_chatbots(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.settings->>'name' as name, c.message_count 
            FROM chatbots c JOIN agents a ON c.agent_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY c.message_count DESC LIMIT 5
            """,
            (user_id,),
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_analytics_recent_questions(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT m.content, m.created_at, a.name as agent_name 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            ORDER BY m.created_at DESC LIMIT 10
            """,
            (user_id,),
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_feedback_stats(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        # Get total upvotes and downvotes for agents owned by this user
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT 
                COUNT(*) FILTER (WHERE vote_type = 'up'),
                COUNT(*) FILTER (WHERE vote_type = 'down')
            FROM message_feedback f
            JOIN agents a ON f.agent_id = a.id
            WHERE a.user_id = %s AND f.created_at >= current_date - interval '30 days'
            """,
            (user_id,)
        )
        vote_counts = await run_in_threadpool(cursor.fetchone)
        up_votes = vote_counts[0] or 0
        down_votes = vote_counts[1] or 0

        # Get category distribution (ignoring null categories)
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT category, COUNT(*) as count
            FROM message_feedback f
            JOIN agents a ON f.agent_id = a.id
            WHERE a.user_id = %s AND f.category IS NOT NULL AND f.created_at >= current_date - interval '30 days'
            GROUP BY category
            ORDER BY count DESC
            """,
            (user_id,)
        )
        category_rows = await run_in_threadpool(cursor.fetchall)
        category_distribution = [{"name": r[0], "value": r[1]} for r in category_rows]

        return up_votes, down_votes, category_distribution
