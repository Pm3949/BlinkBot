import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
conn.autocommit = True
cursor = conn.cursor()

try:
    print("Dropping old constraint...")
    cursor.execute("ALTER TABLE message_feedback DROP CONSTRAINT IF EXISTS message_feedback_status_check;")
    
    print("Adding new constraint...")
    cursor.execute("ALTER TABLE message_feedback ADD CONSTRAINT message_feedback_status_check CHECK (status IN ('open', 'resolved', 'pending_verification'));")
    print("Database updated successfully!")
except Exception as e:
    print("Error:", e)

cursor.close()
conn.close()
