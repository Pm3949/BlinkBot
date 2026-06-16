import psycopg2

conn = psycopg2.connect("postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")
conn.autocommit = True
cursor = conn.cursor()

sql = """
-- Add read_at column
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE;

-- Enable pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Unschedule if it exists to avoid duplicates
DO $$
BEGIN
    PERFORM cron.unschedule('cleanup-old-notifications');
EXCEPTION
    WHEN OTHERS THEN
        -- ignore if it doesn't exist
END $$;

-- Schedule job
SELECT cron.schedule(
  'cleanup-old-notifications', 
  '0 0 * * *', 
  $$ DELETE FROM notifications WHERE is_read = true AND read_at < now() - interval '7 days' $$
);
"""

try:
    cursor.execute(sql)
    print("Database auto-cleanup setup complete!")
except Exception as e:
    print(f"Error: {e}")

