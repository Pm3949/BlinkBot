import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chatbots"])

class ChatbotCreate(BaseModel):
    agent_id: str
    name: str
    settings: Optional[dict] = {}

class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None

@router.get("/api/chatbots")
async def get_chatbots(workspace_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE a.workspace_id = %s
            ORDER BY c.created_at DESC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        chatbots = []
        for row in rows:
            chatbots.append({
                "id": row[0],
                "agent_id": row[1],
                "name": row[2],
                "settings": row[3],
                "message_count": row[4],
                "api_key": row[5],
                "allowed_domains": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "agents": {
                    "workspace_id": row[8],
                    "name": row[9]
                }
            })
            
        return chatbots
    except Exception as e:
        logger.error(f"Error fetching chatbots: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chatbots")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/api/chatbots/{chatbot_id}")
async def get_chatbot_by_id(chatbot_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE c.id = %s
            """,
            (chatbot_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "agents": {
                "workspace_id": row[8],
                "name": row[9]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.post("/api/chatbots")
async def create_chatbot(payload: ChatbotCreate):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json
        settings_json = json.dumps(payload.settings) if payload.settings else "{}"
        
        cursor.execute(
            """
            INSERT INTO chatbots (agent_id, name, settings)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at
            """,
            (payload.agent_id, payload.name, settings_json)
        )
        row = cursor.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to create chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.put("/api/chatbots/{chatbot_id}")
async def update_chatbot(chatbot_id: str, payload: dict):
    conn = None
    cursor = None
    try:
        if not payload:
            return {}

        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json
        set_clauses = []
        values = []
        for key, value in payload.items():
            if key in ["name", "api_key", "allowed_domains"]:
                set_clauses.append(f"{key} = %s")
                values.append(value)
            elif key == "settings":
                set_clauses.append("settings = %s::jsonb")
                values.append(json.dumps(value))
                
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        values.append(chatbot_id)
        
        query = f"UPDATE chatbots SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at;"
        
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chatbot not found")
            
        conn.commit()
        
        return {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "settings": row[3],
            "message_count": row[4],
            "api_key": row[5],
            "allowed_domains": row[6],
            "created_at": row[7].isoformat() if row[7] else None
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating chatbot: {e}")
        raise HTTPException(status_code=500, detail="Failed to update chatbot")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
