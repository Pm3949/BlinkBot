import os
import shutil
import logging
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from database import get_db_connection
from core.dependencies import rag_engine, UPLOAD_DIR
from utils import background_ingestion, get_user_limits
from schemas import URLRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

@router.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str = Form(...),
):
    """Upload a supported file, extract text, create a document row, and schedule ingestion."""
    allowed_exts = {"pdf", "txt", "docx", "csv", "png", "jpg", "jpeg"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.",
        )

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        # Check Storage Limit
        limits = get_user_limits(user_id, cursor)
        file_size = os.path.getsize(file_path)

        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            os.remove(file_path)
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        raw_text = rag_engine.extract_text_from_file(str(file_path), safe_filename)

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (agent_id, safe_filename, file_size),
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(
            background_ingestion,
            document_id,
            agent_id,
            raw_text,
            strategy,
            embed_model,
            str(file_path),
        )
        return {
            "message": f"{ext.upper()} uploaded successfully! Processing in background..."
        }
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


@router.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks):
    """Fetch a webpage, create a document row, and schedule ingestion."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (req.agent_id,),
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        raw_text = rag_engine.extract_text_from_url(req.url)
        file_size = len(raw_text.encode("utf-8"))

        # Check Storage Limit
        limits = get_user_limits(user_id, cursor)
        cursor.execute(
            """
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """,
            (user_id,),
        )
        current_storage = cursor.fetchone()[0] or 0

        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            raise HTTPException(
                status_code=403,
                detail="Storage limit exceeded. Please upgrade your plan.",
            )

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (req.agent_id, req.url, file_size),
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(
            background_ingestion,
            document_id,
            req.agent_id,
            raw_text,
            strategy,
            embed_model,
            None,
        )
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


@router.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
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
        docs = [
            {
                "id": r[0],
                "filename": r[1],
                "status": r[2],
                "created_at": r[3],
                "file_size_bytes": r[4] or 0,
                "chunk_count": r[5] or 0,
            }
            for r in cursor.fetchall()
        ]
        return {"documents": docs}
    finally:
        cursor.close()
        conn.close()


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT filename FROM documents WHERE id = %s", (doc_id,))
        doc = cursor.fetchone()
        if doc and doc[0]:
            from core.dependencies import UPLOAD_DIR
            file_path = UPLOAD_DIR / doc[0]
            import os
            if os.path.exists(file_path):
                os.remove(file_path)

        cursor.execute(
            "DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,)
        )
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        return {"message": "Document and its memory completely deleted!"}
    finally:
        cursor.close()
        conn.close()
