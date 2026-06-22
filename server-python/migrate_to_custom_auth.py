import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("DATABASE_URL not found.")
    exit(1)

def migrate():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Creating public.users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                otp_secret TEXT,
                otp_expires_at TIMESTAMP WITH TIME ZONE,
                reset_token TEXT,
                reset_token_expires_at TIMESTAMP WITH TIME ZONE,
                totp_secret TEXT,
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
            );
        """)

        print("Migrating existing users from auth.users...")
        cur.execute("""
            INSERT INTO public.users (id, email, password_hash, is_verified)
            SELECT id, email, encrypted_password, true
            FROM auth.users
            ON CONFLICT (id) DO NOTHING;
        """)

        tables = [
            ("agents", "user_id"),
            ("chat_sessions", "user_id"),
            ("workspaces", "owner_id"),
            ("workspace_members", "user_id"),
            ("user_subscriptions", "user_id"),
            ("user_settings", "user_id")
        ]

        print("Updating foreign key constraints...")
        for table, col in tables:
            # We need to find the constraint name first
            cur.execute(f"""
                SELECT constraint_name 
                FROM information_schema.key_column_usage 
                WHERE table_name = '{table}' AND column_name = '{col}' AND table_schema = 'public';
            """)
            constraints = cur.fetchall()
            for (cname,) in constraints:
                # check if it points to auth.users
                cur.execute(f"""
                    SELECT confrelid::regclass 
                    FROM pg_constraint 
                    WHERE conname = '{cname}';
                """)
                res = cur.fetchone()
                if res and 'auth.users' in str(res[0]):
                    print(f"Dropping constraint {cname} on {table}")
                    cur.execute(f"ALTER TABLE public.{table} DROP CONSTRAINT {cname};")
                    
            print(f"Adding new constraint to {table}.{col} -> public.users(id)")
            cur.execute(f"""
                ALTER TABLE public.{table} 
                ADD CONSTRAINT {table}_{col}_fkey_custom 
                FOREIGN KEY ({col}) REFERENCES public.users(id) ON DELETE CASCADE;
            """)

        # Drop the trigger on auth.users
        cur.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
        
        conn.commit()
        print("Migration successful.")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
