"""
================================================================================
DOCUMENT AND VECTOR EMBEDDING REPOSITORY LAYER (document_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database interactions for documents, raw file metadata, and
their corresponding vectorized chunks (embeddings). It acts as the backbone database
repository for Retrieval-Augmented Generation (RAG) pipelines, enabling storage monitoring,
chunk serialization, encryption-at-rest for indexed materials, and crash-recovery procedures
for interrupted file processing jobs.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: Context manager for transaction-managed DB sessions.
   - `run_in_threadpool`: Async executor for psycopg2 commands.

2. Repository Functions:
   - `get_agent_and_user_storage(agent_id)` / `get_agent_config_and_storage(agent_id)`:
     Fetches owner IDs, agent configuration models, and sums up total disk storage size
     (in bytes) across all documents indexed by the user to enforce billing restrictions.
   - `insert_document(...)`: Inserts metadata for an uploaded document and returns its ID.
   - `get_document_filename(doc_id)`: Fetches a document's filename from its ID.
   - `get_documents_for_agent(agent_id)`: Retrieves a listing of documents linked to an
     agent, joining and counting chunk records to show granularity.
   - `delete_document_data(doc_id)`: Wipes vector fragments and core document entries
     to clean space.
   - `index_document_chunks(...)`: Loops through text segments and vector floats, encrypting
     the text segments for privacy and writing the raw vectors to pgvector (`%s::vector`),
     finally toggling the status to 'completed'.
   - `mark_document_failed(document_id)`: Sets status to 'failed' when parsing crashes.
   - `get_interrupted_uploads()`: Queries documents stuck in 'processing' status to enable
     the backend server to resume index jobs on startup.
   - `get_document_by_id(doc_id)`: Fetches a document record.
   - `prepare_document_for_reindexing(...)`: Clears old vector chunks and resets status flags
     to trigger a fresh run of the ingestion worker.

SECURITY & VECTOR PRINCIPLES:
- Encryption-at-rest: Documents may contain private personal data. When index_document_chunks
  writes content to the database, it uses `core.security.encrypt_key` to encrypt text chunks
  so that they are stored securely.
- Vector insertion: Floating-point arrays (vectors) representing coordinates in the LLM's semantic
  space are formatted as text strings (e.g. `"[0.12, -0.4, ...]"`), then cast using `%s::vector`
  during execution.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_agent_and_user_storage(agent_id: str):
    """
    Fetches the user owner ID and the cumulative document storage size (in bytes) for that user.

    Purpose:
        Used during document uploads to evaluate whether the user has exceeded their plan's
        maximum allowed storage capacity limits.

    Parameters:
        agent_id (str): The unique UUID of the agent the document is being uploaded to.

    Returns:
        tuple: (user_id (str | None), current_storage (int))
               - user_id: The UUID of the user owning the agent.
               - current_storage: Aggregate size in bytes of all documents indexed by this user.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open connection with commit=False (read-only query).
    async with get_db_cursor_async(commit=False) as cursor:
        # Resolve user_id associated with the agent.
        await run_in_threadpool(cursor.execute, "SELECT user_id FROM agents WHERE id = %s", (agent_id,))
        agent_row = await run_in_threadpool(cursor.fetchone)
        # If the agent doesn't exist, return None for user_id and 0 for storage.
        if not agent_row:
            return None, 0
            
        user_id = agent_row[0]
        
        # Calculate the cumulative size of documents across all agents owned by this user.
        # INNER JOIN documents with agents to filter by the owner's user_id.
        # COALESCE ensures that if the user has no documents, the query returns 0 instead of Null.
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
    """
    Retrieves agent configuration metadata and the owner's total database storage metrics.

    Purpose:
        Combines configuration parameters (embedding models, parsing chunk strategies,
        workspace scope) and current storage aggregates into a single dictionary. Used
        by the file processing pipelines.

    Parameters:
        agent_id (str): The unique agent identifier.

    Returns:
        dict | None: Configuration properties and storage values dictionary, or None if the agent doesn't exist.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # Fetch the core configuration values from the agents profile.
        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, embedding_model, chunk_strategy, workspace_id FROM agents WHERE id = %s",
            (agent_id,)
        )
        agent_row = await run_in_threadpool(cursor.fetchone)
        # If agent record doesn't exist, exit immediately.
        if not agent_row:
            return None
            
        # Unpack the returned configuration tuple.
        user_id, embed_model, strategy, workspace_id = agent_row
        
        # Query total document storage bytes occupied by the owner.
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
        
        # Package metrics into a python dictionary representation.
        return {
            "user_id": user_id,
            "embed_model": embed_model,
            "strategy": strategy,
            "workspace_id": workspace_id,
            "current_storage": current_storage
        }


async def insert_document(agent_id: str, filename: str, status: str, file_size: int):
    """
    Creates a new document record in the database.

    Purpose:
        Initializes document tracking metadata before splitting and vectorizing starts.

    Parameters:
        agent_id (str): Associated agent UUID.
        filename (str): The name of the file.
        status (str): Initial state (e.g. 'processing', 'completed', 'failed').
        file_size (int): Size of the file in bytes.

    Returns:
        str/int: The generated document primary key ID (retrieved via RETURNING id).

    Side Effects / State Changes:
        - Inserts a row in the `documents` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database insertion errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, %s, %s) RETURNING id;",
            (agent_id, filename, status, file_size),
        )
        return (await run_in_threadpool(cursor.fetchone))[0]


