import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

try:
    print("--- AGENT PROJECTS ---")
    cursor.execute("SELECT id, name FROM agent_projects;")
    projects = cursor.fetchall()
    for p in projects:
        print(p)
        
    print("\n--- AGENTS ---")
    cursor.execute("SELECT id, name, project_id FROM agents;")
    agents = cursor.fetchall()
    for a in agents:
        print(a)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    cursor.close()
    conn.close()
