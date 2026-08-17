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
BEGIN
    SELECT (limits->>limit_key)::INT INTO limit_val
    FROM user_subscriptions WHERE user_subscriptions.user_id = $1;

    IF limit_val IS NOT NULL THEN
        RETURN limit_val;
    END IF;

    RETURN default_val;
END;
$function$;
    """
    async with get_db_cursor_async(commit=True) as cursor:
        cursor.execute(sql)
        print("Updated get_user_limit function to strictly use limits column.")
asyncio.run(main())
