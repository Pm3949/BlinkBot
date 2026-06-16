import psycopg2

conn = psycopg2.connect("postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")
conn.autocommit = True
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE agents ADD COLUMN web_search_enabled BOOLEAN DEFAULT FALSE;")
    print("Column added successfully!")
except Exception as e:
    print(f"Skipped or error: {e}")
