"""
================================================================================
META-AGENT DEPLOYMENT AND BLUEPRINT REPOSITORY LAYER (meta_agent_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module handles the database deployment of multi-agent blueprints (defined via
`AgentBlueprint`). When a user designs or generates an AI agent network, the schema
blueprint is parsed, verified, and mapped into corresponding databases tables:
1. `agent_projects`: Stores project metadata and serialized blueprint JSON.
2. `agents`: Automatically registers standard system agents (Network Manager, General Assistant)
   and dynamically parses/inserts custom sub-agents.
3. `documents`: Registers stubs for enabled knowledge bases.
4. `agent_tools`: Registers custom integrations (APIs, query models, searchers).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `json`: Standard JSON encoder.
   - `AgentBlueprint`: Pydantic schema layout configuration (from `meta_agent_schemas.py`).
   - `get_db_cursor_async` and `run_in_threadpool`: Core DB access interfaces.
   - Default prompts (`NETWORK_MANAGER_SYSTEM_PROMPT`, `GENERAL_ASSISTANT_SYSTEM_PROMPT`).

2. Repository Functions:
   - `deploy_agent_blueprint_to_db(...)`: Deploys the blueprint configuration.
     - Saves the root project configuration.
     - Spawns the central router coordinator (Network Manager) and default greetings (General Assistant).
     - Loops through required knowledge bases, creating file placeholder rows for those marked enabled.
     - Iterates over required tools, updating configuration settings and storing them.
     - Inserts the custom sub-agents whitelisted in the blueprint. Stores their database-generated UUIDs
       in a temporary map (`agent_id_map`) keying off their blueprint ID strings.
     - Re-iterates over sub-agents to resolve parent relationships (parent pointers update). If a parent ID
       is not mapped, it defaults to the Network Manager router ID.
     - Queries created tools to map blueprint tool IDs to final database tool IDs.
     - Returns a success status containing the workspace mapping IDs.
"""

import json
from meta_agent_schemas import AgentBlueprint
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from prompts.system_agent_prompts import NETWORK_MANAGER_SYSTEM_PROMPT, GENERAL_ASSISTANT_SYSTEM_PROMPT

