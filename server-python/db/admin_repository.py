from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_super_admin_status(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT is_super_admin FROM users WHERE id = %s", (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_admin_stats():
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM users")
        total_users = (await run_in_threadpool(cursor.fetchone))[0]

        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM workspaces")
        total_workspaces = (await run_in_threadpool(cursor.fetchone))[0]

        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM agents")
        total_agents = (await run_in_threadpool(cursor.fetchone))[0]

        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM chatbots")
        total_chatbots = (await run_in_threadpool(cursor.fetchone))[0]

        await run_in_threadpool(cursor.execute, "SELECT COALESCE(SUM(file_size_bytes), 0) FROM documents")
        total_storage = (await run_in_threadpool(cursor.fetchone))[0] or 0
        total_storage_mb = total_storage / (1024 * 1024)

        return {
            "totalUsers": total_users,
            "totalWorkspaces": total_workspaces,
            "totalAgents": total_agents,
            "totalChatbots": total_chatbots,
            "totalStorageMB": round(total_storage_mb, 2),
        }

async def get_admin_users():
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT u.id, u.email, u.created_at, s.plan_tier, s.limits, u.is_super_admin
            FROM users u
            LEFT JOIN user_subscriptions s ON u.id = s.user_id
            ORDER BY u.created_at DESC
            """
        )
        return await run_in_threadpool(cursor.fetchall)

async def upsert_user_subscription(user_id: str, plan_tier: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_subscriptions (user_id, plan_tier)
            VALUES (%s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET plan_tier = EXCLUDED.plan_tier, updated_at = now()
            """,
            (user_id, plan_tier),
        )

async def update_user_super_admin(user_id: str, is_super_admin: bool):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE users SET is_super_admin = %s WHERE id = %s
            """,
            (is_super_admin, user_id)
        )

async def get_admin_workspaces():
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT 
                w.id, w.name, w.created_at, w.owner_id,
                u.email as owner_email,
                (SELECT COUNT(*) FROM workspace_members wm WHERE wm.workspace_id = w.id) as member_count
            FROM workspaces w
            LEFT JOIN users u ON w.owner_id = u.id
            ORDER BY w.created_at DESC
            """
        )
        return await run_in_threadpool(cursor.fetchall)
