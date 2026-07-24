"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core background parsing and indexing pipeline for documents
in RAGMate. It acts as a worker utility that:
1. Extracts text from raw uploaded document files.
2. Slices text into semantic chunks based on different chunking strategies (Naive, Sentence, Paragraph).
3. Generates vector embeddings for each chunk using embedding models.
4. Indexes and saves these vectors and text chunks into the PostgreSQL database.
5. Sends real-time WebSocket status updates and workspace notifications on success/failure.
6. Resumes interrupted upload tasks upon server restart by decrypting local files and
   re-queuing background processes.

From top to bottom, the file executes as follows:
- Imports: standard libraries, local dependencies (RAG engine, paths, security, limits).
- Logging: scopes a department logger to "knowledge_base".
- `async_background_ingestion`: Main async parsing, chunking, embedding, database indexing,
  and notification workflow.
- `resume_interrupted_uploads`: Cleanup daemon tool that detects unfinished document ingests,
  decrypts local files, and launches ingestion workflows for recovery.
"""

import os  # Read/edit filesystem entries and check file presence
import asyncio  # Manage non-blocking async loops and threads
from pathlib import Path  # Object-oriented path navigation
from core.dependencies import rag_engine, UPLOAD_DIR  # Fetch RAG model wrapper and upload folders
from core.security import decrypt_data  # Helper to decrypt database keys and files
from utils import get_user_limits  # Load tier configuration details

# Logging configuration
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "knowledge_base" activities
logger = get_department_logger("knowledge_base")

from handlers.websocket_handlers import upload_status_manager  # Broadcast socket notifications
from db import document_repository  # Database query repository for documents


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
	Executes the document ingestion workflow asynchronously:
	1. Text Extraction (runs in threadpool to prevent event loop blocking).
	2. Chunking (Naive, Paragraph, or Sentence strategies).
	3. Embeddings (Vectorizes text blocks using HuggingFace models).
	4. DB Indexing (Inserts chunks and vectors into database tables).
	5. Broadcast Status (Sends status notifications via WebSockets).
	6. Workspace notification updates.
	7. Temporary file cleanup.

	Parameters:
		document_id (str): Unique database document UUID.
		agent_id (str): Linked AI Agent UUID.
		filename (str): Original uploaded file name.
		temp_path (str): Temporary path location of decrypted file bytes on disk.
		strategy (str): Chosen chunking strategy ('naive', 'paragraph', 'sentence').
		embed_model (str): Chosen embedding model name (e.g. 'all-MiniLM-L6-v2').
		workspace_id (str): Target workspace UUID.
		file_path (str, optional): Target permanent encrypted file path.

	Returns:
		None: Runs background updates and database inserts.

	Exceptions Handled:
		Catches all errors, updates database document state to 'failed',
		broadcasts failure notifications, and cleans temporary files.
	"""
	logger.info(f"Starting async background ingestion task for document ID: {document_id} ('{filename}')")
	logger.debug(f"Parameters: strategy={strategy}, embed_model={embed_model}, workspace_id={workspace_id}, file_path={file_path}")
	try:
		# Step 1: Text Extraction
		logger.debug("Step 1: Extracting plain text from target document file...")
		await upload_status_manager.send_status(agent_id, "processing", filename, "Extracting text content (running OCR fallback if needed)...", 0.1)
		
		# Run synchronous text extraction helper inside threadpool to prevent blocking FastAPI
		raw_text = await asyncio.to_thread(rag_engine.extract_text_from_file, temp_path, filename)
		
		# Raise error if output content is empty
		if not raw_text or not raw_text.strip():
			logger.error("Text extraction returned an empty payload.")
			raise ValueError("Document is empty or text extraction failed.")
		
		logger.debug(f"Successfully extracted {len(raw_text)} characters of raw text.")

		# Step 2: Chunking
		logger.debug(f"Step 2: Partitioning text using '{strategy}' chunking strategy...")
		await upload_status_manager.send_status(agent_id, "chunking", filename, "Chunking text content...", 0.4)
		
		# Execute chunking based on configured strategy inside threadpool
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
		
		# Generate vector embeddings for text chunks inside threadpool
		vectors = await asyncio.to_thread(rag_engine.vectorize, chunks, model_name=embed_model)
		logger.debug(f"Successfully generated vectors. Output count: {len(vectors)}")

		# Step 4: Database Indexing
		logger.debug(f"Step 4: Inserting {len(chunks)} vectors and chunks into vector database...")
		await upload_status_manager.send_status(agent_id, "indexing", filename, "Saving chunks to database...", 0.9)
		
		# Write vectors and text blocks into database table
		await document_repository.index_document_chunks(document_id, chunks, vectors)
		logger.debug("Successfully committed all document vectors to PostgreSQL.")

		# Broadcast completion status via WebSockets
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
		# Send error status to clients via WebSockets
		await upload_status_manager.send_status(agent_id, "failed", filename, f"Failed: {str(e)}", 0.0)
		
		# Send Failure Notification to Workspace
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

		# Mark document status as 'failed' in database
		try:
			logger.debug(f"Marking document status as 'failed' in database for doc ID: {document_id}")
			await document_repository.mark_document_failed(document_id)
		except Exception as dbe:
			logger.error(f"Failed to mark document as failed in database: {str(dbe)}", exc_info=True)

	finally:
		# Clean up temporary unencrypted file from disk
		if temp_path and os.path.exists(temp_path):
			logger.debug(f"Cleaning up temporary file: {temp_path}")
			os.remove(temp_path)


async def resume_interrupted_uploads():
	"""
	Scans the database for documents stuck in 'processing' status (signifying server crash).
	For each stuck document:
	- Decrypts the corresponding disk file to recreate a temporary unencrypted file.
	- Re-queues the ingestion task in background threadpools.
	"""
	logger.info("Scanning database to check for interrupted document uploads that need to resume...")
	try:
		# Retrieve stuck files from repository
		rows = await document_repository.get_interrupted_uploads()
		if not rows:
			logger.info("No interrupted uploads found.")
			return

		logger.info(f"Found {len(rows)} interrupted document uploads. Resuming execution...")
		for doc_id, agent_id, filename, strategy, embed_model, workspace_id in rows:
			file_path = UPLOAD_DIR / filename
			temp_path = str(file_path) + ".tmp"
			
			logger.debug(f"Processing interrupted document ID: {doc_id} ('{filename}')")
			
			# Decrypt permanent encrypted file if the temporary unencrypted copy is missing
			if not os.path.exists(temp_path) and file_path.exists():
				try:
					logger.debug(f"Temporary file missing. Decrypting permanent file: {file_path}")
					with open(file_path, "rb") as f:
						encrypted_data = f.read()
					# Decrypt data using symmetrical encryption tools
					decrypted_data = decrypt_data(encrypted_data)
					# Write back temporary copy
					with open(temp_path, "wb") as f:
						f.write(decrypted_data)
					logger.info(f"Re-decrypted permanent file for {filename} to {temp_path}")
				except Exception as e:
					logger.error(f"Failed to reconstruct temp file for {filename}: {str(e)}", exc_info=True)
					continue

			# Re-launch ingestion workflow asynchronously
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
