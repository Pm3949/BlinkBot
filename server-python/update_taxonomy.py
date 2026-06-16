import psycopg2

conn = psycopg2.connect("postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")
conn.autocommit = True
cursor = conn.cursor()

try:
    cursor.execute("""
        -- Convert ENUM to VARCHAR
        ALTER TABLE notifications ALTER COLUMN type TYPE VARCHAR(50);
        
        -- Drop the old ENUM
        DROP TYPE IF EXISTS notification_type;
    """)
    print("Taxonomy schema update successful!")
except Exception as e:
    print(f"Error: {e}")

