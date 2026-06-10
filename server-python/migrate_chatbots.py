import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(".env.local")
load_dotenv(".env")
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("No DB_URL found")
    exit(1)

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

try:
    cursor.execute("""
    ALTER TABLE chatbots 
    ADD COLUMN IF NOT EXISTS allowed_domains TEXT,
    ADD COLUMN IF NOT EXISTS api_key TEXT UNIQUE;
    """)
    conn.commit()
    print("Successfully added columns to chatbots table.")
except Exception as e:
    conn.rollback()
    print("Error:", e)
finally:
    cursor.close()
    conn.close()