async def deploy_agent_blueprint_to_db(workspace_id: str, user_id: str, blueprint: AgentBlueprint, config_data: dict):
    """
    Deploys a generated multi-agent blueprint network into the database.

    Purpose:
        Takes an abstract multi-agent network configuration (blueprint) and instantiates it
        within the database. It handles creating the parent project, spawning default system agents,
        creating documents stubs for files, setting up tools, mapping sub-agents, and linking
        sub-agents in a parent-child hierarchy.

    Parameters:
        workspace_id (str): The unique ID of the workspace where the project is deployed.
        user_id (str): The unique database identifier of the user initiating the deployment.
        blueprint (AgentBlueprint): A Pydantic schema detailing project metadata, tools, and sub-agents.
        config_data (dict): User configuration data defining which tools and knowledge bases are active.

    Returns:
        dict: A status payload containing:
            - status (str): "success"
            - project_id (str): The UUID of the created project.
            - agent_id_map (dict): Maps blueprint sub-agent IDs to database UUID strings.
            - tool_id_map (dict): Maps blueprint tool IDs to database primary key IDs.

    Side Effects / State Changes:
        - Writes one row to the `agent_projects` table.
        - Writes multiple rows to the `agents`, `documents`, and `agent_tools` tables.
        - Commits all modifications as an atomic SQL transaction block (commit=True).

    Errors / Exceptions:
        - May raise database constraint violations or insertion errors.
    """
    # Open database connection in a write transaction (commit=True).
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Create the parent agent project record.
        # Store the serialized blueprint configuration inside `blueprint_json`.
        # `model_dump_json()` parses Pydantic model attributes to a JSON string.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_projects (workspace_id, name, description, status, blueprint_json)
            VALUES (%s, %s, %s, 'deployed', %s)
            RETURNING id;
            """,
            (workspace_id, blueprint.project_name, blueprint.description, blueprint.model_dump_json())
        )
        # Fetch the project UUID.
        project_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Step 2: Create the permanent "Network Manager" (the central routing gateway agent).
        # We pass default presets for providers ("groq"), models ("llama-3.3-70b-versatile"),
        # and embedding models ("all-MiniLM-L6-v2") to configure the gateway.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, output_format, api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            ("Network Manager", "The central router agent for this network.", "groq", "llama-3.3-70b-versatile", "all-MiniLM-L6-v2", "sentence", NETWORK_MANAGER_SYSTEM_PROMPT, "", "", "en", user_id, workspace_id, False, project_id, None, "[]", False, "[]", "[]")
        )
        # Fetch the Network Manager's database UUID.
        manager_id = (await run_in_threadpool(cursor.fetchone))[0]

        # Step 3: Create the permanent "General Assistant" (the welcoming greeting sub-agent).
        # We link this sub-agent to the Network Manager by setting its parent_agent_id to `manager_id`.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, output_format, api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            ("General Assistant", "A friendly greeting and welcome assistant.", "groq", "llama-3.3-70b-versatile", "all-MiniLM-L6-v2", "sentence", GENERAL_ASSISTANT_SYSTEM_PROMPT, "", "", "en", user_id, workspace_id, False, project_id, manager_id, "[]", False, "[]", "[]")
        )

        # Step 4: Create document placeholders (knowledge bases).
        # Fetch knowledge activation flags from `config_data`.
        enabled_kb = config_data.get("enabled_knowledge", {})
        # Loop through knowledge blocks requested by the blueprint.
        for kb in blueprint.required_knowledge:
            # If the user enabled this knowledge source, create a placeholder document row in 'pending' status.
            # Background workers will later fetch and parse the files.
            if enabled_kb.get(kb.id):
                await run_in_threadpool(
                    cursor.execute,
                    """
                    INSERT INTO documents (project_id, blueprint_knowledge_id, filename, type, source_uri, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """,
                    (project_id, kb.id, kb.name, kb.type, "")
                )

        # Step 5: Configure and deploy agent tools.
        # Fetch activation maps and custom settings from `config_data`.
        enabled_tools = config_data.get("enabled_tools", {})
        tools_config = config_data.get("tools", {})
        # Loop through tools requested by the blueprint.
        for tool in blueprint.required_tools:
            # Fetch custom settings for this tool, defaulting to an empty dict.
            tool_config_data = tools_config.get(tool.id, {})
            # Set whether this tool is active based on user inputs.
            tool_config_data["is_enabled"] = bool(enabled_tools.get(tool.id))
            
            # Ensure safe fallback schema attributes are set to prevent downstream runtime key errors.
            if "query_format" not in tool_config_data:
                tool_config_data["query_format"] = "{}"
            if "headers" not in tool_config_data:
                tool_config_data["headers"] = "{}"
                
            # Insert the tool configuration, converting config dictionary parameters to a JSON string.
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (project_id, workspace_id, tool.id, tool.name, json.dumps(tool_config_data))
            )

        # Step 6: Deploy custom sub-agents.
        # Keep a dictionary mapping temporary blueprint ID strings to final database UUIDs.
        agent_id_map = {}
        for sub_agent in blueprint.sub_agents:
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO agents (name, description, system_prompt, output_format, user_id, workspace_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    sub_agent.role, 
                    sub_agent.goal, 
                    sub_agent.backstory,
                    sub_agent.output_format_instructions,
                    user_id, 
                    workspace_id, 
                    project_id
                )
            )
            # Fetch the generated database UUID.
            real_uuid = (await run_in_threadpool(cursor.fetchone))[0]
            # Link the temporary blueprint ID key to the database UUID.
            agent_id_map[sub_agent.id] = real_uuid

        # Step 7: Resolve parent-child hierarchical links between sub-agents.
        # Re-iterate over sub-agents since some children might have been defined before their parents.
        for sub_agent in blueprint.sub_agents:
            real_uuid = agent_id_map[sub_agent.id]
            # If the sub-agent defines a parent that exists in our mapped IDs dictionary, resolve it.
            # Otherwise, fall back to linking it directly to the Network Manager router gateway.
            if getattr(sub_agent, 'parent_agent_id', None) and sub_agent.parent_agent_id in agent_id_map:
                parent_real_uuid = agent_id_map[sub_agent.parent_agent_id]
            else:
                parent_real_uuid = manager_id
                
            # Perform query update to link the parent pointer.
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE agents SET parent_agent_id = %s WHERE id = %s
                """,
                (parent_real_uuid, real_uuid)
            )

        # Step 8: Build tool ID mapping lists.
        # Fetch the created tools to map blueprint IDs back to database primary key IDs.
        await run_in_threadpool(cursor.execute, "SELECT blueprint_tool_id, id FROM agent_tools WHERE project_id = %s", (project_id,))
        # Map values using dictionary comprehension.
        tool_id_map = {row[0]: row[1] for row in (await run_in_threadpool(cursor.fetchall))}

        # Return success status details mapping the entire created layout.
        return {
            "status": "success", 
            "project_id": project_id, 
            "agent_id_map": agent_id_map,
            "tool_id_map": tool_id_map
        }

