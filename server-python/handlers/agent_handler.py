import logging
import json
from typing import Optional
from fastapi import HTTPException
from database import get_db_connection
from core.security import encrypt_key, decrypt_key

logger = logging.getLogger(__name__)

async def handle_get_agents(workspace_id: str, include_gateways: bool = False):
    """
    What it does: Retrieves all AI agents associated with a specific workspace.
    Args:
        workspace_id (str): The ID of the workspace to fetch agents for.
        include_gateways (bool): Whether to include top-level router agents (gateways).
    Returns: A list of agent dictionaries with their configurations.
    """
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
                "api_key": decrypt_key(row[8]) or "",
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


async def handle_create_agent(payload_data: dict):
    """
    What it does: Creates a new AI agent with the specified configuration and saves it to the database. API keys are encrypted at rest.
    Args:
        payload_data (dict): A dictionary containing all the settings for the new agent.
    Returns: A dictionary of the created agent's data, including its new ID.
    """
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
            (
                payload_data.get("name"), 
                payload_data.get("description", ""), 
                payload_data.get("llm_provider"), 
                payload_data.get("llm_model"),
                payload_data.get("embedding_model", "text-embedding-3-small"), 
                payload_data.get("chunk_strategy", "semantic"), 
                payload_data.get("system_prompt", ""), 
                payload_data.get("output_format", ""),
                encrypt_key(payload_data.get("api_key", "")), 
                payload_data.get("language", "en"), 
                payload_data.get("user_id"), 
                payload_data.get("workspace_id"), 
                payload_data.get("web_search_enabled", False), 
                payload_data.get("project_id"), 
                payload_data.get("parent_agent_id"), 
                json.dumps(payload_data.get("endpoints", []))
            )
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
            "api_key": decrypt_key(row[9]) or "",
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


async def handle_update_agent(agent_id: str, payload: dict):
    """
    What it does: Updates an existing agent's configuration dynamically based on the provided fields, and sends a real-time notification to the frontend.
    Args:
        agent_id (str): The ID of the agent to modify.
        payload (dict): The fields to update.
    Returns: The updated agent dictionary.
    """
    conn = None
    cursor = None
    try:
        if not payload:
            return {}

        conn = get_db_connection()
        cursor = conn.cursor()
        
        set_clauses = []
        values = []
        for key, value in payload.items():
            if key in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints"]:
                set_clauses.append(f"{key} = %s")
                if key == "api_key":
                    values.append(encrypt_key(value))
                elif key == "endpoints":
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
            
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(row[12]),
                title="Agent Settings Updated",
                message=f"Settings for agent '{row[1]}' were updated.",
                notification_type="agent_setting_updated"
            )
        except Exception as ne:
            logger.error(f"Failed to create settings update notification: {ne}")
            
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
            "api_key": decrypt_key(row[9]) or "",
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


async def handle_create_agent_project(name: str, description: str, workspace_id: str, user_id: str):
    """
    What it does: Creates a new Multi-Agent Project network and immediately creates a default 'Master Router' agent to coordinate it.
    Args:
        name (str): The project name.
        description (str): A brief description of the project.
        workspace_id (str): The workspace the project belongs to.
        user_id (str): The owner's user ID.
    Returns: The new project's ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO agent_projects (name, description, status, workspace_id, blueprint_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (name, description, "active", workspace_id, json.dumps({}))
        )
        project_id = cursor.fetchone()[0]
        
        cursor.execute(
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, 
                              embedding_model, chunk_strategy, system_prompt, output_format, 
                              api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                f"{name} Master", 
                "The central router agent for this network.", 
                "groq", 
                "llama-3.1-8b-instant",
                "all-MiniLM-L6-v2", 
                "sentence", 
                "You are the master coordinator for this network. Analyze user requests and delegate to your sub-agents as necessary.", 
                "",
                encrypt_key(""), 
                "en", 
                user_id, 
                workspace_id, 
                False, 
                project_id, 
                None, 
                json.dumps([])
            )
        )
        
        conn.commit()
        return {"status": "success", "id": project_id}
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error creating agent project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_get_agent_projects(workspace_id: str):
    """
    What it does: Retrieves a list of all Multi-Agent Projects in a workspace.
    Args:
        workspace_id (str): The ID of the workspace.
    Returns: A list of project dictionaries.
    """
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


async def handle_get_project_sub_agents(project_id: str):
    """
    What it does: Gets all the individual AI agents that belong to a specific Multi-Agent Project.
    Args:
        project_id (str): The ID of the project.
    Returns: A list of agents belonging to that project.
    """
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
                "api_key": decrypt_key(row[8]) or "",
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


async def handle_delete_agent_project(project_id: str):
    """
    What it does: Erases an entire Multi-Agent Project and cleans up all associated documents, chat messages, and agent data.
    Args:
        project_id (str): The ID of the project to destroy.
    Returns: A confirmation message upon success.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM document_embeddings
            WHERE document_id IN (
                SELECT id FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
                OR project_id = %s
            )
        """, (project_id, project_id))
        
        cursor.execute("DELETE FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s) OR project_id = %s", (project_id, project_id))
        
        cursor.execute("""
            DELETE FROM chat_messages 
            WHERE session_id IN (
                SELECT id FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
            )
        """, (project_id,))
        
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)", (project_id,))
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


async def handle_get_project_tools(project_id: str):
    """
    What it does: Fetches all custom tools associated with an Agent Project.
    Args:
        project_id (str): The ID of the project.
    Returns: A list of tools.
    """
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


async def handle_update_project_tool(tool_id: str, name: str, config: dict):
    """
    What it does: Updates the name and JSON configuration of a custom project tool.
    Args:
        tool_id (str): The ID of the tool.
        name (str): The new name of the tool.
        config (dict): The new configuration data.
    Returns: A success dictionary.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE agent_tools SET name = %s, config = %s WHERE id = %s RETURNING id;",
            (name, json.dumps(config), tool_id)
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


async def handle_create_project_tool(project_id: str, name: str, config: dict):
    """
    What it does: Creates a brand new custom tool for a project.
    Args:
        project_id (str): The ID of the project to attach the tool to.
        name (str): The name of the new tool.
        config (dict): The JSON configuration of the tool.
    Returns: A dictionary with the new tool's ID.
    """
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
            (project_id, workspace_id, "custom_tool_" + name.lower().replace(" ", "_"), name, json.dumps(config))
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
