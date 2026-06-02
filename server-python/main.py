# server-python/main.py
import json
import logging
import os
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from custom_rag import CustomRAGEngine
from database import get_db_connection
from schemas import ChatRequest, URLRequest

# --- LLM IMPORTS ---
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Custom RAGMate Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rag-mate-ashen.vercel.app/", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize RAG Engine
rag_engine = CustomRAGEngine()

# ==========================================
# BACKGROUND TASKS
# ==========================================
def background_ingestion(document_id: int, agent_id: str, raw_text: str, strategy: str, embed_model: str, file_path: str = None):
    """Runs chunking + embedding in the background and updates document status."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.info("⚙️ Background task started for doc id: %s", document_id)

        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the uploaded content")

        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        for text, vector in zip(chunks, vectors):
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, text, vector)
            )

        cursor.execute("UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,))
        conn.commit()
        logger.info("✅ Background task completed for doc id: %s", document_id)

    except Exception:
        logger.exception("Background ingestion failed for doc id %s", document_id)
        if conn and cursor:
            try:
                cursor.execute("UPDATE documents SET status = 'failed' WHERE id = %s", (document_id,))
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ==========================================
# API ROUTES: DOCUMENTS & INGESTION
# ==========================================
# ==========================================
# API ROUTE: UPLOAD ANY FILE (.pdf, .txt, .docx, .csv)
# ==========================================
@app.post("/process-file")
async def process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), agent_id: str = Form(...)):
    """Upload a supported file, extract text, create a document row, and schedule ingestion."""
    allowed_exts = {"pdf", "txt", "docx", "csv"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.")

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT embedding_model, chunk_strategy FROM agents WHERE id = %s", (agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        embed_model = agent_row[0] if agent_row[0] else "all-MiniLM-L6-v2"
        strategy = agent_row[1] if agent_row[1] else "sentence"

        raw_text = rag_engine.extract_text_from_file(str(file_path), safe_filename)

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
            (agent_id, safe_filename)
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(background_ingestion, document_id, agent_id, raw_text, strategy, embed_model, str(file_path))
        return {"message": f"{ext.upper()} uploaded successfully! Processing in background..."}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process uploaded file")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks):
    """Fetch a webpage, create a document row, and schedule ingestion."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT embedding_model, chunk_strategy FROM agents WHERE id = %s", (req.agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        embed_model = agent_row[0] if agent_row[0] else "all-MiniLM-L6-v2"
        strategy = agent_row[1] if agent_row[1] else "sentence"

        raw_text = rag_engine.extract_text_from_url(req.url)

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
            (req.agent_id, req.url)
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(background_ingestion, document_id, req.agent_id, raw_text, strategy, embed_model, None)
        return {"message": "URL scraped. Processing in background..."}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process URL")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, filename, status, created_at FROM documents WHERE agent_id = %s ORDER BY created_at DESC", (agent_id,))
        docs = [{"id": r[0], "filename": r[1], "status": r[2], "created_at": r[3]} for r in cursor.fetchall()]
        return {"documents": docs}
    finally:
        cursor.close()
        conn.close()

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        return {"message": "Document and its memory completely deleted!"}
    finally:
        cursor.close()
        conn.close()

