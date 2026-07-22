import json
from typing import Optional
from fastapi import HTTPException
from core.security import decrypt_key
from db import agent_repository

from utils.logger import get_department_logger

logger = get_department_logger("agent")

async def handle_get_agents(workspace_id: str, include_gateways: bool = False):
    logger.info(f"Retrieving agents for workspace ID: {workspace_id} (include_gateways: {include_gateways})")
    try:
        logger.debug(f"Querying agent_repository.get_agents with workspace_id: {workspace_id}")
        rows = await agent_repository.get_agents(workspace_id, include_gateways)
        logger.debug(f"Retrieved {len(rows)} agent records from database.")
        
        agents = []
        for idx, row in enumerate(rows):
            logger.debug(f"Parsing agent record index {idx} (ID: {row[0]}, Name: {row[1]})")
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
        logger.info(f"Successfully processed and returned {len(agents)} agents.")
        return agents
    except Exception as e:
        logger.error(f"Error fetching agents for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_agent(payload_data: dict):
    # Mask API key in debug logs
    sanitized_payload = payload_data.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Creating a new agent with payload: {sanitized_payload}")
    
    try:
        logger.debug("Executing database creation query in agent_repository...")
        row = await agent_repository.create_agent(payload_data)
        if not row:
            logger.error("Failed to create agent: database insertion returned no row.")
            raise HTTPException(status_code=500, detail="Failed to create agent")
            
        logger.info(f"Agent successfully created. New Agent ID: {row[0]}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_agent(agent_id: str, payload: dict):
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Updating agent ID: {agent_id} with payload: {sanitized_payload}")
    
    try:
        if not payload:
            logger.warning("Empty payload received for agent update. Aborting early.")
            return {}

        logger.debug(f"Executing database update query for agent ID: {agent_id}")
        row = await agent_repository.update_agent(agent_id, payload)
        if not row:
            valid_keys = ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints", "code_interpreter_enabled", "databases", "native_integrations", "parent_agent_id"]
            if not any(k in valid_keys for k in payload.keys()):
                logger.warning(f"Update rejected: No valid fields found in payload keys: {list(payload.keys())}")
                raise HTTPException(status_code=400, detail="No valid fields to update")
            logger.error(f"Update failed: Agent with ID {agent_id} not found.")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        logger.debug("Triggering agent update dashboard notification...")
        try:
            from handlers.notification_handler import create_notification
            await create_notification(
                workspace_id=str(row["workspace_id"]),
                title="Agent Settings Updated",
                message=f"Settings for agent '{row['name']}' were updated.",
                notification_type="agent_setting_updated"
            )
            logger.info("Agent settings update notification created and broadcast.")
        except Exception as ne:
            logger.error(f"Failed to create settings update notification: {str(ne)}", exc_info=True)
            
        logger.info(f"Agent ID {agent_id} successfully updated.")
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
        logger.error(f"Error updating agent ID {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_agent_project(name: str, description: str, workspace_id: str, user_id: str):
    logger.info(f"Creating Multi-Agent Project: '{name}' in workspace: {workspace_id} by user: {user_id}")
    try:
        logger.debug("Executing database creation query in agent_repository.create_agent_project...")
        project_id = await agent_repository.create_agent_project(name, description, workspace_id, user_id)
        logger.info(f"Multi-Agent Project successfully created. Project ID: {project_id}")
        return {"status": "success", "id": project_id}
    except Exception as e:
        logger.error(f"Error creating agent project: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_agent_projects(workspace_id: str):
    logger.info(f"Fetching all Multi-Agent Projects for workspace ID: {workspace_id}")
    try:
        logger.debug("Executing database fetch query in agent_repository.get_agent_projects...")
        rows = await agent_repository.get_agent_projects(workspace_id)
        logger.debug(f"Retrieved {len(rows)} project records from database.")
        
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
        logger.info(f"Successfully returned {len(projects)} agent projects.")
        return projects
    except Exception as e:
        logger.error(f"Error fetching agent projects for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_project_sub_agents(project_id: str):
    logger.info(f"Fetching all sub-agents belonging to project ID: {project_id}")
    try:
        logger.debug("Executing database fetch query in agent_repository.get_project_sub_agents...")
        rows = await agent_repository.get_project_sub_agents(project_id)
        logger.debug(f"Retrieved {len(rows)} sub-agent records for project ID: {project_id}")
        
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
        logger.info(f"Successfully processed {len(agents)} sub-agents for project {project_id}.")
        return agents
    except Exception as e:
        logger.error(f"Error fetching sub-agents for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_delete_agent_project(project_id: str):
    logger.info(f"Attempting to delete agent project ID: {project_id}")
    try:
        logger.debug("Executing database delete query in agent_repository.delete_agent_project...")
        rowcount = await agent_repository.delete_agent_project(project_id)
        if rowcount == 0:
            logger.warning(f"Delete rejected: Project with ID {project_id} not found.")
            raise HTTPException(status_code=404, detail="Project not found")
            
        logger.info(f"Project ID {project_id} successfully deleted.")
        return {"status": "success", "message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent project ID {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_project_tools(project_id: str):
    logger.info(f"Fetching all custom tools for project ID: {project_id}")
    try:
        logger.debug("Executing database fetch query in agent_repository.get_project_tools...")
        rows = await agent_repository.get_project_tools(project_id)
        logger.debug(f"Retrieved {len(rows)} tool records for project ID: {project_id}")
        
        tools = []
        for row in rows:
            tools.append({
                "id": row[0],
                "name": row[1],
                "config": row[2] if isinstance(row[2], dict) else {},
                "blueprint_tool_id": row[3]
            })
        logger.info(f"Successfully returned {len(tools)} tools for project {project_id}.")
        return tools
    except Exception as e:
        logger.error(f"Error fetching tools for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_project_tool(tool_id: str, name: str, config: dict):
    # Mask API key/credentials inside the tool config in debug log
    sanitized_config = config.copy()
    for field in ["api_key", "password", "token", "key"]:
        if field in sanitized_config:
            sanitized_config[field] = "[MASKED]"
    logger.info(f"Updating custom tool ID: {tool_id} (New Name: '{name}', Config: {sanitized_config})")
    
    try:
        logger.debug("Executing database update query in agent_repository.update_project_tool...")
        rowcount = await agent_repository.update_project_tool(tool_id, name, config)
        if rowcount == 0:
            logger.warning(f"Update rejected: Tool ID {tool_id} not found.")
            raise HTTPException(status_code=404, detail="Tool not found")
            
        logger.info(f"Tool ID {tool_id} successfully updated.")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project tool {tool_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_project_tool(project_id: str, name: str, config: dict):
    sanitized_config = config.copy()
    for field in ["api_key", "password", "token", "key"]:
        if field in sanitized_config:
            sanitized_config[field] = "[MASKED]"
    logger.info(f"Creating a new custom tool for project ID: {project_id} (Name: '{name}', Config: {sanitized_config})")
    
    try:
        logger.debug("Executing database insertion in agent_repository.create_project_tool...")
        tool_id = await agent_repository.create_project_tool(project_id, name, config)
        if not tool_id:
            logger.warning(f"Creation rejected: Project ID {project_id} not found.")
            raise HTTPException(status_code=404, detail="Project not found")
            
        logger.info(f"New custom tool successfully created. Tool ID: {tool_id}")
        return {"status": "success", "id": tool_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tool for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
