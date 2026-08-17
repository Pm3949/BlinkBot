"""
================================================================================
AUTHENTICATION AND USER MANAGEMENT DATABASE REPOSITORY LAYER (auth_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) / repository layer for handling
user authentication, registration, onboarding (default workspaces), OTP (One-Time
Password) flows, and Multi-Factor/Two-Factor Authentication (2FA/TOTP). It handles
all interactions with the user profiles in the `public.users` table and their related settings.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: The custom asynchronous database context manager.
   - `run_in_threadpool`: The FastAPI utility used to invoke synchronous psycopg2
     database methods inside external threads to prevent event loop blocking.
   - `psycopg2.extras`: Imports special PostgreSQL adapter cursor types, such as
     `DictCursor` (which allows fetching rows as dictionary-like objects instead
     of plain tuples).

2. Repository Functions:
   - `create_default_workspace(...)`: Checks if a user has a workspace. If not, splits
     the email to formulate a workspace name, inserts the workspace, and binds the
     user as the 'Owner' with standard permissions.
   - `get_user_by_email(...)`: Fetches a user record by email, returning a DictRow.
   - `create_unverified_user(...)`: Inserts a verified/unverified user directly.
   - `verify_user(...)`: Updates a user's is_verified status to TRUE.
   - `create_user_with_otp(...)`: Creates a new user in unverified state and stores
     an OTP secret and expiry time.
   - `update_user_otp(...)`: Updates the stored OTP code and its expiration for password
     resets or registration confirmations.
   - `verify_user_and_clear_otp(...)`: Verifies user verification status and wipes OTP data.
   - `reset_user_password(...)`: Changes a user's password hash and clears OTP settings.
   - `get_user_settings(...)`: Retrieves two-factor verification statuses from the database.
   - `get_auth_user_email(...)`: Searches both supabase-auth schemas and legacy/local user tables.
   - `update_user_totp_secret(...)`: Saves the TOTP secret key for MFA.
   - `get_user_by_id(...)`: Fetches a user record by ID.
   - `enable_2fa(...)` / `disable_2fa(...)`: Toggles Multi-Factor Authentication.

DATABASE CONCURRENCY & DICT CURSORS:
- We execute block-based psycopg2 functions in a threadpool utilizing `run_in_threadpool`.
- Using `cursor_factory=psycopg2.extras.DictCursor` lets us access query column names directly
  as keys in the returned row objects (e.g., `row['email']` instead of index-based `row[1]`).
"""

from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import psycopg2.extras

async def create_default_workspace(user_id: str, email: str):
    """
    Creates a default workspace and registers the user as the owner.

    Purpose:
        Initializes a default sandbox workspace for a newly registered user if they
        don't already own one. Adds the user to the workspace members list with owner roles.

    Parameters:
        user_id (str): The unique database identifier of the user.
        email (str): The email address of the user, used to generate the workspace name.

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts a row in the `workspaces` table.
        - Inserts a row in the `workspace_members` table.
        - Commits all modifications (commit=True).

    Errors / Exceptions:
        - May raise database constraint errors or connection exceptions.
    """
    # Open database connection in a writable transaction (commit=True).
    async with get_db_cursor_async(commit=True) as cursor:
        # Check if the user already owns any workspaces.
        # This prevents duplicate default workspaces from being created if this function is called multiple times.
        await run_in_threadpool(cursor.execute, "SELECT id FROM workspaces WHERE owner_id = %s", (user_id,))
        # If fetchone returning a row is not None, the user already has a workspace, so exit early.
        if await run_in_threadpool(cursor.fetchone):
            return
            
        # Formulate a friendly workspace name from the prefix of their email address.
        # split('@')[0] extracts the username segment of an email (e.g., 'john.doe' from 'john.doe@example.com').
        workspace_name = f"{email.split('@')[0]}'s Workspace"
        # Insert the workspace record and fetch its new database UUID using RETURNING id.
        await run_in_threadpool(
            cursor.execute, 
            "INSERT INTO workspaces (name, owner_id) VALUES (%s, %s) RETURNING id", 
            (workspace_name, user_id)
        )
        # Fetch and unpack the workspace ID from the returned row.
        workspace_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Define standard privileges for the workspace owner in JSON format.
        permissions = '{"studio": true, "models": true}'
        # Register the user as the 'Owner' of the workspace in the membership table.
        # We explicitly cast the permissions string to jsonb using the `::jsonb` cast in PostgreSQL.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Owner', %s::jsonb)
            """, 
            (workspace_id, user_id, email, email.split('@')[0], permissions)
        )


async def get_user_by_email(email: str):
    """
    Retrieves a user's record from the public users table based on their email.

    Purpose:
        Retrieves user login parameters, passwords hashes, and OTP flags for verification check.

    Parameters:
        email (str): The email address to look up.

    Returns:
        DictRow | None: The user record dict-like object if found, or None if it does not exist.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open connection with commit=False (read-only). We specify cursor_factory=psycopg2.extras.DictCursor
    # so the returned record acts like a Python dictionary, mapping column names to row fields.
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT * FROM public.users WHERE email = %s", (email,))
        # Fetch and return the matching user row.
        return await run_in_threadpool(cursor.fetchone)


