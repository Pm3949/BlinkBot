import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("DATABASE_URL not found.")
    exit(1)

def migrate_super_admin():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Adding is_super_admin to public.users...")
        cur.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE;")
        
        print("Migrating is_super_admin data from user_subscriptions to public.users...")
        cur.execute("""
            UPDATE public.users 
            SET is_super_admin = s.is_super_admin 
            FROM user_subscriptions s 
            WHERE s.user_id = public.users.id;
        """)

        print("Dropping is_super_admin from user_subscriptions...")
        cur.execute("ALTER TABLE user_subscriptions DROP COLUMN IF EXISTS is_super_admin;")

        conn.commit()
        print("Super admin migration successful.")
    except Exception as e:
        conn.rollback()
        print(f"Error during super admin migration: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_super_admin()
