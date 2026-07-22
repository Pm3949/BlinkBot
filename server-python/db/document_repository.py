from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_agent_and_user_storage(agent_id: str):
    """Fetches user_id and total current storage for that user."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT user_id FROM agents WHERE id = %s", (agent_id,))
        agent_row = await run_in_threadpool(cursor.fetchone)
        if not agent_row:
            return None, 0
            
        user_id = agent_row[0]
        
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        current_storage = (await run_in_threadpool(cursor.fetchone))[0] or 0
        
        return user_id, current_storage

async def get_agent_config_and_storage(agent_id: str):
    """Fetches agent config (user_id, embed, strategy, workspace) and total storage."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, embedding_model, chunk_strategy, workspace_id FROM agents WHERE id = %s",
            (agent_id,)
        )
        agent_row = await run_in_threadpool(cursor.fetchone)
        if not agent_row:
            return None
            
        user_id, embed_model, strategy, workspace_id = agent_row
        
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        current_storage = (await run_in_threadpool(cursor.fetchone))[0] or 0
        
        return {
            "user_id": user_id,
            "embed_model": embed_model,
            "strategy": strategy,
            "workspace_id": workspace_id,
            "current_storage": current_storage
        }

async def insert_document(agent_id: str, filename: str, status: str, file_size: int):
    """Inserts a new document row and returns the document ID."""
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, %s, %s) RETURNING id;",
            (agent_id, filename, status, file_size),
        )
        return (await run_in_threadpool(cursor.fetchone))[0]

async def get_document_filename(doc_id: str):
    """Gets the filename for a document."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT filename FROM documents WHERE id = %s", (doc_id,))
        row = await run_in_threadpool(cursor.fetchone)
        return row[0] if row else None

async def get_documents_for_agent(agent_id: str):
    """Gets all documents and their chunk counts for an agent."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT d.id, d.filename, d.status, d.created_at, d.file_size_bytes, COUNT(e.id) as chunk_count
            FROM documents d
            LEFT JOIN document_embeddings e ON d.id = e.document_id
            WHERE d.agent_id = %s 
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """,
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchall)

async def delete_document_data(doc_id: str):
    """Deletes a document and its embeddings from the DB, returning the filename."""
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT filename FROM documents WHERE id = %s", (doc_id,))
        doc = await run_in_threadpool(cursor.fetchone)
        filename = doc[0] if doc else None
        
        await run_in_threadpool(cursor.execute, "DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE id = %s", (doc_id,))
        
        return filename

async def index_document_chunks(document_id: str, chunks: list, vectors: list):
    async with get_db_cursor_async(commit=True) as cursor:
        from core.security import encrypt_key
        for text, vector in zip(chunks, vectors):
            encrypted_chunk = encrypt_key(text)
            await run_in_threadpool(
                cursor.execute,
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, encrypted_chunk, str(vector)),
            )

        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,)
        )

async def mark_document_failed(document_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET status = 'failed' WHERE id = %s",
            (document_id,),
        )

async def get_interrupted_uploads():
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT d.id, d.agent_id, d.filename, a.chunk_strategy, a.embedding_model, a.workspace_id
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE d.status = 'processing'
            """
        )
        return await run_in_threadpool(cursor.fetchall)

async def get_document_by_id(doc_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id, agent_id, filename, status, file_size_bytes FROM documents WHERE id = %s",
            (doc_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

async def prepare_document_for_reindexing(doc_id: str, new_filename: str, new_size: int):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM document_embeddings WHERE document_id = %s",
            (doc_id,)
        )
        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET filename = %s, status = 'processing', file_size_bytes = %s WHERE id = %s",
            (new_filename, new_size, doc_id)
        )
