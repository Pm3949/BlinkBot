import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notes"])

class NoteCreate(BaseModel):
    user_id: str
    workspace_id: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = "General"
    title: str
    content: str

class NoteUpdate(BaseModel):
    pinned: bool

@router.get("/api/notes")
async def get_notes(workspace_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, workspace_id, agent_id, agent_name, title, content, pinned, created_at 
            FROM notes 
            WHERE workspace_id = %s 
            ORDER BY pinned DESC, created_at DESC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        notes = []
        for row in rows:
            notes.append({
                "id": str(row[0]),
                "userId": str(row[1]),
                "workspaceId": str(row[2]),
                "agentId": str(row[3]) if row[3] else None,
                "agentName": row[4],
                "title": row[5],
                "content": row[6],
                "pinned": row[7],
                "createdAt": row[8].isoformat() if row[8] else None
            })
        return notes
    except Exception as exc:
        logger.exception("Failed to get notes")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.post("/api/notes")
async def create_note(req: NoteCreate):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if identical note exists
        cursor.execute(
            """
            SELECT id FROM notes 
            WHERE workspace_id = %s AND agent_id IS NOT DISTINCT FROM %s AND content = %s
            """,
            (req.workspace_id, req.agent_id, req.content)
        )
        if cursor.fetchone():
            return {"message": "Note already exists"}
            
        cursor.execute(
            """
            INSERT INTO notes (user_id, workspace_id, agent_id, agent_name, title, content)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (req.user_id, req.workspace_id, req.agent_id, req.agent_name, req.title, req.content)
        )
        new_id, created_at = cursor.fetchone()
        conn.commit()
        
        return {
            "id": str(new_id),
            "userId": req.user_id,
            "workspaceId": req.workspace_id,
            "agentId": req.agent_id,
            "agentName": req.agent_name,
            "title": req.title,
            "content": req.content,
            "pinned": False,
            "createdAt": created_at.isoformat()
        }
    except Exception as exc:
        logger.exception("Failed to create note")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.delete("/api/notes/{note_id}")
async def delete_note(note_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        conn.commit()
        return {"message": "Note deleted successfully"}
    except Exception as exc:
        logger.exception("Failed to delete note")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.put("/api/notes/{note_id}/pin")
async def toggle_pin_note(note_id: str, req: NoteUpdate):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET pinned = %s WHERE id = %s", (req.pinned, note_id))
        conn.commit()
        return {"message": "Note pin status updated"}
    except Exception as exc:
        logger.exception("Failed to update note pin")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
