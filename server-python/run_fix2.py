import psycopg2
url = "postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

conn = psycopg2.connect(url)
conn.autocommit = True
cursor = conn.cursor()

try:
    print("Dropping old constraint...")
    cursor.execute("ALTER TABLE message_feedback DROP CONSTRAINT IF EXISTS message_feedback_status_check;")
    print("Adding new constraint...")
    cursor.execute("ALTER TABLE message_feedback ADD CONSTRAINT message_feedback_status_check CHECK (status IN ('open', 'resolved', 'pending_verification', 'closed'));")
    print("✅ Database updated successfully!")
except Exception as e:
    print("❌ Error:", e)

cursor.close()
conn.close()
