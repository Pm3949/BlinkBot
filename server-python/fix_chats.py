import psycopg2

conn = psycopg2.connect("postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")
conn.autocommit = True
cursor = conn.cursor()

try:
    # Add workspace_id column
    cursor.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;")
    
    # Backfill workspace_id based on agent's workspace
    cursor.execute("""
        UPDATE chat_sessions cs
        SET workspace_id = a.workspace_id
        FROM agents a
        WHERE cs.agent_id = a.id AND cs.workspace_id IS NULL;
    """)
    print("Database updated successfully!")
except Exception as e:
    print(f"Error: {e}")