# ==========================================
# API ROUTES: CHAT & AGENTS
# ==========================================
@app.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """Stream an LLM response grounded in the uploaded documents."""
    if not req.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name, system_prompt, provider, model, api_key, embedding_model FROM agents WHERE id = %s",
            (req.agent_id,)
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent_name, system_prompt, provider, model, custom_api_key, embed_model = agent_data
        embed_model = embed_model or "all-MiniLM-L6-v2"

        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        cursor.execute("""
            SELECT de.content, de.embedding
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = %s
        """, (req.agent_id,))
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [json.loads(row[1]) if isinstance(row[1], str) else row[1] for row in rows]

            query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=10,
            )

            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        prompt = f"""{system_prompt}
        You are a strict, professional AI assistant grounded ONLY in the provided documents.

        CRITICAL RULES:
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {req.message}
        """

        async def stream_generator():
            try:
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Chat endpoint failed")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM document_embeddings
            WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
        """, (agent_id,))
        cursor.execute("DELETE FROM documents WHERE agent_id = %s", (agent_id,))
        cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        conn.commit()
        return {"message": "Agent and all its memory completely wiped!"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Modular RAGMate Server on Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# # server-python/main.py
# import os
# import json
# import shutil
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request    
# from fastapi.responses import StreamingResponse
# from fastapi.middleware.cors import CORSMiddleware
# from schemas import ChatRequest, URLRequest

# # --- CUSTOM MODULES IMPORT ---
# from database import get_db_connection
# from schemas import ChatRequest, URLRequest
# from custom_rag import CustomRAGEngine 

# # --- LLM IMPORTS ---
# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI

# app = FastAPI(title="Custom RAGMate Backend")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "temp_uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # Initialize RAG Engine
# rag_engine = CustomRAGEngine()

# # ==========================================
# # BACKGROUND TASKS
# # ==========================================
# def background_ingestion(document_id: int, agent_id: str, raw_text: str, strategy: str, embed_model: str, file_path: str = None):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         print(f"⚙️ Background Task Started for Doc ID: {document_id}")
        
#         if strategy == "naive": chunks = rag_engine.chunk_text_naive(raw_text)
#         elif strategy == "paragraph": chunks = rag_engine.chunk_text_paragraph(raw_text)
#         else: chunks = rag_engine.chunk_text_sentence(raw_text)
        
#         vectors = rag_engine.vectorize(chunks, model_name=embed_model)
        
#         for text, vector in zip(chunks, vectors):
#             cursor.execute(
#                 "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
#                 (document_id, text, vector)
#             )
            
#         cursor.execute("UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,))
#         conn.commit()
#         print(f"✅ Background Task Completed for Doc ID: {document_id}")

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         if conn: 
#             cursor = conn.cursor()
#             cursor.execute("UPDATE documents SET status = 'failed' WHERE id = %s", (document_id,))
#             conn.commit()
#     finally:
#         if conn: conn.close()
#         if file_path and os.path.exists(file_path): 
#             os.remove(file_path)

# # ==========================================
# # API ROUTES: DOCUMENTS & INGESTION
# # ==========================================
# # ==========================================
# # API ROUTE: UPLOAD ANY FILE (.pdf, .txt, .docx, .csv)
# # ==========================================
# @app.post("/process-file") # Route name changed
# async def process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), agent_id: str = Form(...)):
    
#     # Check allowed extensions
#     allowed_exts = ['pdf', 'txt', 'docx', 'csv']
#     ext = file.filename.split('.')[-1].lower()
    
#     if ext not in allowed_exts:
#         raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_exts)} files are allowed.")
        
#     file_path = os.path.join(UPLOAD_DIR, file.filename)
    
#     with open(file_path, "wb") as buffer: 
#         shutil.copyfileobj(file.file, buffer)
        
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT embedding_model, chunking_strategy FROM agents WHERE id = %s", (agent_id,))
#         agent_row = cursor.fetchone()
#         embed_model = agent_row[0] if agent_row and agent_row[0] else "all-MiniLM-L6-v2"
#         strategy = agent_row[1] if agent_row and agent_row[1] else "sentence"
        
#         # Call the new Universal Extractor
#         raw_text = rag_engine.extract_text_from_file(file_path, file.filename)
        
#         cursor.execute(
#             "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
#             (agent_id, file.filename)
#         )
#         document_id = cursor.fetchone()[0]
#         conn.commit()
        
#         background_tasks.add_task(background_ingestion, document_id, agent_id, raw_text, strategy, embed_model, file_path)
#         return {"message": f"{ext.upper()} uploaded successfully! Processing in background..."}
#     finally:
#         conn.close()

# @app.post("/process-url")
# async def process_url(req: URLRequest, background_tasks: BackgroundTasks):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT embedding_model, chunking_strategy FROM agents WHERE id = %s", (req.agent_id,))
#         agent_row = cursor.fetchone()
#         embed_model = agent_row[0] if agent_row and agent_row[0] else "all-MiniLM-L6-v2"
#         strategy = agent_row[1] if agent_row and agent_row[1] else "sentence"
        
#         raw_text = rag_engine.extract_text_from_url(req.url)
        
#         cursor.execute(
#             "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
#             (req.agent_id, req.url)
#         )
#         document_id = cursor.fetchone()[0]
#         conn.commit()
        
#         background_tasks.add_task(background_ingestion, document_id, req.agent_id, raw_text, strategy, embed_model, None)
#         return {"message": "URL scraped. Processing in background..."}
#     finally:
#         conn.close()

# @app.get("/agents/{agent_id}/documents")
# async def get_documents(agent_id: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT id, filename, status, created_at FROM documents WHERE agent_id = %s ORDER BY created_at DESC", (agent_id,))
#         docs = [{"id": r[0], "filename": r[1], "status": r[2], "created_at": r[3]} for r in cursor.fetchall()]
#         return {"documents": docs}
#     finally:
#         conn.close()

# @app.delete("/documents/{doc_id}")
# async def delete_document(doc_id: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
#         cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
#         conn.commit()
#         return {"message": "Document and its memory completely deleted!"}
#     finally:
#         conn.close()

# # ==========================================
# # API ROUTES: CHAT & AGENTS
# # ==========================================
# @app.post("/chat")
# async def chat_with_agent(req: ChatRequest):
#     # Agar frontend se khali request aayi hai (invalid data), toh yahan se return kar do
#     if not req.agent_id or not req.message:
#         return {"status": "ignored", "message": "Invalid request payload"}

#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         cursor.execute(
#             "SELECT name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s", 
#             (req.agent_id,) 
#         )
#         agent_data = cursor.fetchone()
#         if not agent_data: raise HTTPException(status_code=404, detail="Agent not found")
        
#         agent_name, system_prompt, llm_provider, llm_model, custom_api_key, embed_model = agent_data
#         if not embed_model: embed_model = "all-MiniLM-L6-v2"

#         if llm_provider == 'openai':
#             key_to_use = custom_api_key if custom_api_key else os.getenv("OPENAI_API_KEY")
#             if not key_to_use: raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
#             llm = ChatOpenAI(model_name=llm_model, api_key=key_to_use)
#         else:
#             key_to_use = custom_api_key if custom_api_key else os.getenv("GROQ_API_KEY")
#             if not key_to_use: raise HTTPException(status_code=400, detail="Groq API Key missing.")
#             llm = ChatGroq(model_name=llm_model, api_key=key_to_use)

#         cursor.execute("""
#             SELECT de.content, de.embedding 
#             FROM document_embeddings de
#             JOIN documents d ON de.document_id = d.id
#             WHERE d.agent_id = %s
#         """, (req.agent_id,))
#         rows = cursor.fetchall()
        
