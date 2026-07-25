"""
================================================================================
BILLING AND SUBSCRIPTION DATABASE REPOSITORY LAYER (billing_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) / repository layer for managing
billing-related information, subscription details, and resource limitations.
It provides functions to query and modify records in the `user_subscriptions` table in
the backend database (PostgreSQL).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: A custom asynchronous database context manager (imported from
     `database.py`) that handles connecting to the database, fetching a database
     cursor, and automatically closing/committing/rolling back transactions.
   - `run_in_threadpool`: A FastAPI utility used to run synchronous, blocking
     functions (like psycopg2 methods) in an external thread pool so that they
     do not block FastAPI's single-threaded asynchronous event loop.

2. Repository Functions:
   - `get_user_subscription(user_id)`: Fetches a user's subscription details, including
     their plan tier, billing cycle, status, and limits.
   - `upsert_user_subscription(user_id, plan_tier, billing_cycle, limits_json)`: Inserts
     or updates a user's subscription, handling conflicts on user_id gracefully by overwriting
     existing records and updating timestamps.

CONCURRENCY & TRANSACTION PHILOSOPHY:
- Asynchronous Event Loop safety: Python's standard database adapters run synchronously.
  Wrapping cursor executions in `run_in_threadpool` prevents database latency from freezing
  the web server's async requests handling.
- Transactions: Read-only statements are executed with `commit=False` for efficiency, while
  updates use `commit=True` to persist modifications immediately.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_subscription(user_id: str):
    """
    Retrieves the subscription details for a specific user ID.

    Purpose:
        Fetches subscription metadata (plan tier, billing cycle, status, and limits)
        to evaluate resource availability and authorize premium features.

    Parameters:
        user_id (str): The unique database identifier of the target user.

    Returns:
        tuple | None: A tuple containing (plan_tier, billing_cycle, status, limits) if the
                     user has a subscription record, or None if no record is found.

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database connection errors or query exceptions.
    """
    # Open database connection using our async context manager.
    # Set commit=False since this is a read-only query.
    async with get_db_cursor_async(commit=False) as cursor:
        # Execute SELECT statement inside a thread pool because psycopg2 cursor execution is blocking.
        # Use parameterized queries `%s` with tuple parameters to prevent SQL injection.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT plan_tier, billing_cycle, status, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (user_id,)
        )
        # Fetch the row containing subscription details asynchronously from the thread pool and return it.
        return await run_in_threadpool(cursor.fetchone)


async def upsert_user_subscription(user_id: str, plan_tier: str, billing_cycle: str, limits_json: str):
    """
    Inserts a new user subscription or updates an existing one if a conflict occurs on user_id.

    Purpose:
        Performs an "upsert" (update or insert) operation to sync a user's subscription
        tier, billing cycle, status, and limits details, keeping timestamps updated.

    Parameters:
        user_id (str): The unique database identifier of the user.
        plan_tier (str): The subscription plan tier name (e.g. 'free', 'pro', 'enterprise').
        billing_cycle (str): The billing recurrence interval (e.g. 'monthly', 'yearly').
        limits_json (str): A JSON-formatted string defining resource limits (e.g. document counts).

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts or modifies a row in the `user_subscriptions` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database exceptions.
    """
    # Open database connection with commit=True since we are modifying state.
    async with get_db_cursor_async(commit=True) as cursor:
        # Execute the upsert statement in a thread pool.
        # We explicitly cast `limits` using `%s::jsonb` to ensure PostgreSQL parses the string parameter as JSONB.
        # `ON CONFLICT (user_id)` catches unique constraint violations on user_id and switches to DO UPDATE.
        # `EXCLUDED.plan_tier` etc. references the values we attempted to insert in the VALUES block.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_subscriptions (user_id, plan_tier, billing_cycle, status, limits, updated_at)
            VALUES (%s, %s, %s, 'active', %s::jsonb, now())
            ON CONFLICT (user_id) DO UPDATE 
            SET plan_tier = EXCLUDED.plan_tier,
                billing_cycle = EXCLUDED.billing_cycle,
                status = 'active',
                limits = EXCLUDED.limits,
                updated_at = now();
            """,
            (user_id, plan_tier, billing_cycle, limits_json),
        )

