import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()
cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('agents', 'documents', 'chatbots', 'chat_sessions', 'chat_messages');")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")
