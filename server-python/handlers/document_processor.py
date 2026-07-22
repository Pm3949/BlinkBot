import os
import asyncio
from pathlib import Path
from core.dependencies import rag_engine, UPLOAD_DIR
from core.security import decrypt_data
from utils import get_user_limits

from utils.logger import get_department_logger

logger = get_department_logger("knowledge_base")

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
	logger.info(f"Starting async background ingestion task for document ID: {document_id} ('{filename}')")
	logger.debug(f"Parameters: strategy={strategy}, embed_model={embed_model}, workspace_id={workspace_id}, file_path={file_path}")
	try:
		# Step 1: Text extraction
		logger.debug("Step 1: Extracting plain text from target document file...")
		await upload_status_manager.send_status(agent_id, "processing", filename, "Extracting text content (running OCR fallback if needed)...", 0.1)
		raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, filename)
		
		if not raw_text or not raw_text.strip():
			logger.error("Text extraction returned an empty payload.")
			raise ValueError("Document is empty or text extraction failed.")
		
		logger.debug(f"Successfully extracted {len(raw_text)} characters of raw text.")

		# Step 2: Chunking
		logger.debug(f"Step 2: Partitioning text using '{strategy}' chunking strategy...")
		await upload_status_manager.send_status(agent_id, "chunking", filename, "Chunking text content...", 0.4)
		if strategy == "naive":
			chunks = await asyncio.to_thread(rag_engine.chunk_text_naive, raw_text)
		elif strategy == "paragraph":
			chunks = await asyncio.to_thread(rag_engine.chunk_text_paragraph, raw_text)
		else:
			chunks = await asyncio.to_thread(rag_engine.chunk_text_sentence, raw_text)

		if not chunks:
			logger.error("Chunking algorithm generated zero chunks.")
			raise ValueError("No chunks were produced from the uploaded content")
		
		logger.debug(f"Successfully partitioned text into {len(chunks)} chunks.")

		# Step 3: Embeddings
		logger.debug(f"Step 3: Vectorizing {len(chunks)} text chunks using embedding model '{embed_model}'...")
		await upload_status_manager.send_status(agent_id, "embeddings", filename, "Generating embeddings...", 0.7)
		vectors = await asyncio.to_thread(rag_engine.vectorize, chunks, model_name=embed_model)
		logger.debug(f"Successfully generated vectors. Output count: {len(vectors)}")

		# Step 4: Database Indexing
		logger.debug(f"Step 4: Inserting {len(chunks)} vectors and chunks into vector database...")
		await upload_status_manager.send_status(agent_id, "indexing", filename, "Saving chunks to database...", 0.9)
		await document_repository.index_document_chunks(document_id, chunks, vectors)
		logger.debug("Successfully committed all document vectors to PostgreSQL.")

		await upload_status_manager.send_status(agent_id, "completed", filename, "Successfully processed document!", 1.0)
		logger.info(f"✅ Ingestion task completed successfully for doc: {filename}")

		# Send Real-Time Workspace Notification
		logger.debug("Sending real-time workspace notification...")
		try:
			from handlers.notification_handler import create_notification
			await create_notification(
				workspace_id=workspace_id,
				title="Document Processed Successfully",
				message=f"Document '{filename}' was processed and is ready for search.",
				notification_type="document_processed"
			)
			logger.info(f"Broadcasted success notification for document '{filename}'.")
		except Exception as ne:
			logger.error(f"Failed to create notification on success: {str(ne)}", exc_info=True)

	except Exception as e:
		logger.error(f"Async background ingestion failed for doc ID {document_id}: {str(e)}", exc_info=True)
		await upload_status_manager.send_status(agent_id, "failed", filename, f"Failed: {str(e)}", 0.0)
		
		# Send Failure Notification
		logger.debug("Sending workspace failure notification...")
		try:
			from handlers.notification_handler import create_notification
			await create_notification(
				workspace_id=workspace_id,
				title="Document Processing Failed",
				message=f"Document '{filename}' failed: {str(e)}",
				notification_type="document_failed"
			)
		except Exception as ne:
			logger.error(f"Failed to create notification on failure: {str(ne)}", exc_info=True)

		try:
			logger.debug(f"Marking document status as 'failed' in database for doc ID: {document_id}")
			await document_repository.mark_document_failed(document_id)
		except Exception as dbe:
			logger.error(f"Failed to mark document as failed in database: {str(dbe)}", exc_info=True)

	finally:
		# Clean up the temporary unencrypted file
		if temp_path and os.path.exists(temp_path):
			logger.debug(f"Cleaning up temporary file: {temp_path}")
			os.remove(temp_path)


async def resume_interrupted_uploads():
	logger.info("Scanning database to check for interrupted document uploads that need to resume...")
	try:
		rows = await document_repository.get_interrupted_uploads()
		if not rows:
			logger.info("No interrupted uploads found.")
			return

		logger.info(f"Found {len(rows)} interrupted document uploads. Resuming execution...")
		for doc_id, agent_id, filename, strategy, embed_model, workspace_id in rows:
			file_path = UPLOAD_DIR / filename
			temp_path = str(file_path) + ".tmp"
			
			logger.debug(f"Processing interrupted document ID: {doc_id} ('{filename}')")
			
			# Reconstruct temp unencrypted file from the permanent encrypted file if missing
			if not os.path.exists(temp_path) and file_path.exists():
				try:
					logger.debug(f"Temporary file missing. Decrypting permanent file: {file_path}")
					with open(file_path, "rb") as f:
						encrypted_data = f.read()
					decrypted_data = decrypt_data(encrypted_data)
					with open(temp_path, "wb") as f:
						f.write(decrypted_data)
					logger.info(f"Re-decrypted permanent file for {filename} to {temp_path}")
				except Exception as e:
					logger.error(f"Failed to reconstruct temp file for {filename}: {str(e)}", exc_info=True)
					continue

			# Resume background task asynchronously
			logger.debug(f"Spawning async background task for document ID: {doc_id}")
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
		logger.error(f"Error during interrupted uploads recovery: {str(e)}", exc_info=True)
