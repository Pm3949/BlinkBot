"""
================================================================================
ADMINISTRATIVE DATABASE REPOSITORY LAYER (admin_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module serves as the Data Access Object (DAO) or repository layer specifically
for super-admin dashboard operations in the RAGMate backend. It acts as an
intermediary between the database (managed via PostgreSQL) and the administrative
routers/APIs (FastAPI).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: A custom asynchronous context manager (imported from
     `database.py`) that handles connecting to the database, fetching a database
     cursor, and automatically closing/committing/rolling back transactions.
   - `run_in_threadpool`: A FastAPI utility designed to run synchronous, blocking
     functions (like standard database driver executions) in an external thread pool
     so that they do not block FastAPI's single-threaded asynchronous event loop.

2. Repository Functions (Queries & Mutations):
   - `get_user_super_admin_status(user_id)`: Checks if a given user has super-admin
     privileges. Useful for role-based access control (RBAC).
   - `get_admin_stats()`: Gathers aggregate metrics (counts of users, workspaces,
     agents, chatbots, and total document storage size in MB) to display on the
     admin dashboard.
   - `get_admin_users()`: Fetches a listing of all registered users, their subscription
     tiers, limits, and super-admin flags, ordered chronologically.
   - `upsert_user_subscription(user_id, plan_tier)`: Inserts or updates (upserts)
     a subscription plan tier for a user.
   - `update_user_super_admin(user_id, is_super_admin)`: Toggles or sets a user's
     super-admin status.
   - `get_admin_workspaces()`: Fetches a listing of all workspaces, their owners,
     and membership counts.

CONCURRENCY AND DATABASE MOTIVATION:
Python's standard database adapters (like `psycopg2`) are blocking (synchronous).
If we run a blocking database query directly in an `async def` function, it will
block the entire event loop, stopping all other concurrent web requests.
To solve this, we wrap synchronous cursor methods (`cursor.execute`, `cursor.fetchone`,
and `cursor.fetchall`) with `run_in_threadpool`. This delegates the execution
to a background thread and returns an awaitable coroutine, keeping the application
highly concurrent and responsive.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_super_admin_status(user_id: str):
    """
    Retrieves the super-admin status flag for a specific user ID.

    Purpose:
        This function is used during authentication and authorization checks to
        verify whether a user has administrative control. It queries the `users`
        table for the `is_super_admin` boolean flag.

    Parameters:
        user_id (str): The unique identifier (UUID or string ID) of the user
                       whose admin status is being checked.

    Returns:
        bool | None: True if the user is a super-admin, False if they are a regular
                     user, or None if the user does not exist in the database.
                     Technically, `fetchone` returns a tuple (e.g., `(True,)`) or None,
                     which is later processed by caller or returned directly.

    Side Effects / State Changes:
        - None. This is a read-only query and does not modify database state.

    Errors / Exceptions:
        - May raise database connection errors or PostgreSQL exceptions if the
          database is unreachable or the schema is invalid.
    """
    # Use the async context manager `get_db_cursor_async` to obtain a database cursor.
    # We pass `commit=False` because this is a read-only SELECT query; there is no
    # data modification to commit to the database.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # We must execute the query inside a thread pool because the underlying database
        # driver's `execute` method is blocking. `run_in_threadpool` prevents this blocking
        # behavior from stalling our asynchronous event loop. We use a parameterized query
        # (`%s` placeholder with a tuple argument `(user_id,)`) to prevent SQL Injection attacks.
        await run_in_threadpool(
            cursor.execute,
            "SELECT is_super_admin FROM users WHERE id = %s", (user_id,)
        )
        
        # After executing the query, we fetch the first matching row.
        # Again, we use `run_in_threadpool` since `fetchone` is a blocking call.
        # This will return a tuple containing the requested columns, or `None` if no match.
        return await run_in_threadpool(cursor.fetchone)


async def get_admin_stats():
    """
    Compiles global administrative statistics across various database tables.

    Purpose:
        Gathers aggregate information (total users, workspaces, agents, chatbots,
        and total storage used by uploaded documents) to provide a high-level
        dashboard overview.

    Parameters:
        None.

    Returns:
        dict: A dictionary containing the following keys:
            - "totalUsers" (int): The total count of registered users.
            - "totalWorkspaces" (int): The total count of created workspaces.
            - "totalAgents" (int): The total count of configured AI agents.
            - "totalChatbots" (int): The total count of deployed chatbots.
            - "totalStorageMB" (float): The total size of all uploaded documents
                                        converted to Megabytes (MB), rounded to 2 decimal places.

    Side Effects / State Changes:
        - None. This function performs read-only analytical queries.

    Errors / Exceptions:
        - May raise database-related exceptions (e.g., connection issues).
    """
    # Acquire a read-only cursor (`commit=False`) since we are only querying counts and sums.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # --- Total Users Count ---
        # Run a COUNT query to get the total number of records in the `users` table.
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM users")
        # Fetch the single row result. Since COUNT(*) returns a single value in a tuple
        # (e.g., `(150,)`), we extract index `0` to get the integer value.
        total_users = (await run_in_threadpool(cursor.fetchone))[0]

        # --- Total Workspaces Count ---
        # Run a COUNT query to get the total number of records in the `workspaces` table.
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM workspaces")
        # Extract the count from the returned tuple.
        total_workspaces = (await run_in_threadpool(cursor.fetchone))[0]

        # --- Total Agents Count ---
        # Run a COUNT query to get the total number of records in the `agents` table.
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM agents")
        # Extract the count from the returned tuple.
        total_agents = (await run_in_threadpool(cursor.fetchone))[0]

        # --- Total Chatbots Count ---
        # Run a COUNT query to get the total number of records in the `chatbots` table.
        await run_in_threadpool(cursor.execute, "SELECT COUNT(*) FROM chatbots")
        # Extract the count from the returned tuple.
        total_chatbots = (await run_in_threadpool(cursor.fetchone))[0]

        # --- Total Storage Usage ---
        # Sum the `file_size_bytes` column from the `documents` table.
        # We use `COALESCE(SUM(...), 0)` to handle cases where there are no documents;
        # otherwise, SUM() on an empty table would return `NULL` (None in Python).
        # COALESCE returns the first non-null argument (0 in this case).
        await run_in_threadpool(cursor.execute, "SELECT COALESCE(SUM(file_size_bytes), 0) FROM documents")
        # Fetch the sum. If the database returned None (e.g. if COALESCE wasn't supported
        # or somehow bypassed), we fall back to `0` with the `or 0` operator.
        total_storage = (await run_in_threadpool(cursor.fetchone))[0] or 0
        # Convert bytes to Megabytes (MB).
        # 1 KB = 1024 Bytes, 1 MB = 1024 KB. Thus, divide by (1024 * 1024).
        total_storage_mb = total_storage / (1024 * 1024)

        # Construct and return the statistics payload with the storage rounded to 2 decimal places.
        return {
            "totalUsers": total_users,
            "totalWorkspaces": total_workspaces,
            "totalAgents": total_agents,
            "totalChatbots": total_chatbots,
            "totalStorageMB": round(total_storage_mb, 2),
        }


async def get_admin_users():
    """
    Retrieves all users along with their subscription details for administration management.

    Purpose:
        Provides the administrator list view with details about users, when they
        joined, their current subscription plan tiers, limits, and whether they
        are super-admins.

    Parameters:
        None.

    Returns:
        list of tuples: A list of user records. Each record tuple contains:
            - id (str): User ID.
            - email (str): User email address.
            - created_at (datetime): Timestamp when the user was created.
            - plan_tier (str | None): User's plan tier (e.g., 'free', 'pro').
            - limits (dict / json | None): Limit details configured for the user.
            - is_super_admin (bool): Boolean flag for super-admin status.
            The list is sorted in descending order of creation date (newest first).

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a transaction-less/read-only database connection.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # Execute the query in a separate thread.
        # We perform a LEFT JOIN from `users` (alias u) to `user_subscriptions` (alias s)
        # on the user's ID. A LEFT JOIN ensures that even if a user has no subscription record
        # in the subscription table, they will still appear in the results, with subscription
        # columns appearing as NULL (None).
        # Results are ordered by `created_at DESC` to show the most recently registered users first.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT u.id, u.email, u.created_at, s.plan_tier, s.limits, u.is_super_admin
            FROM users u
            LEFT JOIN user_subscriptions s ON u.id = s.user_id
            ORDER BY u.created_at DESC
            """
        )
        # Fetch all matched records. Since `fetchall` is blocking, we run it in the thread pool.
        return await run_in_threadpool(cursor.fetchall)


async def upsert_user_subscription(user_id: str, plan_tier: str):
    """
    Inserts a new user subscription record or updates an existing one if a conflict occurs.

    Purpose:
        This is an "upsert" (update or insert) operation. When assigning or changing
        a subscription plan for a user, we either create a new record in the
        `user_subscriptions` table or update the tier of their existing subscription.

    Parameters:
        user_id (str): The unique identifier of the user.
        plan_tier (str): The tier name to assign (e.g., "free", "hobby", "pro", "enterprise").

    Returns:
        None.

    Side Effects / State Changes:
        - Writes or updates a record in the `user_subscriptions` table.
        - Updates the `updated_at` column to the current timestamp on updates.
        - Because `commit=True` is used, the transaction is immediately committed
          to the database.

    Errors / Exceptions:
        - May raise database errors if the input parameters fail database constraint
          checks (e.g., invalid foreign key reference for `user_id`).
    """
    # We pass `commit=True` to the cursor context manager. This ensures that the
    # transaction is committed (saved permanently) to the database when the `with` block exits.
    # If an exception is raised within the block, it will automatically roll back.
    async with get_db_cursor_async(commit=True) as cursor:
        
        # Execute the INSERT statement.
        # The `ON CONFLICT (user_id)` clause handles the case where the user already has a subscription.
        # Since `user_id` is a primary or unique key in the `user_subscriptions` table, a duplicate
        # entry would normally trigger a constraint violation error.
        # Instead, `DO UPDATE SET` catches this conflict and updates the `plan_tier` to the
        # new value (`EXCLUDED.plan_tier` refers to the value we attempted to insert) and sets
        # the `updated_at` timestamp to the current time using the database's `now()` function.
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
    """
    Updates the super-admin status flag for a specific user.

    Purpose:
        Allows administrative promotion or demotion of a user account. Sets the
        `is_super_admin` flag to True or False.

    Parameters:
        user_id (str): The unique ID of the target user.
        is_super_admin (bool): The new super-admin status (True to grant, False to revoke).

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies the `is_super_admin` column in the `users` table for the specified user.
        - Commit is set to True, so this change is persistent.

    Errors / Exceptions:
        - May raise database errors if the user ID is invalid or the connection fails.
    """
    # Set `commit=True` because we are performing a database update.
    async with get_db_cursor_async(commit=True) as cursor:
        
        # Execute the UPDATE statement in a thread pool.
        # Updates the row in the `users` table matching the given `user_id` and sets
        # `is_super_admin` to the provided boolean value.
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE users SET is_super_admin = %s WHERE id = %s
            """,
            (is_super_admin, user_id)
        )


