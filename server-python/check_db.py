import sys
import os
sys.path.append('/home/mp3949/Documents/RAGMate/server-python')
from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'documents';
""")
print("DOCUMENTS TABLE:")
for row in cur.fetchall(): print(row)

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'document_embeddings';
""")
print("\nDOCUMENT_EMBEDDINGS TABLE:")
for row in cur.fetchall(): print(row)

conn.close()
Connect to the internet
