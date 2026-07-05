import os
import asyncio
import logging
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect
from database import get_db_connection
from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import decrypt_data
from utils import get_user_limits

logger = logging.getLogger(__name__)

from handlers.websocket_handlers import upload_status_manager

async def async_background_ingestion(
    document_id: str,
    agent_id: str,
    filename: str,
    temp_path: str,
    strategy: str,
    embed_model: str,
    workspace_id: str,
    file_path: str = None,
):
    """
    What it does: Runs the heavy lifting of reading a document, breaking it into smaller pieces, creating vector embeddings for AI search, and saving everything to the database. It runs in the background so it doesn't freeze the app.
    Args:
        document_id (str): The unique ID of the document in the database.
        agent_id (str): The ID of the agent this document belongs to.
        filename (str): The name of the file being processed.
        temp_path (str): Where the temporary file is located on disk.
        strategy (str): How to break the text up (e.g. 'sentence' or 'paragraph').
        embed_model (str): Which AI model to use to create the embeddings.
        workspace_id (str): The ID of the workspace this is happening in.
        file_path (str, optional): The final permanent path of the file.
    Returns: None.
    """
    conn = None
    cursor = None
    try:
        logger.info(f"⚙️ Async background task started for doc: {filename} ({document_id})")

        # Step 1: Text extraction
        await upload_status_manager.send_status(agent_id, "processing", filename, "Extracting text content (running OCR fallback if needed)...", 0.1)
        raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, filename)

        if not raw_text or not raw_text.strip():
            raise ValueError("Document is empty or text extraction failed.")

        # Step 2: Chunking
        await upload_status_manager.send_status(agent_id, "chunking", filename, "Chunking text content...", 0.4)
        if strategy == "naive":
            chunks = await asyncio.to_thread(rag_engine.chunk_text_naive, raw_text)
        elif strategy == "paragraph":
            chunks = await asyncio.to_thread(rag_engine.chunk_text_paragraph, raw_text)
        else:
            chunks = await asyncio.to_thread(rag_engine.chunk_text_sentence, raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the uploaded content")

        # Step 3: Embeddings
        await upload_status_manager.send_status(agent_id, "embeddings", filename, "Generating embeddings...", 0.7)
        vectors = await asyncio.to_thread(rag_engine.vectorize, chunks, model_name=embed_model)

        # Step 4: Database Indexing
        await upload_status_manager.send_status(agent_id, "indexing", filename, "Saving chunks to database...", 0.9)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        from core.security import encrypt_key
        for text, vector in zip(chunks, vectors):
            encrypted_chunk = encrypt_key(text)
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, encrypted_chunk, str(vector)),
            )

        cursor.execute(
            "UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,)
        )
        conn.commit()
        
        await upload_status_manager.send_status(agent_id, "completed", filename, "Successfully processed document!", 1.0)
        logger.info(f"✅ Async background task completed for doc: {filename}")

        # Send Real-Time Workspace Notification
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=workspace_id,
                title="Document Processed Successfully",
                message=f"Document '{filename}' was processed and is ready for search.",
                notification_type="document_processed"
            )
        except Exception as ne:
            logger.error(f"Failed to create notification on success: {ne}")

    except Exception as e:
        logger.exception(f"Async background ingestion failed for doc id {document_id}")
        await upload_status_manager.send_status(agent_id, "failed", filename, f"Failed: {str(e)}", 0.0)
        
        # Send Failure Notification
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=workspace_id,
                title="Document Processing Failed",
                message=f"Document '{filename}' failed: {str(e)}",
                notification_type="document_failed"
            )
        except Exception as ne:
            logger.error(f"Failed to create notification on failure: {ne}")

        if conn and cursor:
            try:
                cursor.execute(
                    "UPDATE documents SET status = 'failed' WHERE id = %s",
                    (document_id,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        # Clean up the temporary unencrypted file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def resume_interrupted_uploads():
    """
    What it does: Looks through the database when the server starts up to find any document uploads that were interrupted (like if the server crashed) and starts them up again.
    Args: None.
    Returns: None.
    """
    logger.info("Checking for interrupted document uploads to resume...")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.id, d.agent_id, d.filename, a.chunk_strategy, a.embedding_model, a.workspace_id
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE d.status = 'processing'
            """
        )
        rows = cursor.fetchall()
        if not rows:
            logger.info("No interrupted uploads found.")
            return

        logger.info(f"Found {len(rows)} interrupted uploads. Resuming them...")
        for doc_id, agent_id, filename, strategy, embed_model, workspace_id in rows:
            file_path = UPLOAD_DIR / filename
            temp_path = str(file_path) + ".tmp"
            
            # Reconstruct temp unencrypted file from the permanent encrypted file if missing
            if not os.path.exists(temp_path) and file_path.exists():
                try:
                    with open(file_path, "rb") as f:
                        encrypted_data = f.read()
                    decrypted_data = decrypt_data(encrypted_data)
                    with open(temp_path, "wb") as f:
                        f.write(decrypted_data)
                    logger.info(f"Re-decrypted permanent file for {filename} to {temp_path}")
                except Exception as e:
                    logger.error(f"Failed to reconstruct temp file for {filename}: {e}")
                    continue

            # Resume background task asynchronously
            asyncio.create_task(
                async_background_ingestion(
                    document_id=doc_id,
                    agent_id=agent_id,
                    filename=filename,
                    temp_path=temp_path,
                    strategy=strategy or "sentence",
                    embed_model=embed_model or "text-embedding-3-small",
                    workspace_id=str(workspace_id),
                    file_path=str(file_path)
                )
            )
            logger.info(f"Resumed background ingestion task for: {filename}")
    except Exception as e:
        logger.error(f"Error during interrupted uploads recovery: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
