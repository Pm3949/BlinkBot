import logging
import json
from typing import Optional
from fastapi import HTTPException
from core.security import decrypt_key
from database_layer import agent_repository

logger = logging.getLogger(__name__)

async def handle_get_agents(workspace_id: str, include_gateways: bool = False):
    """
    What it does: Retrieves all AI agents associated with a specific workspace.
    Args:
        workspace_id (str): The ID of the workspace to fetch agents for.
        include_gateways (bool): Whether to include top-level router agents (gateways).
    Returns: A list of agent dictionaries with their configurations.
    """
    try:
        rows = await agent_repository.get_agents(workspace_id, include_gateways)
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
                "output_format": row[16],
                "endpoints": row[17] if len(row) > 17 else [],
                "code_interpreter_enabled": row[18] if len(row) > 18 else False,
                "databases": json.loads(decrypt_key(row[19])) if len(row) > 19 and decrypt_key(row[19]) else [],
                "native_integrations": json.loads(decrypt_key(row[20])) if len(row) > 20 and decrypt_key(row[20]) else []
            })
        return agents
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_agent(payload_data: dict):
    """
    What it does: Creates a new AI agent with the specified configuration and saves it to the database. API keys are encrypted at rest.
    Args:
        payload_data (dict): A dictionary containing all the settings for the new agent.
    Returns: A dictionary of the created agent's data, including its new ID.
    """
    try:
        row = await agent_repository.create_agent(payload_data)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create agent")
            
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
            "endpoints": row[17] if len(row) > 17 else [],
            "code_interpreter_enabled": row[18] if len(row) > 18 else False,
            "databases": json.loads(decrypt_key(row[19])) if len(row) > 19 and decrypt_key(row[19]) else [],
            "native_integrations": json.loads(decrypt_key(row[20])) if len(row) > 20 and decrypt_key(row[20]) else []
        }
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_agent(agent_id: str, payload: dict):
    """
    What it does: Updates an existing agent's configuration dynamically based on the provided fields, and sends a real-time notification to the frontend.
    Args:
        agent_id (str): The ID of the agent to modify.
        payload (dict): The fields to update.
    Returns: The updated agent dictionary.
    """
    try:
        if not payload:
            return {}

        row = await agent_repository.update_agent(agent_id, payload)
        if not row:
            if not any(k in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints", "code_interpreter_enabled", "databases", "native_integrations", "parent_agent_id"] for k in payload.keys()):
                raise HTTPException(status_code=400, detail="No valid fields to update")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(row["workspace_id"]),
                title="Agent Settings Updated",
                message=f"Settings for agent '{row['name']}' were updated.",
                notification_type="agent_setting_updated"
            )
        except Exception as ne:
            logger.error(f"Failed to create settings update notification: {ne}")
            
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "llm_provider": row["llm_provider"],
            "llm_model": row["llm_model"],
            "embedding_model": row["embedding_model"],
            "chunk_strategy": row["chunk_strategy"],
            "system_prompt": row["system_prompt"],
            "output_format": row["output_format"],
            "api_key": decrypt_key(row["api_key"]) or "",
            "language": row["language"],
            "user_id": row["user_id"],
            "workspace_id": row["workspace_id"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "web_search_enabled": row["web_search_enabled"],
            "parent_agent_id": row.get("parent_agent_id"),
            "is_active": row["is_active"],
            "endpoints": row["endpoints"] if "endpoints" in row else [],
            "code_interpreter_enabled": row.get("code_interpreter_enabled", False),
            "databases": json.loads(decrypt_key(row["databases"])) if row.get("databases") and decrypt_key(row["databases"]) else [],
            "native_integrations": json.loads(decrypt_key(row["native_integrations"])) if row.get("native_integrations") and decrypt_key(row["native_integrations"]) else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        project_id = await agent_repository.create_agent_project(name, description, workspace_id, user_id)
        return {"status": "success", "id": project_id}
    except Exception as e:
        logger.error(f"Error creating agent project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_agent_projects(workspace_id: str):
    """
    What it does: Retrieves a list of all Multi-Agent Projects in a workspace.
    Args:
        workspace_id (str): The ID of the workspace.
    Returns: A list of project dictionaries.
    """
    try:
        rows = await agent_repository.get_agent_projects(workspace_id)
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


async def handle_get_project_sub_agents(project_id: str):
    """
    What it does: Gets all the individual AI agents that belong to a specific Multi-Agent Project.
    Args:
        project_id (str): The ID of the project.
    Returns: A list of agents belonging to that project.
    """
    try:
        rows = await agent_repository.get_project_sub_agents(project_id)
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
                "endpoints": row[17] if len(row) > 17 else [],
                "code_interpreter_enabled": row[18] if len(row) > 18 else False,
                "databases": json.loads(decrypt_key(row[19])) if len(row) > 19 and decrypt_key(row[19]) else [],
                "native_integrations": json.loads(decrypt_key(row[20])) if len(row) > 20 and decrypt_key(row[20]) else []
            })
        return agents
    except Exception as e:
        logger.error(f"Error fetching sub-agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_delete_agent_project(project_id: str):
    """
    What it does: Erases an entire Multi-Agent Project and cleans up all associated documents, chat messages, and agent data.
    Args:
        project_id (str): The ID of the project to destroy.
    Returns: A confirmation message upon success.
    """
    try:
        rowcount = await agent_repository.delete_agent_project(project_id)
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
            
        return {"status": "success", "message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_project_tools(project_id: str):
    """
    What it does: Fetches all custom tools associated with an Agent Project.
    Args:
        project_id (str): The ID of the project.
    Returns: A list of tools.
    """
    try:
        rows = await agent_repository.get_project_tools(project_id)
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


async def handle_update_project_tool(tool_id: str, name: str, config: dict):
    """
    What it does: Updates the name and JSON configuration of a custom project tool.
    Args:
        tool_id (str): The ID of the tool.
        name (str): The new name of the tool.
        config (dict): The new configuration data.
    Returns: A success dictionary.
    """
    try:
        rowcount = await agent_repository.update_project_tool(tool_id, name, config)
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Tool not found")
            
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_project_tool(project_id: str, name: str, config: dict):
    """
    What it does: Creates a brand new custom tool for a project.
    Args:
        project_id (str): The ID of the project to attach the tool to.
        name (str): The name of the new tool.
        config (dict): The JSON configuration of the tool.
    Returns: A dictionary with the new tool's ID.
    """
    try:
        tool_id = await agent_repository.create_project_tool(project_id, name, config)
        if not tool_id:
            raise HTTPException(status_code=404, detail="Project not found")
            
        return {"status": "success", "id": tool_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
