from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def fix_feedback_db_constraint():
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "ALTER TABLE message_feedback DROP CONSTRAINT IF EXISTS message_feedback_status_check;")
        await run_in_threadpool(cursor.execute, "ALTER TABLE message_feedback ADD CONSTRAINT message_feedback_status_check CHECK (status IN ('open', 'resolved', 'pending_verification', 'closed'));")

async def submit_feedback(message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO message_feedback 
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]

async def check_workspace_role(workspace_id: str, user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id)
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_open_feedback(workspace_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT f.id, f.message_id, f.agent_id, f.vote_type, f.category, 
                   f.comment_text, f.created_at, f.created_by,
                   m.content as message_content, m.role,
                   a.name as agent_name
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.status = 'open'
            ORDER BY f.created_at DESC;
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_feedback_workspace_id(feedback_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT workspace_id FROM message_feedback WHERE id = %s", (feedback_id,))
        return await run_in_threadpool(cursor.fetchone)

async def mark_feedback_resolved(feedback_id: str, resolved_by: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE message_feedback
            SET status = 'pending_verification', resolved_at = now(), resolved_by = %s
            WHERE id = %s
            RETURNING id;
            """,
            (resolved_by, feedback_id)
        )

async def get_pending_verification(workspace_id: str, user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT f.id, f.message_id, f.agent_id, f.category, 
                   f.comment_text, f.created_at,
                   m.content as message_content,
                   a.name as agent_name,
                   (
                       SELECT content 
                       FROM chat_messages um 
                       WHERE um.session_id = m.session_id 
                         AND um.role = 'user' 
                         AND um.created_at < m.created_at 
                       ORDER BY created_at DESC 
                       LIMIT 1
                   ) as user_message
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.created_by = %s AND f.status = 'pending_verification'
            ORDER BY f.resolved_at DESC;
            """,
            (workspace_id, user_id)
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_feedback_for_verification(feedback_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT created_by, comment_text FROM message_feedback WHERE id = %s", (feedback_id,))
        return await run_in_threadpool(cursor.fetchone)

async def verify_feedback(feedback_id: str, is_satisfied: bool, comment: str, current_comment: str):
    async with get_db_cursor_async(commit=True) as cursor:
        if is_satisfied:
            await run_in_threadpool(cursor.execute, "UPDATE message_feedback SET status = 'closed' WHERE id = %s", (feedback_id,))
        else:
            new_comment = current_comment or ""
            if comment:
                new_comment = f"{new_comment}\\n\\n[User Unsatisfied]: {comment}"
                
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE message_feedback
                SET status = 'open', comment_text = %s
                WHERE id = %s
                """,
                (new_comment, feedback_id)
            )
