import psycopg2
url = "postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"
conn = psycopg2.connect(url)
cursor = conn.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'workspace_members'")
print([row[0] for row in cursor.fetchall()])