async def get_admin_workspaces():
    """
    Retrieves all workspaces along with their owners and member counts for admin dashboard monitoring.

    Purpose:
        Provides admins with overview statistics of all active workspaces.

    Parameters:
        None.

    Returns:
        list of tuples: A list of workspace records, where each record contains:
            - id (str): Workspace ID.
            - name (str): Workspace name.
            - created_at (datetime): Creation timestamp of the workspace.
            - owner_id (str): Owner's user ID.
            - owner_email (str | None): Owner's email address (retrieved via LEFT JOIN).
            - member_count (int): The total number of members in this workspace
                                  (retrieved via a correlated scalar subquery).
            Sorted in descending order of creation date (newest first).

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a read-only context manager connection (`commit=False`).
    async with get_db_cursor_async(commit=False) as cursor:
        
        # Execute the query in a thread pool.
        # This query performs a:
        # 1. LEFT JOIN with the `users` table to fetch the owner's email address matching the `owner_id`.
        # 2. Correlated subquery `(SELECT COUNT(*) FROM workspace_members wm WHERE wm.workspace_id = w.id)`
        #    to count the total number of members in the workspace, alias-ed as `member_count`.
        # The result is sorted chronologically by workspace creation (`created_at DESC`).
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
        # Fetch all matching workspaces synchronously inside the thread pool and return them.
        return await run_in_threadpool(cursor.fetchall)

