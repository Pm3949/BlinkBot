import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DB_URL:
        print("DATABASE_URL not found in environment.")
        return

    sql = """
    -- 1. AGENTS
    ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Users can view own agents" ON agents;
    DROP POLICY IF EXISTS "Users can create own agents" ON agents;
    DROP POLICY IF EXISTS "Users can delete own agents" ON agents;
    DROP POLICY IF EXISTS "Workspace members can access agents" ON agents;

    CREATE POLICY "Workspace members can access agents" ON agents
    FOR ALL TO authenticated
    USING (
      workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid())
      OR user_id = auth.uid()
    );

    -- 2. CHAT SESSIONS
    ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Workspace members can access chat sessions" ON chat_sessions;

    CREATE POLICY "Workspace members can access chat sessions" ON chat_sessions
    FOR ALL TO authenticated
    USING (
      workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid())
      OR user_id = auth.uid()
    );

    -- 3. CHAT MESSAGES
    ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Workspace members can access chat messages" ON chat_messages;

    CREATE POLICY "Workspace members can access chat messages" ON chat_messages
    FOR ALL TO authenticated
    USING (
      session_id IN (
        SELECT id FROM chat_sessions WHERE workspace_id IN (
          SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
        ) OR user_id = auth.uid()
      )
    );

    -- 4. CHATBOTS
    ALTER TABLE chatbots ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Workspace members can access chatbots" ON chatbots;

    CREATE POLICY "Workspace members can access chatbots" ON chatbots
    FOR ALL TO authenticated
    USING (
      agent_id IN (
        SELECT id FROM agents WHERE workspace_id IN (
          SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
        ) OR user_id = auth.uid()
      )
    );

    -- 5. DOCUMENTS
    ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Workspace members can access documents" ON documents;

    CREATE POLICY "Workspace members can access documents" ON documents
    FOR ALL TO authenticated
    USING (
      agent_id IN (
        SELECT id FROM agents WHERE workspace_id IN (
          SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()
        ) OR user_id = auth.uid()
      )
    );
    """

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        print("Executing RLS migration...")
        cursor.execute(sql)
        conn.commit()
        print("Migration successful: Enforced RLS on all tables.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
