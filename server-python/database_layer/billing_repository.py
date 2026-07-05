from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_user_subscription(user_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT plan_tier, billing_cycle, status, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def upsert_user_subscription(user_id: str, plan_tier: str, billing_cycle: str, limits_json: str):
    async with get_db_cursor_async(commit=True) as cursor:
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
