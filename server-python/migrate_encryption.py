import os
import sys
from dotenv import load_dotenv, set_key

# Ensure working directory is server-python
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load env from local .env
env_path = '.env'
load_dotenv(env_path)

# Generate and save ENCRYPTION_KEY if not present
encryption_key = os.getenv("ENCRYPTION_KEY")
if not encryption_key:
    from cryptography.fernet import Fernet
    new_key = Fernet.generate_key().decode('utf-8')
    print(f"Generating new ENCRYPTION_KEY and saving to {env_path}...")
    set_key(env_path, "ENCRYPTION_KEY", new_key)
    # Reload environment
    os.environ["ENCRYPTION_KEY"] = new_key
    encryption_key = new_key

from core.security import encrypt_key
from database import get_db_connection

def migrate_database():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Migrating user_settings table keys...")
        cursor.execute("SELECT user_id, openai_api_key, groq_api_key, gemini_api_key FROM user_settings;")
        settings_rows = cursor.fetchall()
        
        updated_settings = 0
        for user_id, openai, groq, gemini in settings_rows:
            needs_update = False
            
            # Helper to check if key needs encryption
            def process_key(k):
                nonlocal needs_update
                if k and not k.startswith("gAAAA"):
                    needs_update = True
                    return encrypt_key(k)
                return k

            new_openai = process_key(openai)
            new_groq = process_key(groq)
            new_gemini = process_key(gemini)
            
            if needs_update:
                cursor.execute(
                    """
                    UPDATE user_settings 
                    SET openai_api_key = %s, groq_api_key = %s, gemini_api_key = %s 
                    WHERE user_id = %s;
                    """,
                    (new_openai, new_groq, new_gemini, user_id)
                )
                updated_settings += 1

        print(f"Updated {updated_settings} settings records.")

        print("Migrating agents table keys...")
        cursor.execute("SELECT id, api_key FROM agents;")
        agents_rows = cursor.fetchall()
        
        updated_agents = 0
        for agent_id, api_key in agents_rows:
            if api_key and not api_key.startswith("gAAAA"):
                enc_key = encrypt_key(api_key)
                cursor.execute(
                    "UPDATE agents SET api_key = %s WHERE id = %s;",
                    (enc_key, agent_id)
                )
                updated_agents += 1
                
        print(f"Updated {updated_agents} agent records.")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error migrating database: {e}")
        sys.exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    migrate_database()
