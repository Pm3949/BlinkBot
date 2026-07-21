import os
import asyncio
import logging
from pathlib import Path
from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import decrypt_data
from utils import get_user_limits

logger = logging.getLogger(__name__)

from handlers.websocket_handlers import upload_status_manager
from db import document_repository

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
        
        await document_repository.index_document_chunks(document_id, chunks, vectors)
        
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

        try:
            await document_repository.mark_document_failed(document_id)
        except Exception as dbe:
            logger.error(f"Failed to mark document as failed: {dbe}")

    finally:
        # Clean up the temporary unencrypted file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


async def resume_interrupted_uploads():
    logger.info("Checking for interrupted document uploads to resume...")
    try:
        rows = await document_repository.get_interrupted_uploads()
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
