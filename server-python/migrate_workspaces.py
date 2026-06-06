import os
import psycopg2
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

# 1. Create the trigger function and trigger
sql = """
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
  new_workspace_id UUID;
  placeholder_count INT;
BEGIN
  -- Link any existing placeholder invites
  UPDATE public.workspace_members
  SET user_id = NEW.id,
      name = COALESCE(NEW.raw_user_meta_data->>'full_name', public.workspace_members.name)
  WHERE email = NEW.email AND user_id IS NULL;

  -- Create a default personal workspace
  INSERT INTO public.workspaces (name, owner_id)
  VALUES (
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1), 'New User') || '''s Workspace',
    NEW.id
  )
  RETURNING id INTO new_workspace_id;

  -- Add user as Admin to their personal workspace
  INSERT INTO public.workspace_members (workspace_id, user_id, email, name, role, permissions)
  VALUES (
    new_workspace_id,
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    'Admin',
    '{"agents": true, "database": true, "notes": true}'::jsonb
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
"""
cursor.execute(sql)
print("Added auth.users trigger for automatic workspace creation.")

# 2. Retroactively create workspaces for existing users who don't own any workspace
cursor.execute("""
    SELECT id, email, raw_user_meta_data->>'full_name' AS full_name 
    FROM auth.users u
    WHERE NOT EXISTS (
        SELECT 1 FROM public.workspaces w WHERE w.owner_id = u.id
    )
""")
users_without_workspace = cursor.fetchall()

for user_id, email, full_name in users_without_workspace:
    name_to_use = full_name or (email.split('@')[0] if email else 'User')
    workspace_name = f"{name_to_use}'s Workspace"
    
    # Create workspace
    cursor.execute("""
        INSERT INTO public.workspaces (name, owner_id)
        VALUES (%s, %s) RETURNING id
    """, (workspace_name, user_id))
    new_workspace_id = cursor.fetchone()[0]
    
    # Check if they are already in workspace_members without a user_id (placeholder via email)
    cursor.execute("UPDATE public.workspace_members SET user_id = %s WHERE email = %s AND user_id IS NULL", (user_id, email))
    
    # Add to their newly created workspace
    cursor.execute("""
        INSERT INTO public.workspace_members (workspace_id, user_id, email, name, role, permissions)
        VALUES (%s, %s, %s, %s, 'Admin', '{"agents": true, "database": true, "notes": true}'::jsonb)
    """, (new_workspace_id, user_id, email, name_to_use))
    print(f"Created default workspace for existing user: {email}")

conn.commit()
cursor.close()
conn.close()
print("Migration completed successfully.")
