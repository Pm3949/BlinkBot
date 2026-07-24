"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core business logic handler for managing AI Agents, 
Agent Projects (multi-agent collections), and Custom Project Tools in RAGMate.

From top to bottom, this handler coordinates:
1. Imports: Brings in json parsing, optional type hinting, FastAPI exceptions, 
   the decryption module for encrypted API keys, and the database query layer.
2. Agents Listing & Management:
   - `handle_get_agents`: Fetches and formats all agents belonging to a workspace.
   - `handle_create_agent`: Validates, inserts, and encrypts credentials for a new agent.
   - `handle_update_agent`: Modifies configuration details for an agent and emits notifications.
3. Multi-Agent Projects management:
   - `handle_create_agent_project`: Registers a container for grouped routing agents.
   - `handle_get_agent_projects`: Lists projects by workspace.
   - `handle_get_project_sub_agents`: Finds sub-agents nested inside a parent project.
   - `handle_delete_agent_project`: Removes projects from the system database.
4. Custom Tools Management:
   - `handle_get_project_tools`: Fetches custom integrations configured for a project.
   - `handle_update_project_tool`: Alters configs (masking credentials in logs).
   - `handle_create_project_tool`: Creates custom tools for multi-agent workflows.

All methods are asynchronous (`async def`) and run database tasks using 
non-blocking execution threads, raising clean HTTP status codes upon errors.
"""

import json  # Import utility to convert Python objects to JSON strings and vice-versa
from typing import Optional  # Type hinting wrapper to mark parameters as optional (nullable)
from fastapi import HTTPException  # FastAPI class to return custom HTTP responses to client errors
from core.security import decrypt_key  # Import local decryption function to decrypt encrypted API keys
from db import agent_repository  # Database communication layer for agent queries

# Logging utilities
from utils.logger import get_department_logger

# Scoping a dedicated logger to record "agent" department transactions
logger = get_department_logger("agent")


async def handle_get_agents(workspace_id: str, include_gateways: bool = False):
    """
    Retrieves all AI agents configured within a given workspace.
    Processes the raw database rows and formats them into clean JSON-serializable dictionaries.

    Parameters:
        workspace_id (str): The unique database UUID identifying the target workspace.
        include_gateways (bool): If True, returns coordinator/gateway router agents too. Default is False.

    Returns:
        list: A list of dictionary objects representing each agent in the workspace.

    Exceptions Raised:
        HTTPException(500): Raised if an database query or parsing error occurs.
    """
    # Log information indicating retrieval is initiated
    logger.info(f"Retrieving agents for workspace ID: {workspace_id} (include_gateways: {include_gateways})")
    try:
        # Query database rows through the repository
        logger.debug(f"Querying agent_repository.get_agents with workspace_id: {workspace_id}")
        rows = await agent_repository.get_agents(workspace_id, include_gateways)
        logger.debug(f"Retrieved {len(rows)} agent records from database.")
        
        # Loop through each row tuple and map fields to a dictionary structure
        agents = []
        for idx, row in enumerate(rows):
            logger.debug(f"Parsing agent record index {idx} (ID: {row[0]}, Name: {row[1]})")
            agents.append({
                "id": row[0],                                                # Unique Agent UUID
                "name": row[1],                                              # Display name of the agent
                "description": row[2],                                      # Short description of the agent's purpose
                "llm_provider": row[3],                                      # LLM provider (e.g. groq, openai, gemini)
                "llm_model": row[4],                                         # Specific model name (e.g. gpt-4o, llama-3.3)
                "embedding_model": row[5],                                   # Model used for RAG vectors (e.g. text-embedding-3)
                "chunk_strategy": row[6],                                    # Text splitting method (e.g. sentence, token)
                "system_prompt": row[7],                                     # Core system prompt instructions for the LLM
                "api_key": decrypt_key(row[8]) or "",                        # Decrypted custom API key for this agent if set
                "language": row[9],                                          # Language preference (e.g. 'en')
                "user_id": row[10],                                          # Owner's user UUID
                "workspace_id": row[11],                                     # Workspace ID
                "created_at": row[12].isoformat() if row[12] else None,      # ISO 8601 formatted date string
                "web_search_enabled": row[13],                               # Boolean flag enabling DuckDuckGo search tool
                "project_id": row[14],                                       # Multi-Agent project UUID container if applicable
                "is_active": row[15],                                        # Active status flag (boolean)
                "output_format": row[16],                                    # Strict formatting instructions (e.g. JSON, markdown)
                "endpoints": row[17] if len(row) > 17 else [],               # Custom REST webhook calls registered to agent
                "code_interpreter_enabled": row[18] if len(row) > 18 else False, # True to allow running python scripts locally
                "databases": json.loads(decrypt_key(row[19])) if len(row) > 19 and decrypt_key(row[19]) else [],  # Decrypted custom DB connection list
                "native_integrations": json.loads(decrypt_key(row[20])) if len(row) > 20 and decrypt_key(row[20]) else []  # Decrypted native API keys (Slack, etc.)
            })
        
        # Log successful completion and count
        logger.info(f"Successfully processed and returned {len(agents)} agents.")
        return agents
    except Exception as e:
        # Catch errors, log details, and raise 500 status response to the client
        logger.error(f"Error fetching agents for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_agent(payload_data: dict):
    """
    Creates a new AI Agent record in the database using the provided payload.

    Parameters:
        payload_data (dict): Dictionary payload containing properties to configure the agent.

    Returns:
        dict: A dictionary structure of the newly created agent record.

    Exceptions Raised:
        HTTPException(500): Raised if the database insertion fails or returns empty rows.
    """
    # Sanitize payload for logging (mask the API keys to keep logs secure)
    sanitized_payload = payload_data.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Creating a new agent with payload: {sanitized_payload}")
    
    try:
        # Call the repository to insert rows into the 'agents' database table
        logger.debug("Executing database creation query in agent_repository...")
        row = await agent_repository.create_agent(payload_data)
        
        # If the database failed to return the inserted record
        if not row:
            logger.error("Failed to create agent: database insertion returned no row.")
            raise HTTPException(status_code=500, detail="Failed to create agent")
            
        # Log insertion success
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
    """
    Updates properties on an existing AI Agent.
    Sends a system notification upon successful update.

    Parameters:
        agent_id (str): The unique database UUID of the agent to update.
        payload (dict): A dictionary of key-value properties to update.

    Returns:
        dict: The updated agent details.

    Exceptions Raised:
        HTTPException(400): Raised if the payload contains no valid fields.
        HTTPException(404): Raised if the agent is not found.
        HTTPException(500): Raised if the database fails to execute.
    """
    # Sanitize parameters for secure logging
    sanitized_payload = payload.copy()
    if "api_key" in sanitized_payload:
        sanitized_payload["api_key"] = "[MASKED]"
    logger.info(f"Updating agent ID: {agent_id} with payload: {sanitized_payload}")
    
    try:
        # Return early if payload dictionary is completely empty
        if not payload:
            logger.warning("Empty payload received for agent update. Aborting early.")
            return {}

        # Call repository update method
        logger.debug(f"Executing database update query for agent ID: {agent_id}")
        row = await agent_repository.update_agent(agent_id, payload)
        
        # If the database returns no row, indicating agent doesn't exist
        if not row:
            valid_keys = ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints", "code_interpreter_enabled", "databases", "native_integrations", "parent_agent_id"]
            if not any(k in valid_keys for k in payload.keys()):
                logger.warning(f"Update rejected: No valid fields found in payload keys: {list(payload.keys())}")
                raise HTTPException(status_code=400, detail="No valid fields to update")
            logger.error(f"Update failed: Agent with ID {agent_id} not found.")
            raise HTTPException(status_code=404, detail="Agent not found")
            
        # Trigger an in-app workspace notification about the update
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
            # We catch notification errors separately so a failure in the notification module doesn't crash the main update transaction
            logger.error(f"Failed to create settings update notification: {str(ne)}", exc_info=True)
            
        # Log success and return the newly saved data
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
    """
    Creates a new Multi-Agent Project container record.

    Parameters:
        name (str): The display name/title of the project.
        description (str): Explanatory text of the project.
        workspace_id (str): The workspace UUID.
        user_id (str): The creator's user UUID.

    Returns:
        dict: A dictionary structure indicating success and containing the new project ID.

    Exceptions Raised:
        HTTPException(500): Raised if project creation fails in the database.
    """
    logger.info(f"Creating Multi-Agent Project: '{name}' in workspace: {workspace_id} by user: {user_id}")
    try:
        # Call database query layer to create a project entry
        logger.debug("Executing database creation query in agent_repository.create_agent_project...")
        project_id = await agent_repository.create_agent_project(name, description, workspace_id, user_id)
        
        # Log success and return the project_id
        logger.info(f"Multi-Agent Project successfully created. Project ID: {project_id}")
        return {"status": "success", "id": project_id}
    except Exception as e:
        logger.error(f"Error creating agent project: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_agent_projects(workspace_id: str):
    """
    Fetches all Multi-Agent projects configured in a given workspace.

    Parameters:
        workspace_id (str): The target workspace UUID.

    Returns:
        list: A list of formatted project dictionary items.

    Exceptions Raised:
        HTTPException(500): Raised if queries fail.
    """
    logger.info(f"Fetching all Multi-Agent Projects for workspace ID: {workspace_id}")
    try:
        # Retrieve raw database rows
        logger.debug("Executing database fetch query in agent_repository.get_agent_projects...")
        rows = await agent_repository.get_agent_projects(workspace_id)
        logger.debug(f"Retrieved {len(rows)} project records from database.")
        
        # Format database tuples into clear JSON-serializable dictionary items
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],                                                # Project UUID
                "name": row[1],                                              # Project Name
                "description": row[2],                                      # Project Description
                "status": row[3],                                            # Project Status (e.g. active, archived)
                "created_at": row[4].isoformat() if row[4] else None,        # Registration timestamp
                "blueprint": row[5]                                          # Layout/Blueprint structure configurations
            })
        
        # Return formatted project registry
        logger.info(f"Successfully returned {len(projects)} agent projects.")
        return projects
    except Exception as e:
        logger.error(f"Error fetching agent projects for workspace {workspace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_project_sub_agents(project_id: str):
    """
    Retrieves all sub-agents linked inside a specific multi-agent project context.

    Parameters:
        project_id (str): The unique database UUID of the project container.

    Returns:
        list: A list of dictionary objects representing the project's sub-agents.

    Exceptions Raised:
        HTTPException(500): Raised if retrieval or parsing crashes.
    """
    logger.info(f"Fetching all sub-agents belonging to project ID: {project_id}")
    try:
        # Query sub-agents matching project_id
        logger.debug("Executing database fetch query in agent_repository.get_project_sub_agents...")
        rows = await agent_repository.get_project_sub_agents(project_id)
        logger.debug(f"Retrieved {len(rows)} sub-agent records for project ID: {project_id}")
        
        # Format raw database row tuples
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
                "parent_agent_id": row[14],                                  # Links to supervisor coordinator agent
                "is_active": row[15],
                "output_format": row[16],
                "endpoints": row[17] if len(row) > 17 else [],
                "code_interpreter_enabled": row[18] if len(row) > 18 else False,
                "databases": json.loads(decrypt_key(row[19])) if len(row) > 19 and decrypt_key(row[19]) else [],
                "native_integrations": json.loads(decrypt_key(row[20])) if len(row) > 20 and decrypt_key(row[20]) else []
            })
            
        # Return parsed list
        logger.info(f"Successfully processed {len(agents)} sub-agents for project {project_id}.")
        return agents
    except Exception as e:
        logger.error(f"Error fetching sub-agents for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_delete_agent_project(project_id: str):
    """
    Deletes a Multi-Agent project container.

    Parameters:
        project_id (str): The unique database UUID of the project to remove.

    Returns:
        dict: A dictionary object indicating deletion success.

    Exceptions Raised:
        HTTPException(404): Raised if the target project doesn't exist.
        HTTPException(500): Raised if SQL transactions crash.
    """
    logger.info(f"Attempting to delete agent project ID: {project_id}")
    try:
        # Call database query layer to execute project removal
        logger.debug("Executing database delete query in agent_repository.delete_agent_project...")
        rowcount = await agent_repository.delete_agent_project(project_id)
        
        # If no rows were affected (meaning no matching project was found)
        if rowcount == 0:
            logger.warning(f"Delete rejected: Project with ID {project_id} not found.")
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Log success and return success payload
        logger.info(f"Project ID {project_id} successfully deleted.")
        return {"status": "success", "message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent project ID {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_project_tools(project_id: str):
    """
    Retrieves all custom webhook actions and tools registered inside a project.

    Parameters:
        project_id (str): The unique database UUID identifying the project context.

    Returns:
        list: A list of dictionary objects representing tools configurations.

    Exceptions Raised:
        HTTPException(500): Raised if fetching query crashes.
    """
    logger.info(f"Fetching all custom tools for project ID: {project_id}")
    try:
        # Fetch raw database custom tool rows
        logger.debug("Executing database fetch query in agent_repository.get_project_tools...")
        rows = await agent_repository.get_project_tools(project_id)
        logger.debug(f"Retrieved {len(rows)} tool records for project ID: {project_id}")
        
        # Parse database tuples
        tools = []
        for row in rows:
            tools.append({
                "id": row[0],                                                # Tool UUID
                "name": row[1],                                              # Tool Display Name
                "config": row[2] if isinstance(row[2], dict) else {},        # Configuration settings (headers, credentials, URLs)
                "blueprint_tool_id": row[3]                                  # Maps template ID if loaded from marketplace blueprint
            })
            
        # Log and return listing
        logger.info(f"Successfully returned {len(tools)} tools for project {project_id}.")
        return tools
    except Exception as e:
        logger.error(f"Error fetching tools for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_project_tool(tool_id: str, name: str, config: dict):
    """
    Updates the configuration configurations and naming for an existing project tool.

    Parameters:
        tool_id (str): The database UUID of the tool to update.
        name (str): The updated name/label of the custom tool.
        config (dict): A dictionary payload containing settings parameters.

    Returns:
        dict: A dictionary structure indicating execution success.

    Exceptions Raised:
        HTTPException(404): Raised if the target tool cannot be resolved.
        HTTPException(500): Raised if SQL update transaction crashes.
    """
    # Sanitize credentials inside config for secure log prints
    sanitized_config = config.copy()
    for field in ["api_key", "password", "token", "key"]:
        if field in sanitized_config:
            sanitized_config[field] = "[MASKED]"
    logger.info(f"Updating custom tool ID: {tool_id} (New Name: '{name}', Config: {sanitized_config})")
    
    try:
        # Call repository update method
        logger.debug("Executing database update query in agent_repository.update_project_tool...")
        rowcount = await agent_repository.update_project_tool(tool_id, name, config)
        
        # If no tool matching tool_id is found
        if rowcount == 0:
            logger.warning(f"Update rejected: Tool ID {tool_id} not found.")
            raise HTTPException(status_code=404, detail="Tool not found")
            
        # Log success
        logger.info(f"Tool ID {tool_id} successfully updated.")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project tool {tool_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_project_tool(project_id: str, name: str, config: dict):
    """
    Creates and registers a custom webhook or action tool for a project.

    Parameters:
        project_id (str): The target container project UUID.
        name (str): The display name/label of the tool.
        config (dict): The configuration settings (headers, credentials).

    Returns:
        dict: A dictionary containing success status and the new Tool ID.

    Exceptions Raised:
        HTTPException(404): Raised if the target project doesn't exist.
        HTTPException(500): Raised if database insert crashes.
    """
    # Sanitize logs
    sanitized_config = config.copy()
    for field in ["api_key", "password", "token", "key"]:
        if field in sanitized_config:
            sanitized_config[field] = "[MASKED]"
    logger.info(f"Creating a new custom tool for project ID: {project_id} (Name: '{name}', Config: {sanitized_config})")
    
    try:
        # Call database insert script in repository
        logger.debug("Executing database insertion in agent_repository.create_project_tool...")
        tool_id = await agent_repository.create_project_tool(project_id, name, config)
        
        # If insertion returns empty tool_id, signifying target project doesn't exist
        if not tool_id:
            logger.warning(f"Creation rejected: Project ID {project_id} not found.")
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Log success and return
        logger.info(f"New custom tool successfully created. Tool ID: {tool_id}")
        return {"status": "success", "id": tool_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tool for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