async def create_unverified_user(email: str, password_hash: str):
    """
    Inserts a pre-verified user record directly.

    Purpose:
        Creates a user record that is immediately marked as verified (is_verified = TRUE).
        Typically used in simple configurations or integrations that skip verification steps.

    Parameters:
        email (str): User's email address.
        password_hash (str): The hashed representation of the user's password.

    Returns:
        str: The generated database UUID of the new user.

    Side Effects / State Changes:
        - Writes a new row to the `public.users` table.
        - Commits change to the database.

    Errors / Exceptions:
        - May raise database integrity errors (e.g. duplicate email constraint).
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO public.users (email, password_hash, is_verified)
            VALUES (%s, %s, TRUE) RETURNING id
            """, 
            (email, password_hash)
        )
        # Fetch the row, unpack index 0, and cast the UUID to a standard Python string.
        return str((await run_in_threadpool(cursor.fetchone))[0])


async def verify_user(user_id: str):
    """
    Sets a user's verification status to true.

    Purpose:
        Manually validates a user account by updating the verification flag.

    Parameters:
        user_id (str): The unique database identifier of the user.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates the `is_verified` column in the database.
        - Commits change to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET is_verified = TRUE WHERE id = %s", (user_id,))


async def create_user_with_otp(email: str, password_hash: str, otp: str, otp_expiry):
    """
    Registers a new unverified user alongside an activation OTP.

    Purpose:
        Creates a user account that remains locked (is_verified = FALSE) until the user enters
        the correct registration OTP before it expires.

    Parameters:
        email (str): The user's email address.
        password_hash (str): Hashed password.
        otp (str): The OTP confirmation token.
        otp_expiry (datetime): Expiration date and time of the OTP.

    Returns:
        str/UUID: The generated user database ID.

    Side Effects / State Changes:
        - Inserts an unverified user record in the `public.users` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database integrity constraints.
    """
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
    """
    Updates or resets the OTP verification details for a user.

    Purpose:
        Updates user OTP codes, commonly used during password reset requests or resending email verification codes.

    Parameters:
        user_id (str): Unique database user identifier.
        otp (str): The new OTP token string.
        otp_expiry (datetime): The expiration time of the new OTP code.

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies OTP secret and expiry columns for the user.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute, 
            "UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", 
            (otp, otp_expiry, user_id)
        )


