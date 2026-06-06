import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'completed';")
    conn.commit()
    print("Added 'status' column to documents table.")
except psycopg2.errors.DuplicateColumn:
    print("'status' column already exists.")
    conn.rollback()

cursor.close()
conn.close()
