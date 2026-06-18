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
    output_format: Optional[str] = ""
    api_key: Optional[str] = ""
    language: Optional[str] = "en"
    user_id: str
    workspace_id: str
    web_search_enabled: bool = False
    project_id: Optional[str] = None
    parent_agent_id: Optional[str] = None
    endpoints: Optional[list] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_strategy: Optional[str] = None
    system_prompt: Optional[str] = None
    output_format: Optional[str] = None
    api_key: Optional[str] = None
    language: Optional[str] = None
    web_search_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    endpoints: Optional[list] = None

@router.get("/api/agents")
async def get_agents(workspace_id: str, include_gateways: bool = False):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if include_gateways:
            condition = "WHERE workspace_id = %s AND (project_id IS NULL OR parent_agent_id IS NULL)"
        else:
            condition = "WHERE workspace_id = %s AND project_id IS NULL"
            
        cursor.execute(
            f"""
            SELECT id, name, description, llm_provider, llm_model, 
                   embedding_model, chunk_strategy, system_prompt, 
                   api_key, language, user_id, workspace_id, created_at,
                   web_search_enabled, project_id, is_active, output_format
            FROM agents 
            {condition}
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
                "created_at": row[12].isoformat() if row[12] else None,
                "web_search_enabled": row[13],
                "project_id": row[14],
                "is_active": row[15],
                "output_format": row[16]
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
                              embedding_model, chunk_strategy, system_prompt, output_format, 
                              api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, llm_provider, llm_model, 
                      embedding_model, chunk_strategy, system_prompt, output_format, 
                      api_key, language, user_id, workspace_id, created_at, web_search_enabled, project_id, parent_agent_id, endpoints;
            """,
            (agent.name, agent.description, agent.llm_provider, agent.llm_model,
             agent.embedding_model, agent.chunk_strategy, agent.system_prompt, agent.output_format,
             agent.api_key, agent.language, agent.user_id, agent.workspace_id, agent.web_search_enabled, agent.project_id, agent.parent_agent_id, json.dumps(agent.endpoints))
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
            "output_format": row[8],
            "api_key": row[9],
            "language": row[10],
            "user_id": row[11],
            "workspace_id": row[12],
            "created_at": row[13].isoformat() if row[13] else None,
            "web_search_enabled": row[14],
            "endpoints": row[17] if len(row) > 17 else []
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
    import json
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
            if key in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints"]:
                set_clauses.append(f"{key} = %s")
                if key == "endpoints":
                    values.append(json.dumps(value))
                else:
                    values.append(value)
                
        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        values.append(agent_id)
        
        query = f"UPDATE agents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, output_format, api_key, language, user_id, workspace_id, created_at, web_search_enabled, is_active, endpoints;"
        
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        # Insert Notification
        cursor.execute(
            """
            INSERT INTO notifications (workspace_id, title, message, type)
            VALUES (%s, %s, %s, 'agent_setting_updated');
            """,
            (
                row[12], # workspace_id
                "Agent Settings Updated",
                f"Settings for agent '{row[1]}' were updated."
            )
        )
            
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
            "output_format": row[8],
            "api_key": row[9],
            "language": row[10],
            "user_id": row[11],
            "workspace_id": row[12],
            "created_at": row[13].isoformat() if row[13] else None,
            "web_search_enabled": row[14],
            "is_active": row[15],
            "endpoints": row[16] if len(row) > 16 else []
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

@router.get("/api/agent-projects")
async def get_agent_projects(workspace_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, name, description, status, created_at, blueprint_json
            FROM agent_projects 
            WHERE workspace_id = %s 
            ORDER BY created_at DESC
            """,
            (workspace_id,)
        )
        rows = cursor.fetchall()
        
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "blueprint": row[5]
            })
            
        return projects
    except Exception as e:
        logger.error(f"Error fetching agent projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.get("/api/agent-projects/{project_id}/sub-agents")
async def get_project_sub_agents(project_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, name, description, llm_provider, llm_model, 
                   embedding_model, chunk_strategy, system_prompt, 
                   api_key, language, user_id, workspace_id, created_at,
                   web_search_enabled, parent_agent_id, is_active, output_format, endpoints
            FROM agents 
            WHERE project_id = %s 
            ORDER BY created_at ASC
            """,
            (project_id,)
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
                "created_at": row[12].isoformat() if row[12] else None,
                "web_search_enabled": row[13],
                "parent_agent_id": row[14],
                "is_active": row[15],
                "output_format": row[16],
                "endpoints": row[17] if len(row) > 17 else []
            })
            
        return agents
    except Exception as e:
        logger.error(f"Error fetching sub-agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.delete("/api/agent-projects/{project_id}")
async def delete_agent_project(project_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all document embeddings linked to the project or its agents
        cursor.execute("""
            DELETE FROM document_embeddings
            WHERE document_id IN (
                SELECT id FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
                OR project_id = %s
            )
        """, (project_id, project_id))
        
        # Delete all documents linked to the project or its agents
        cursor.execute("DELETE FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s) OR project_id = %s", (project_id, project_id))
        
        # Delete all chat messages linked to the project's agents
        cursor.execute("""
            DELETE FROM chat_messages 
            WHERE session_id IN (
                SELECT id FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
            )
        """, (project_id,))
        
        # Delete all chat sessions linked to the project's agents
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)", (project_id,))
        
        # Delete all agents linked to the project
        cursor.execute("DELETE FROM agents WHERE project_id = %s", (project_id,))

        cursor.execute("DELETE FROM agent_projects WHERE id = %s", (project_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
            
        conn.commit()
        return {"status": "success", "message": "Project deleted successfully"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class ToolUpdate(BaseModel):
    name: str
    config: dict

@router.get("/api/agent-projects/{project_id}/tools")
async def get_project_tools(project_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, config, blueprint_tool_id FROM agent_tools WHERE project_id = %s ORDER BY created_at ASC",
            (project_id,)
        )
        rows = cursor.fetchall()
        tools = []
        for row in rows:
            tools.append({
                "id": row[0],
                "name": row[1],
                "config": row[2] if isinstance(row[2], dict) else {},
                "blueprint_tool_id": row[3]
            })
        return tools
    except Exception as e:
        logger.error(f"Error fetching tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@router.put("/api/tools/{tool_id}")
async def update_project_tool(tool_id: str, payload: ToolUpdate):
    import json
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE agent_tools SET name = %s, config = %s WHERE id = %s RETURNING id;",
            (payload.name, json.dumps(payload.config), tool_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tool not found")
            
        conn.commit()
        return {"status": "success"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error updating tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class ToolCreate(BaseModel):
    name: str
    config: dict

@router.post("/api/agent-projects/{project_id}/tools")
async def create_project_tool(project_id: str, payload: ToolCreate):
    import json
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT workspace_id FROM agent_projects WHERE id = %s", (project_id,))
        project_row = cursor.fetchone()
        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")
            
        workspace_id = project_row[0]

        cursor.execute(
            """
            INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (project_id, workspace_id, "custom_tool_" + payload.name.lower().replace(" ", "_"), payload.name, json.dumps(payload.config))
        )
        tool_id = cursor.fetchone()[0]
        conn.commit()
        return {"status": "success", "id": tool_id}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