async def verify_user_and_clear_otp(user_id: str):
    """
    Completes OTP activation, marks user verified, and cleans up verification variables.

    Purpose:
        To be run when a user enters a valid OTP. Sets `is_verified` to TRUE and wipes the
        OTP fields to prevent token reuse.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        None.

    Side Effects / State Changes:
        - Sets user verification status and clears OTP variables.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute, 
            "UPDATE public.users SET is_verified = TRUE, otp_secret = NULL, otp_expires_at = NULL WHERE id = %s", 
            (user_id,)
        )


async def reset_user_password(user_id: str, new_password_hash: str):
    """
    Resets the user's password and clears active OTP resets.

    Purpose:
        Overwrites the old password hash with a new one and cleans up reset states.
        Also guarantees verification is active.

    Parameters:
        user_id (str): Unique database user identifier.
        new_password_hash (str): The newly computed password hash.

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies `password_hash`, clears OTP columns, verifies user.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
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
    """
    Retrieves user settings related to Multi-Factor Authentication.

    Purpose:
        Checks if the user has enabled 2FA and retrieves their secret keys for TOTP.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        DictRow | None: Dict-like settings containing `two_factor_enabled` and `totp_secret`,
                         or None if settings row doesn't exist.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT two_factor_enabled, totp_secret FROM user_settings WHERE user_id = %s", (user_id,))
        return await run_in_threadpool(cursor.fetchone)


async def get_auth_user_email(user_id: str):
    """
    Finds a user's email address by checking both Supabase auth schemas and custom local users tables.

    Purpose:
        Ensures compatibility with multiple auth setups (Supabase auth vs custom SQL table setups)
        by checking both namespaces.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        str | None: The user's email address, or None if the user ID matches neither schema.

    Side Effects / State Changes:
        - None. Read-only queries.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        # Check first in the Supabase schema `auth.users`
        await run_in_threadpool(cursor.execute, "SELECT email FROM auth.users WHERE id = %s", (user_id,))
        auth_user = await run_in_threadpool(cursor.fetchone)
        if auth_user:
            return auth_user['email']
            
        # Fall back to checking the custom local schema `public.users`
        await run_in_threadpool(cursor.execute, "SELECT email FROM public.users WHERE id = %s", (user_id,))
        legacy_user = await run_in_threadpool(cursor.fetchone)
        return legacy_user['email'] if legacy_user else None


async def update_user_totp_secret(user_id: str, secret: str, settings_exist: bool):
    """
    Updates the TOTP secret key for Multi-Factor Authentication.

    Purpose:
        Saves the security key inside both user_settings and public.users tables to sync authentication state.

    Parameters:
        user_id (str): Unique database user identifier.
        secret (str): The unencrypted/encoded setup token.
        settings_exist (bool): Flag indicating if a row already exists in `user_settings` for this user.

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts or updates records in `user_settings`.
        - Updates the `totp_secret` field in the `public.users` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # If settings_exist is False, we insert the settings row first.
        if not settings_exist:
            await run_in_threadpool(cursor.execute, "INSERT INTO user_settings (user_id, totp_secret) VALUES (%s, %s)", (user_id, secret))
        else:
            await run_in_threadpool(cursor.execute, "UPDATE user_settings SET totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        # Keep both tables synchronized.
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET totp_secret = %s WHERE id = %s", (secret, user_id))


async def get_user_by_id(user_id: str):
    """
    Retrieves user record fields from the database by user ID.

    Purpose:
        Fetches username, verification status, TOTP flag, etc. using user ID.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        DictRow | None: Dict-like user record, or None if not found.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False, cursor_factory=psycopg2.extras.DictCursor) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT * FROM public.users WHERE id = %s", (user_id,))
        return await run_in_threadpool(cursor.fetchone)


async def enable_2fa(user_id: str, secret: str, settings_exist: bool):
    """
    Activates Two-Factor Authentication for a user.

    Purpose:
        Switches two_factor_enabled flag to TRUE and saves the TOTP key in both settings and profile tables.

    Parameters:
        user_id (str): Unique database user identifier.
        secret (str): The validated TOTP verification secret.
        settings_exist (bool): Flag indicating if a row already exists in `user_settings`.

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies records in `user_settings` and `public.users` tables.
        - Commits modifications.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        if not settings_exist:
            await run_in_threadpool(cursor.execute, "INSERT INTO user_settings (user_id, two_factor_enabled, totp_secret) VALUES (%s, TRUE, %s)", (user_id, secret))
        else:
            await run_in_threadpool(cursor.execute, "UPDATE user_settings SET two_factor_enabled = TRUE, totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET two_factor_enabled = TRUE, totp_secret = %s WHERE id = %s", (secret, user_id))


async def disable_2fa(user_id: str):
    """
    Deactivates Two-Factor Authentication for a user.

    Purpose:
        Disables Multi-Factor login requirements and wipes the corresponding secrets to clean security context.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates verification configuration states and wipes secrets in settings and user profiles tables.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "UPDATE user_settings SET two_factor_enabled = FALSE, totp_secret = NULL WHERE user_id = %s", (user_id,))
        await run_in_threadpool(cursor.execute, "UPDATE public.users SET two_factor_enabled = FALSE, totp_secret = NULL WHERE id = %s", (user_id,))

