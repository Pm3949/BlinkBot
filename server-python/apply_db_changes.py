import sys
import os
sys.path.append('/home/mp3949/Documents/RAGMate/server-python')
from database import get_db_connection

def apply_db_changes():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Creating HNSW Index...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS hnsw_embedding_idx 
        ON document_embeddings 
        USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
    """)

    print("Creating match_documents RPC with threshold...")
    cur.execute("""
        CREATE OR REPLACE FUNCTION match_documents(
          query_embedding VECTOR(384),
          match_agent_id UUID,
          match_count INT DEFAULT 5,
          similarity_threshold FLOAT DEFAULT 0.3
        ) RETURNS TABLE (
          content TEXT,
          similarity FLOAT,
          embedding_json TEXT
        ) LANGUAGE plpgsql AS $$
        BEGIN
          RETURN QUERY
          SELECT
            de.content,
            1 - (de.embedding <=> query_embedding) AS similarity,
            de.embedding::text AS embedding_json
          FROM document_embeddings de
          JOIN documents d ON de.document_id = d.id
          WHERE d.agent_id = match_agent_id
            AND 1 - (de.embedding <=> query_embedding) > similarity_threshold
          ORDER BY de.embedding <=> query_embedding
          LIMIT match_count;
        END;
        $$;
    """)

    conn.commit()
    print("Database optimization applied successfully!")
    conn.close()

if __name__ == '__main__':
    apply_db_changes()
