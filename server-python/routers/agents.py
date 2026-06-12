import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    llm_provider: str
    llm_model: str
    embedding_model: Optional[str] = "text-embedding-3-small"
    chunk_strategy: Optional[str] = "semantic"
    system_prompt: Optional[str] = ""
    api_key: Optional[str] = ""
    language: Optional[str] = "en"
    user_id: str
    workspace_id: str

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_strategy: Optional[str] = None
    system_prompt: Optional[str] = None
    api_key: Optional[str] = None
    language: Optional[str] = None

@router.get("/api/agents")
async def get_agents(workspace_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, name, description, llm_provider, llm_model, 
                   embedding_model, chunk_strategy, system_prompt, 
                   api_key, language, user_id, workspace_id, created_at 
            FROM agents 
            WHERE workspace_id = %s 
            ORDER BY created_at DESC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        agents = []
        for row in rows:
            agents.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "llm_provider": row[3],
                "llm_model": row[4],
                "embedding_model": row[5],
                "chunk_strategy": row[6],
                "system_prompt": row[7],
                "api_key": row[8],
                "language": row[9],
                "user_id": row[10],
                "workspace_id": row[11],
                "created_at": row[12].isoformat() if row[12] else None
            })
            
        return agents
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.post("/api/agents")
async def create_agent(agent: AgentCreate):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, 
                              embedding_model, chunk_strategy, system_prompt, 
                              api_key, language, user_id, workspace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, llm_provider, llm_model, 
                      embedding_model, chunk_strategy, system_prompt, 
                      api_key, language, user_id, workspace_id, created_at;
            """,
            (agent.name, agent.description, agent.llm_provider, agent.llm_model,
             agent.embedding_model, agent.chunk_strategy, agent.system_prompt,
             agent.api_key, agent.language, agent.user_id, agent.workspace_id)
        )
        row = cursor.fetchone()
        conn.commit()
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "llm_provider": row[3],
            "llm_model": row[4],
            "embedding_model": row[5],
            "chunk_strategy": row[6],
            "system_prompt": row[7],
            "api_key": row[8],
            "language": row[9],
            "user_id": row[10],
            "workspace_id": row[11],
            "created_at": row[12].isoformat() if row[12] else None
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, payload: dict):
    conn = None
    cursor = None
    try:
        if not payload:
            return {}

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # We build the update query dynamically
        set_clauses = []
        values = []
        for key, value in payload.items():
            # Allow only valid columns to be updated
            if key in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "api_key", "language"]:
                set_clauses.append(f"{key} = %s")
                values.append(value)
                
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        values.append(agent_id)
        
        query = f"UPDATE agents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, api_key, language, user_id, workspace_id, created_at;"
        
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        conn.commit()
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "llm_provider": row[3],
            "llm_model": row[4],
            "embedding_model": row[5],
            "chunk_strategy": row[6],
            "system_prompt": row[7],
            "api_key": row[8],
            "language": row[9],
            "user_id": row[10],
            "workspace_id": row[11],
            "created_at": row[12].isoformat() if row[12] else None
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