#         context = "No specific documents found."
        
#         if rows:
#             doc_chunks = [row[0] for row in rows]
#             doc_vectors = [json.loads(row[1]) if isinstance(row[1], str) else row[1] for row in rows]
            
#             query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
#             top_matches = rag_engine.hybrid_search(
#                 query_text=req.message, query_vector=query_vector,
#                 document_texts=doc_chunks, document_vectors=doc_vectors,
#                 alpha=0.7, top_k=10
#             )
            
#             best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
#             context = "\n\n---\n\n".join(best_chunks)

#         history_text = ""
#         for msg in req.history[-6:]: 
#             role_name = "User" if msg["role"] == "user" else "Assistant"
#             history_text += f"{role_name}: {msg['content']}\n"
#         if not history_text: history_text = "No previous conversation."

#         cursor.close()
#         conn.close()
#         conn = None 

#         prompt = f"""{system_prompt}
#         You are a strict, professional AI assistant grounded ONLY in the provided documents. 

#         CRITICAL RULES:
#         1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
#         2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
#         3. Format response beautifully in Markdown.
#         4. Use the PREVIOUS CHAT HISTORY to understand context.
#         5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
#         6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

#         CONTEXT DOCUMENTS:
#         {context}

#         PREVIOUS CHAT HISTORY:
#         {history_text}

#         CURRENT USER INPUT: {req.message}
#         """

#         async def stream_generator():
#             try:
#                 for chunk in llm.stream(prompt):
#                     if chunk.content:
#                         yield chunk.content
#             except Exception as e:
#                 yield f"\n\n⚠️ Error during generation: {str(e)}"

#         return StreamingResponse(stream_generator(), media_type="text/plain")

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         if conn: conn.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         if conn: conn.close()

# @app.delete("/agents/{agent_id}")
# async def delete_agent(agent_id: str):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("""
#             DELETE FROM document_embeddings 
#             WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
#         """, (agent_id,))
#         cursor.execute("DELETE FROM documents WHERE agent_id = %s", (agent_id,))
#         cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
#         conn.commit()
#         return {"message": "Agent and all its memory completely wiped!"}
#     except Exception as e:
#         if conn: conn.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         if conn: conn.close()

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting Modular RAGMate Server on Port 8000...")
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
