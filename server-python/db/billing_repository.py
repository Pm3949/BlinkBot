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


async def get_wallet_balance(user_id: str) -> float:
    """
    Retrieves the current credit balance of the user's wallet.
    Defaults to 0.0 if no wallet is found.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT credit_balance FROM user_wallets WHERE user_id = %s",
            (user_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return float(row[0])
        return 0.0


async def get_wallet_details(user_id: str) -> dict:
    """
    Retrieves the full wallet configuration and balance.
    Creates a wallet if one doesn't exist.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_wallets (user_id, credit_balance, auto_recharge_enabled, recharge_threshold, recharge_amount_usd)
            VALUES (%s, 0.0000, FALSE, 10.0000, 20.00)
            ON CONFLICT (user_id) DO NOTHING;
            """,
            (user_id,)
        )
        await run_in_threadpool(
            cursor.execute,
            "SELECT credit_balance, auto_recharge_enabled, recharge_threshold, recharge_amount_usd FROM user_wallets WHERE user_id = %s",
            (user_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return {
                "credit_balance": float(row[0]),
                "auto_recharge_enabled": row[1],
                "recharge_threshold": float(row[2]),
                "recharge_amount_usd": float(row[3])
            }
        return {
            "credit_balance": 0.0,
            "auto_recharge_enabled": False,
            "recharge_threshold": 10.0,
            "recharge_amount_usd": 20.0
        }


async def deduct_wallet_balance_atomic(user_id: str, amount: float) -> bool:
    """
    Deducts the specified amount from the user's wallet atomically.
    Allows balance to go negative as per requirements.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE user_wallets
            SET credit_balance = credit_balance - %s,
                updated_at = timezone('utc'::text, now())
            WHERE user_id = %s;
            """,
            (amount, user_id)
        )
        return True


async def topup_wallet_credits(user_id: str, amount_credits: float) -> bool:
    """
    Adds credits to the user's wallet balance.
    Creates a wallet if one doesn't exist.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO user_wallets (user_id, credit_balance, updated_at)
            VALUES (%s, %s, timezone('utc'::text, now()))
            ON CONFLICT (user_id) DO UPDATE
            SET credit_balance = user_wallets.credit_balance + EXCLUDED.credit_balance,
                updated_at = timezone('utc'::text, now());
            """,
            (user_id, amount_credits)
        )
        return True


async def update_wallet_recharge_settings(user_id: str, enabled: bool, threshold: float, amount_usd: float) -> bool:
    """
    Updates the auto-recharge thresholds and toggles.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE user_wallets
            SET auto_recharge_enabled = %s,
                recharge_threshold = %s,
                recharge_amount_usd = %s,
                updated_at = timezone('utc'::text, now())
            WHERE user_id = %s;
            """,
            (enabled, threshold, amount_usd, user_id)
        )
        return True


async def create_credit_transaction(
    user_id: str,
    agent_id: str,
    amount_credits: float,
    transaction_type: str,
    model_used: str = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    invoice_id: str = None
) -> bool:
    """
    Creates a record of a credit transaction log.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Check if agent exists to satisfy foreign key (or set to None if deleted/not found)
        valid_agent_id = None
        if agent_id:
            await run_in_threadpool(
                cursor.execute,
                "SELECT 1 FROM agents WHERE id = %s",
                (agent_id,)
            )
            if await run_in_threadpool(cursor.fetchone):
                valid_agent_id = agent_id

        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO credit_transactions (user_id, agent_id, amount_credits, transaction_type, model_used, prompt_tokens, completion_tokens, invoice_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (user_id, valid_agent_id, amount_credits, transaction_type, model_used, prompt_tokens, completion_tokens, invoice_id)
        )
        return True


async def get_credit_transactions(user_id: str, limit: int = 50) -> list:
    """
    Retrieves the transaction logs list for a specific user.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, agent_id, amount_credits, transaction_type, model_used, prompt_tokens, completion_tokens, created_at, invoice_id
            FROM credit_transactions
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (user_id, limit)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": str(r[0]),
                "agent_id": str(r[1]) if r[1] else None,
                "amount_credits": float(r[2]),
                "transaction_type": r[3],
                "model_used": r[4],
                "prompt_tokens": r[5],
                "completion_tokens": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "invoice_id": str(r[8]) if r[8] else None
            }
            for r in rows
        ]


import json

async def create_invoice(user_id: str, invoice_number: str, amount_inr: float, description: str, invoice_metadata: dict) -> dict:
    """
    Creates and records a new invoice in the DB.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO invoices (user_id, invoice_number, amount_inr, description, invoice_metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, invoice_number, amount_inr, status, description, invoice_metadata, created_at, user_id, (SELECT email FROM users WHERE id = %s) as user_email;
            """,
            (user_id, invoice_number, amount_inr, description, json.dumps(invoice_metadata), user_id)
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": str(r[0]),
                "invoice_number": r[1],
                "amount_inr": float(r[2]),
                "status": r[3],
                "description": r[4],
                "invoice_metadata": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
                "created_at": r[6].isoformat() if r[6] else None,
                "user_id": str(r[7]),
                "user_email": r[8] or "Unknown User"
            }
        return None


async def get_user_invoices(user_id: str) -> list:
    """
    Fetches all billing invoices for a specific user ID.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, invoice_number, amount_inr, status, description, invoice_metadata, created_at
            FROM invoices
            WHERE user_id = %s
            ORDER BY created_at DESC;
            """,
            (user_id,)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": str(r[0]),
                "invoice_number": r[1],
                "amount_inr": float(r[2]),
                "status": r[3],
                "description": r[4],
                "invoice_metadata": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
                "created_at": r[6].isoformat() if r[6] else None
            }
            for r in rows
        ]


async def get_invoice_by_id(invoice_id: str) -> dict:
    """
    Retrieves a single invoice entry metadata details matching database ID.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT i.id, i.invoice_number, i.amount_inr, i.status, i.description, i.invoice_metadata, i.created_at, i.user_id, u.email
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.id = %s;
            """,
            (invoice_id,)
        )
        r = await run_in_threadpool(cursor.fetchone)
        if r:
            return {
                "id": str(r[0]),
                "invoice_number": r[1],
                "amount_inr": float(r[2]),
                "status": r[3],
                "description": r[4],
                "invoice_metadata": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
                "created_at": r[6].isoformat() if r[6] else None,
                "user_id": str(r[7]),
                "user_email": r[8] or "Unknown User"
            }
        return None



