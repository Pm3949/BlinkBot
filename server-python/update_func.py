import asyncio
from core.database import get_db_cursor_async
async def main():
    sql = """
CREATE OR REPLACE FUNCTION public.get_user_limit(user_id uuid, limit_key text, default_val integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    limit_val INT;
    tier TEXT;
BEGIN
    SELECT plan_tier, (limits->>limit_key)::INT INTO tier, limit_val
    FROM user_subscriptions WHERE user_subscriptions.user_id = $1;

    -- If a limit is explicitly set in the JSON column, prioritize it.
    IF limit_val IS NOT NULL THEN
        RETURN limit_val;
    END IF;

    -- Otherwise, fall back to tier defaults
    IF tier = 'Pro' THEN
        IF limit_key = 'agents' THEN RETURN 5; END IF;
        IF limit_key = 'chatbots' THEN RETURN 2; END IF;
    ELSIF tier = 'Enterprise' THEN
        IF limit_key = 'agents' THEN RETURN 20; END IF;
        IF limit_key = 'chatbots' THEN RETURN 10; END IF;
    ELSIF tier = 'Business' THEN
        IF limit_key = 'agents' THEN RETURN 999999; END IF;
        IF limit_key = 'chatbots' THEN RETURN 999999; END IF;
    END IF;

    RETURN default_val;
END;
$function$;
    """
    async with get_db_cursor_async(commit=True) as cursor:
        cursor.execute(sql)
        print("Updated get_user_limit function.")
asyncio.run(main())
