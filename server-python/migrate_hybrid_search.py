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
    CREATE OR REPLACE FUNCTION match_documents_hybrid(
        query_text text,
        query_embedding vector(1536),
        match_agent_id uuid,
        match_count int DEFAULT 5,
        match_threshold float DEFAULT 0.3,
        rrf_k int DEFAULT 60
    )
    RETURNS TABLE (
        content text,
        similarity float
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        WITH vector_search AS (
            SELECT de.content,
                   RANK() OVER (ORDER BY de.embedding <=> query_embedding) as vector_rank,
                   1 - (de.embedding <=> query_embedding) as vector_sim
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = match_agent_id
        ),
        keyword_search AS (
            SELECT de.content,
                   RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', de.content), websearch_to_tsquery('english', query_text)) DESC) as keyword_rank
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = match_agent_id
              AND to_tsvector('english', de.content) @@ websearch_to_tsquery('english', query_text)
        ),
        combined AS (
            SELECT
                COALESCE(vs.content, ks.content) as doc_content,
                (COALESCE(1.0 / (rrf_k + vs.vector_rank), 0.0) +
                 COALESCE(1.0 / (rrf_k + ks.keyword_rank), 0.0))::float as rrf_score,
                vs.vector_sim
            FROM vector_search vs
            FULL OUTER JOIN keyword_search ks ON vs.content = ks.content
        )
        SELECT 
            doc_content as content,
            rrf_score as similarity
        FROM combined
        WHERE vector_sim IS NULL OR vector_sim >= match_threshold
        ORDER BY rrf_score DESC
        LIMIT match_count;
    END;
    $$;
    """

    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        print("Executing migration...")
        cursor.execute(sql)
        conn.commit()
        print("Migration successful: Created match_documents_hybrid function.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
