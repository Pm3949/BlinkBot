import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def migrate():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    print("Adding file_size_bytes to documents table...")
    cursor.execute("""
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;
    """)

    print("Adding message_count to chatbots table...")
    cursor.execute("""
        ALTER TABLE chatbots ADD COLUMN IF NOT EXISTS message_count BIGINT DEFAULT 0;
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration successful.")

if __name__ == "__main__":
    migrate()
