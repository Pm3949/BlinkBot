import psycopg2

conn = psycopg2.connect("postgresql://postgres.phqaaugotzmxjgjzhvhp:%40Mp39496759@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")
cursor = conn.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'chat_sessions';")
columns = [row[0] for row in cursor.fetchall()]
print(columns)
