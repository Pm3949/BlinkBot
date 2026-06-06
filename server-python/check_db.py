import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

cursor.execute("SELECT id FROM agents")
agent_ids = [row[0] for row in cursor.fetchall()]

if agent_ids:
    format_strings = ','.join(['%s'] * len(agent_ids))
    
    # Delete orphaned document_embeddings
    cursor.execute(f"DELETE FROM document_embeddings WHERE document_id IN (SELECT id FROM documents WHERE agent_id NOT IN ({format_strings}))", tuple(agent_ids))
    
    # Delete orphaned documents
    cursor.execute(f"DELETE FROM documents WHERE agent_id NOT IN ({format_strings})", tuple(agent_ids))

    # Delete orphaned chat_messages
    cursor.execute(f"DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id NOT IN ({format_strings}))", tuple(agent_ids))

    # Delete orphaned chat_sessions
    cursor.execute(f"DELETE FROM chat_sessions WHERE agent_id NOT IN ({format_strings})", tuple(agent_ids))
else:
    cursor.execute("DELETE FROM document_embeddings")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM chat_messages")
    cursor.execute("DELETE FROM chat_sessions")

conn.commit()
print("Cleaned up orphaned records.")
conn.close()
