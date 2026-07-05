from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import json

async def check_workspace_member_exists(workspace_id: str, email: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (workspace_id, email),
        )
        return await run_in_threadpool(cursor.fetchone)

async def create_workspace_member(workspace_id: str, email: str, role: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, '{"agents": false, "database": false, "notes": false}'::jsonb)
            RETURNING id;
            """,
            (workspace_id, email, email.split("@")[0], role),
        )
        return (await run_in_threadpool(cursor.fetchone))[0]

async def get_user_subscription_limits(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT plan_tier, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def count_owned_workspaces(owner_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT COUNT(*) FROM workspaces WHERE owner_id = %s", 
            (owner_id,)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]

async def create_workspace(name: str, owner_id: str, email: str, user_name: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspaces (name, owner_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (name, owner_id)
        )
        workspace_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Admin', '{"agents": true, "database": true, "notes": true}'::jsonb)
            """,
            (workspace_id, owner_id, email, user_name)
        )
        return workspace_id

async def get_primary_workspace(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, owner_id
            FROM workspaces
            WHERE owner_id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def update_workspace_name(workspace_id: str, name: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE workspaces
            SET name = %s, updated_at = now()
            WHERE id = %s
            RETURNING id, name, owner_id;
            """,
            (name, workspace_id)
        )
        return await run_in_threadpool(cursor.fetchone)

async def get_user_workspaces(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT w.id, w.name, w.owner_id, wm.role, wm.permissions
            FROM workspace_members wm
            JOIN workspaces w ON wm.workspace_id = w.id
            WHERE wm.user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_workspace_members(workspace_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, user_id, email, name, role, permissions, created_at
            FROM workspace_members
            WHERE workspace_id = %s
            ORDER BY created_at ASC
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def update_member_role(member_id: str, role: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE workspace_members SET role = %s WHERE id = %s RETURNING id;",
            (role, member_id)
        )
        return await run_in_threadpool(cursor.fetchone)

async def update_member_permissions(member_id: str, permissions: dict):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE workspace_members SET permissions = %s::jsonb WHERE id = %s RETURNING id;",
            (json.dumps(permissions), member_id)
        )
        return await run_in_threadpool(cursor.fetchone)

async def remove_member(member_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM workspace_members WHERE id = %s RETURNING id;",
            (member_id,)
        )
        return await run_in_threadpool(cursor.fetchone)