async def get_document_filename(doc_id: str):
    """
    Retrieves the filename of a document from its ID.

    Purpose:
        Locates the physical file metadata, useful during storage cleaning or downloads.

    Parameters:
        doc_id (str): The unique database UUID of the document.

    Returns:
        str | None: The filename string if found, or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database connection errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT filename FROM documents WHERE id = %s", (doc_id,))
        row = await run_in_threadpool(cursor.fetchone)
        return row[0] if row else None


async def get_documents_for_agent(agent_id: str):
    """
    Retrieves all documents associated with an agent, along with their chunk counts.

    Purpose:
        Renders a files manager list on the frontend. Performs a LEFT JOIN with
        `document_embeddings` and aggregates chunk occurrences (`COUNT(e.id)`) to show
        how many vector blocks each file was divided into.

    Parameters:
        agent_id (str): Unique agent identifier.

    Returns:
        list of tuples: A list of documents, ordered by creation date descending (newest first).

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # Group by d.id to aggregate counts accurately.
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
    """
    Removes a document metadata record and all its associated vector embeddings.

    Purpose:
        Deletes a document from the system, freeing database storage. We manually clear
        vector chunks from `document_embeddings` before deleting the parent document row
        to ensure database referential integrity.

    Parameters:
        doc_id (str): Unique database identifier of the document to delete.

    Returns:
        str | None: The filename of the deleted document, useful for cleaning underlying storage.

    Side Effects / State Changes:
        - Deletes rows in `document_embeddings` and `documents` tables.
        - Commits deletions to the database.

    Errors / Exceptions:
        - May raise database reference errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Fetch the filename before deleting the rows so that the caller can clean the local file system.
        await run_in_threadpool(cursor.execute, "SELECT filename FROM documents WHERE id = %s", (doc_id,))
        doc = await run_in_threadpool(cursor.fetchone)
        filename = doc[0] if doc else None
        
        # Delete embedding chunks first.
        await run_in_threadpool(cursor.execute, "DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
        # Delete the master document metadata entry.
        await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE id = %s", (doc_id,))
        
        return filename


async def index_document_chunks(document_id: str, chunks: list, vectors: list):
    """
    Encrypts and saves document chunks and their high-dimensional vector embeddings.

    Purpose:
        Iterates over text segments (chunks) and their corresponding LLM floating-point vectors,
        encrypts the text segments for data privacy, and saves them in the database.
        Sets status to 'completed' after successful execution.

    Parameters:
        document_id (str): The parent document database identifier.
        chunks (list of str): List of plain text document splits.
        vectors (list of list of float): List of vector float arrays corresponding to the chunks.

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts multiple rows in `document_embeddings` table.
        - Updates the parent `documents` status to 'completed'.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Import dynamic credentials protection helper.
        from core.security import encrypt_key
        # Loop through chunks and vectors in lockstep using `zip`.
        for text, vector in zip(chunks, vectors):
            # Encrypt plain text split for database storage security.
            encrypted_chunk = encrypt_key(text)
            # Insert the chunk. We cast the vector string to standard pgvector type via `%s::vector`.
            await run_in_threadpool(
                cursor.execute,
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, encrypted_chunk, str(vector)),
            )

        # Set status to completed to indicate document is fully indexed and ready for queries.
        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,)
        )


async def mark_document_failed(document_id: str):
    """
    Updates a document status to 'failed'.

    Purpose:
        To be run if document parsing or vector generation fails, allowing user to see error states.

    Parameters:
        document_id (str): Unique document identifier.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates status column in the `documents` table.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET status = 'failed' WHERE id = %s",
            (document_id,),
        )


async def get_interrupted_uploads():
    """
    Retrieves documents that were interrupted during upload or processing.

    Purpose:
        Crash recovery system. Queries documents stuck in a 'processing' state.
        Allows workers to identify and resume interrupted document indexing tasks on server startup.

    Parameters:
        None.

    Returns:
        list of tuples: A list of records containing:
            - id (str): Document ID.
            - agent_id (str): Agent ID.
            - filename (str): Filename.
            - chunk_strategy (str): Splitting rules configured for the agent.
            - embedding_model (str): Embedding model parameter.
            - workspace_id (str): Scope workspace.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # INNER JOIN documents with agents to pull the target configurations needed to process the file.
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
    """
    Retrieves document attributes by its database key ID.

    Purpose:
        Fetches metadata fields for verification or details checking.

    Parameters:
        doc_id (str): Unique document identifier.

    Returns:
        tuple | None: Document metadata fields tuple, or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id, agent_id, filename, status, file_size_bytes FROM documents WHERE id = %s",
            (doc_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def prepare_document_for_reindexing(doc_id: str, new_filename: str, new_size: int):
    """
    Prepares a document for re-indexing, wiping old segments.

    Purpose:
        Resets indexing states (e.g. when updating a file). Deletes all old
        associated embeddings and updates the status to 'processing' to trigger the workers.

    Parameters:
        doc_id (str): The database identifier of the document.
        new_filename (str): The new filename.
        new_size (int): The new size of the file in bytes.

    Returns:
        None.

    Side Effects / State Changes:
        - Deletes all matching rows in `document_embeddings`.
        - Modifies filename, status, and size fields in `documents`.
        - Commits transaction (commit=True).

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Clear out any old chunk vector resources.
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM document_embeddings WHERE document_id = %s",
            (doc_id,)
        )
        # Update metadata and reset status to 'processing' to restart vector generation.
        await run_in_threadpool(
            cursor.execute,
            "UPDATE documents SET filename = %s, status = 'processing', file_size_bytes = %s WHERE id = %s",
            (new_filename, new_size, doc_id)
        )

