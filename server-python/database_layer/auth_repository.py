from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import psycopg2.extras

async def create_default_workspace(user_id: str, email: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT id FROM workspaces WHERE owner_id = %s", (user_id,))
        if await run_in_threadpool(cursor.fetchone):
            return
            
        workspace_name = f"{email.split('@')[0]}'s Workspace"
        await run_in_threadpool(
            cursor.execute, 
            "INSERT INTO workspaces (name, owner_id) VALUES (%s, %s) RETURNING id", 
            (workspace_name, user_id)
        )
        workspace_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        permissions = '{"agents": true, "database": true, "notes": true}'
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Owner', %s::jsonb)
            """, 
            (workspace_id, user_id, email, email.split('@')[0], permissions)
        )

async def get_user_by_email(email: str):
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT * FROM public.users WHERE email = %s", (email,))
        return await run_in_threadpool(cursor.fetchone)

async def create_unverified_user(email: str, password_hash: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO public.users (email, password_hash, is_verified)
            VALUES (%s, %s, TRUE) RETURNING id
            """, 
            (email, password_hash)
        )
        return str((await run_in_threadpool(cursor.fetchone))[0])

async def verify_user(user_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET is_verified = TRUE WHERE id = %s", (user_id,))

async def create_user_with_otp(email: str, password_hash: str, otp: str, otp_expiry):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO public.users (email, password_hash, otp_secret, otp_expires_at, is_verified)
            VALUES (%s, %s, %s, %s, FALSE) RETURNING id
            """, 
            (email, password_hash, otp, otp_expiry)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]

async def update_user_otp(user_id: str, otp: str, otp_expiry):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute, 
            "UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", 
            (otp, otp_expiry, user_id)
        )

async def verify_user_and_clear_otp(user_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute, 
            "UPDATE public.users SET is_verified = TRUE, otp_secret = NULL, otp_expires_at = NULL WHERE id = %s", 
            (user_id,)
        )

async def reset_user_password(user_id: str, new_password_hash: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE public.users 
            SET password_hash = %s, otp_secret = NULL, otp_expires_at = NULL, is_verified = TRUE 
            WHERE id = %s
            """, 
            (new_password_hash, user_id)
        )

async def get_user_settings(user_id: str):
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT two_factor_enabled, totp_secret FROM user_settings WHERE user_id = %s", (user_id,))
        return await run_in_threadpool(cursor.fetchone)

async def get_auth_user_email(user_id: str):
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT email FROM auth.users WHERE id = %s", (user_id,))
        auth_user = await run_in_threadpool(cursor.fetchone)
        if auth_user:
            return auth_user['email']
            
        await run_in_threadpool(cursor.execute, "SELECT email FROM public.users WHERE id = %s", (user_id,))
        legacy_user = await run_in_threadpool(cursor.fetchone)
        return legacy_user['email'] if legacy_user else None

async def update_user_totp_secret(user_id: str, secret: str, settings_exist: bool):
    async with get_db_cursor_async(commit=True) as cursor:
        if not settings_exist:
            await run_in_threadpool(cursor.execute, "INSERT INTO user_settings (user_id, totp_secret) VALUES (%s, %s)", (user_id, secret))
        else:
            await run_in_threadpool(cursor.execute, "UPDATE user_settings SET totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET totp_secret = %s WHERE id = %s", (secret, user_id))

async def get_user_by_id(user_id: str):
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT * FROM public.users WHERE id = %s", (user_id,))
        return await run_in_threadpool(cursor.fetchone)

async def enable_2fa(user_id: str, secret: str, settings_exist: bool):
    async with get_db_cursor_async(commit=True) as cursor:
        if not settings_exist:
            await run_in_threadpool(cursor.execute, "INSERT INTO user_settings (user_id, two_factor_enabled, totp_secret) VALUES (%s, TRUE, %s)", (user_id, secret))
        else:
            await run_in_threadpool(cursor.execute, "UPDATE user_settings SET two_factor_enabled = TRUE, totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET two_factor_enabled = TRUE, totp_secret = %s WHERE id = %s", (secret, user_id))
