"""
================================================================================
AGENT AND WORKSPACE DATABASE REPOSITORY LAYER (agent_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) / repository layer for managing
AI Agents, Agent Projects (Networks), and Agent Tools within the RAGMate backend.
It contains functions to perform CRUD (Create, Read, Update, Delete) operations
on the `agents`, `agent_projects`, and `agent_tools` tables in the PostgreSQL database.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `json`: Standard Python library for serializing/deserializing JSON. Used here
     to convert list/dict configurations (like tools, endpoints, databases) to strings
     before storing them in the database.
   - `get_db_cursor_async`: A custom asynchronous context manager that acquires a
     database cursor and manages the lifecycle of SQL transactions.
   - `run_in_threadpool`: A FastAPI utility to execute blocking synchronous database
     adapter tasks (e.g., psycopg2 cursor functions) in a background thread.
   - `encrypt_key`: Security function to encrypt sensitive information (API keys,
     database credentials, third-party integration secrets) before writing them to the DB.
   - `GENERAL_ASSISTANT_SYSTEM_PROMPT`: The default system prompt template for
     general assistant agents.

2. Repository Functions:
   - `get_agents(...)`: Fetches all agents in a workspace, optionally including gateway/router agents.
   - `create_agent(...)`: Inserts a new agent record, encrypting keys and serializing JSON payloads.
   - `update_agent(...)`: Dynamically builds an SQL UPDATE statement to modify modified agent properties.
   - `create_agent_project(...)`: Creates a new agent network/project, initializing a "Network Manager"
     router agent and a default "General Assistant" sub-agent automatically.
   - `get_agent_projects(...)`: Retrieves all projects in a workspace.
   - `get_project_sub_agents(...)`: Retrieves all sub-agents linked to a project.
   - `delete_agent_project(...)`: Cascading delete operation. Clears embeddings, documents, chats,
     messages, agents, and the project record in a structured transaction.
   - `get_project_tools(...)`: Gets custom tools configured for a project.
   - `update_project_tool(...)`: Updates a tool's name and JSON configuration.
   - `create_project_tool(...)`: Dynamically generates a slug/blueprint ID and inserts a custom tool.

CONCURRENCY & SECURITY PHILOSOPHY:
- Asynchronous Concurrency: Database adapters block on network operations. This script wraps
  blocking calls in `run_in_threadpool` to prevent stalls in FastAPI.
- Encryption-at-Rest: Sensitive fields such as `api_key`, `databases`, and `native_integrations`
  are encrypted using the `encrypt_key` helper before storage.
"""

import json
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from core.security import encrypt_key
from prompts.system_agent_prompts import GENERAL_ASSISTANT_SYSTEM_PROMPT

async def get_agents(workspace_id: str, include_gateways: bool = False):
    """
    Retrieves a list of agents associated with a given workspace ID.

    Purpose:
        Fetches agent details for configuration and listing. It can optionally filter out
        project-specific sub-agents and child agents depending on whether gateway agents are requested.

    Parameters:
        workspace_id (str): The unique ID of the workspace containing the agents.
        include_gateways (bool): If True, returns agents that are either standalone (project_id IS NULL)
                                 or parent/gateway agents (parent_agent_id IS NULL). If False, only
                                 returns standalone root agents. Defaults to False.

    Returns:
        list of tuples: A list of agent records matching the workspace filter, sorted newest first.

    Side Effects / State Changes:
        - None. Read-only database query.

    Errors / Exceptions:
        - May raise database-related errors (e.g. connectivity problems).
    """
    # Open a database connection using our async context manager.
    # Set commit=False since this is a read-only query.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # Determine the WHERE query condition based on whether we should include gateway/manager agents.
        # Project sub-agents have a non-null `project_id`. If include_gateways is True, we want to allow
        # agents where `project_id IS NULL` OR `parent_agent_id IS NULL` (meaning it's a top-level coordinator/gateway).
        # Otherwise, we restrict it strictly to standalone agents (`project_id IS NULL`).
        if include_gateways:
            condition = "WHERE workspace_id = %s AND (project_id IS NULL OR parent_agent_id IS NULL)"
        else:
            condition = "WHERE workspace_id = %s AND project_id IS NULL"
            
        # Execute the SELECT statement inside a thread pool because psycopg2's execution is blocking.
        # String interpolation is used here ONLY for the pre-defined safe WHERE condition string.
        # The dynamic `workspace_id` value is safely bound using parameters `%s` / `(workspace_id,)`.
        await run_in_threadpool(
            cursor.execute,
            f"""
            SELECT id, name, description, llm_provider, llm_model, 
                   embedding_model, chunk_strategy, system_prompt, 
                   api_key, language, user_id, workspace_id, created_at,
                   web_search_enabled, project_id, is_active, output_format,
                   endpoints, code_interpreter_enabled, databases, native_integrations
            FROM agents 
            {condition}
            ORDER BY created_at DESC
            """,
            (workspace_id,)
        )
        # Fetch and return all matching records asynchronously from the thread pool.
        return await run_in_threadpool(cursor.fetchall)


async def create_agent(payload_data: dict):
    """
    Creates a new agent in the database.

    Purpose:
        Inserts a new agent record into the `agents` table using the provided configuration
        parameters. Automatically handles key encryption and JSON serialization.

    Parameters:
        payload_data (dict): A dictionary containing agent configuration data:
            - name (str): The name of the agent.
            - description (str, optional): Summary of the agent's responsibilities.
            - llm_provider (str): The LLM service provider (e.g., OpenAI, Anthropic, Groq).
            - llm_model (str): Specific model to use (e.g., gpt-4, claude-3).
            - embedding_model (str, optional): Model for vector embeddings.
            - chunk_strategy (str, optional): Document chunking strategy (e.g., semantic, character).
            - system_prompt (str, optional): Custom instructions for the agent.
            - output_format (str, optional): Desired response format structure.
            - api_key (str, optional): Plaintext API key, which will be encrypted before storage.
            - language (str, optional): Language code (e.g. 'en').
            - user_id (str): User ID of the creator.
            - workspace_id (str): Associated workspace ID.
            - web_search_enabled (bool, optional): Enables web browsing access.
            - project_id (str, optional): Linked project/network ID if it's a sub-agent.
            - parent_agent_id (str, optional): Parent agent ID for hierarchical coordination.
            - endpoints (list, optional): Configured webhooks or API endpoints.
            - code_interpreter_enabled (bool, optional): Enables code execution sandbox.
            - databases (list, optional): SQL database configurations, encrypted.
            - native_integrations (list, optional): Third-party app integrations, encrypted.

    Returns:
        tuple: The newly created agent's row tuple.

    Side Effects / State Changes:
        - Writes a new record to the `agents` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database constraint violations or insertion errors.
    """
    # Open database connection with commit=True since we are modifying state by inserting a new record.
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, 
                              embedding_model, chunk_strategy, system_prompt, output_format, 
                              api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, llm_provider, llm_model, 
                      embedding_model, chunk_strategy, system_prompt, output_format, 
                      api_key, language, user_id, workspace_id, created_at, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations;
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
                # Protect credentials: the API key is encrypted using the core security module.
                encrypt_key(payload_data.get("api_key", "")), 
                payload_data.get("language", "en"), 
                payload_data.get("user_id"), 
                payload_data.get("workspace_id"), 
                payload_data.get("web_search_enabled", False), 
                payload_data.get("project_id"), 
                payload_data.get("parent_agent_id"), 
                # Convert structured arrays/lists into JSON strings for database compatibility.
                json.dumps(payload_data.get("endpoints", [])),
                payload_data.get("code_interpreter_enabled", False),
                # Databases and native integration configs may contain sensitive secrets, so we encrypt their JSON strings.
                encrypt_key(json.dumps(payload_data.get("databases", []))),
                encrypt_key(json.dumps(payload_data.get("native_integrations", [])))
            )
        )
        # Fetch the returning row containing the freshly generated record values (including its new UUID).
        return await run_in_threadpool(cursor.fetchone)


async def update_agent(agent_id: str, payload: dict):
    """
    Updates specific attributes of an existing agent.

    Purpose:
        Performs a dynamic SQL update depending on which keys are provided in the payload dictionary.
        Safely encrypts sensitive keys and encodes lists/dicts to JSON strings.

    Parameters:
        agent_id (str): The unique identifier of the agent to update.
        payload (dict): A dictionary containing fields to modify. Only valid keys
                        defined in the allowed list are updated.

    Returns:
        dict | None: A dictionary of the updated agent's attributes mapping column names to values,
                     or None if the update failed or no valid fields were supplied.

    Side Effects / State Changes:
        - Modifies an existing row in the `agents` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        set_clauses = []
        values = []
        # Loop through keys in the payload to dynamically build the SET clause of the SQL statement.
        for key, value in payload.items():
            # Check against a whitelist of valid fields to prevent writing to read-only columns (like id or created_at).
            if key in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints", "code_interpreter_enabled", "databases", "native_integrations", "parent_agent_id"]:
                set_clauses.append(f"{key} = %s")
                # Perform special handling (encryption, serialization) on specific data types.
                if key == "api_key":
                    values.append(encrypt_key(value))
                elif key == "endpoints":
                    values.append(json.dumps(value))
                elif key == "databases" or key == "native_integrations":
                    values.append(encrypt_key(json.dumps(value)))
                else:
                    values.append(value)
                
        # If no fields in the payload matched the whitelist, exit early without making database changes.
        if not set_clauses:
            return None
            
        # Append the agent_id to the query values list to bind to the final WHERE clause.
        values.append(agent_id)
        
        # Build the dynamic SQL query string.
        query = f"UPDATE agents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, output_format, api_key, language, user_id, workspace_id, created_at, web_search_enabled, is_active, endpoints, code_interpreter_enabled, databases, native_integrations, parent_agent_id;"
        
        # Execute the dynamic update query in a thread pool.
        await run_in_threadpool(cursor.execute, query, tuple(values))
        # Fetch the updated row record.
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            # Map the returned database tuple back into a friendly dictionary using the column descriptions.
            # cursor.description returns metadata about each selected column. desc[0] is the column name.
            columns = [desc[0] for desc in cursor.description]
            # zip combines column names and row values into pairs, then dict() builds the dictionary.
            return dict(zip(columns, row))
        return None


async def create_agent_project(name: str, description: str, workspace_id: str, user_id: str):
    """
    Creates an Agent Project (Network) and automatically initializes standard network agents.

    Purpose:
        Sets up an multi-agent collaboration network project by:
        1. Creating a record in `agent_projects`.
        2. Creating a "Network Manager" (gateway/router agent).
        3. Creating a default "General Assistant" sub-agent, linking it to the manager.

    Parameters:
        name (str): The name of the project network.
        description (str): Explanatory summary of the project.
        workspace_id (str): The ID of the workspace to create the project in.
        user_id (str): The ID of the user creating the project.

    Returns:
        str: The newly created project ID.

    Side Effects / State Changes:
        - Inserts one record in the `agent_projects` table.
        - Inserts two records in the `agents` table.
        - Commits all insertions atomically as a single transaction block.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection with commit=True since we are inserting multiple records.
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Create the Project record
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_projects (name, description, status, workspace_id, blueprint_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (name, description, "active", workspace_id, json.dumps({}))
        )
        # Extract the project ID generated by the database (index 0 of fetchone).
        project_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Step 2: Create the central gateway/coordinator agent called "Network Manager"
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, 
                              embedding_model, chunk_strategy, system_prompt, output_format, 
                              api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                "Network Manager", 
                "The central router agent for this network.", 
                "groq", 
                "llama-3.3-70b-versatile",
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
                None, # Has no parent since it is the root gateway coordinator.
                json.dumps([]),
                False,
                encrypt_key(json.dumps([])),
                encrypt_key(json.dumps([]))
            )
        )
        # Extract the Network Manager's agent ID.
        manager_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Step 3: Create the standard sub-agent called "General Assistant"
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agents (name, description, llm_provider, llm_model, 
                              embedding_model, chunk_strategy, system_prompt, output_format, 
                              api_key, language, user_id, workspace_id, web_search_enabled, project_id, parent_agent_id, endpoints, code_interpreter_enabled, databases, native_integrations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                "General Assistant", 
                "A friendly greeting and welcome assistant.", 
                "groq", 
                "llama-3.3-70b-versatile",
                "all-MiniLM-L6-v2", 
                "sentence", 
                GENERAL_ASSISTANT_SYSTEM_PROMPT, # Predefined prompt imported from our system agent prompts.
                "",
                encrypt_key(""), 
                "en", 
                user_id, 
                workspace_id, 
                False, # Web search is disabled by default.
                project_id, 
                manager_id, # Link this sub-agent to the Network Manager as its coordinator.
                json.dumps([]),
                False,
                encrypt_key(json.dumps([])),
                encrypt_key(json.dumps([]))
            )
        )

        # Return the overall project UUID so the frontend can redirect or query the new layout.
        return project_id


async def get_agent_projects(workspace_id: str):
    """
    Retrieves all agent projects (networks) in a specific workspace.

    Purpose:
        Fetches projects to render the networks lists on the admin or workspace dashboard.

    Parameters:
        workspace_id (str): The workspace identifier filtering the projects.

    Returns:
        list of tuples: A list of project record tuples, ordered from newest to oldest.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, description, status, created_at, blueprint_json
            FROM agent_projects 
            WHERE workspace_id = %s 
            ORDER BY created_at DESC
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_project_sub_agents(project_id: str):
    """
    Retrieves all agents associated with a specific agent project (network).

    Purpose:
        Used to render and configure the sub-agents structure layout inside a project network view.

    Parameters:
        project_id (str): The project identifier.

    Returns:
        list of tuples: A list of agent records linked to the project, sorted chronologically (oldest first).

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, description, llm_provider, llm_model, 
                   embedding_model, chunk_strategy, system_prompt, 
                   api_key, language, user_id, workspace_id, created_at,
                   web_search_enabled, parent_agent_id, is_active, output_format, endpoints, code_interpreter_enabled, databases, native_integrations
            FROM agents 
            WHERE project_id = %s 
            ORDER BY created_at ASC
            """,
            (project_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def delete_agent_project(project_id: str):
    """
    Deletes an agent project and performs cascading deletions of all downstream resources.

    Purpose:
        Clears out all database elements associated with a project. Because foreign key constraints
        might not cascade on all dynamic resources, we manually delete dependencies in order:
        1. Document embeddings linked to documents of agents in this project, or documents directly attached to the project.
        2. Documents of agents in this project or project-level documents.
        3. Chat messages belonging to chat sessions of agents in this project.
        4. Chat sessions belonging to agents in this project.
        5. Agents belonging to this project.
        6. The agent project record itself.

    Parameters:
        project_id (str): The ID of the project network to delete.

    Returns:
        int: The number of rows affected by the final project deletion query (typically 1).

    Side Effects / State Changes:
        - Permanently removes database rows across multiple tables.
        - Commits all deletions in a single transactional block (commit=True).

    Errors / Exceptions:
        - May raise database constraints violations if some references are not handled.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Delete document vector embeddings.
        # We select documents that are linked either directly to an agent belonging to the project
        # or attached directly to the project.
        await run_in_threadpool(
            cursor.execute,
            """
            DELETE FROM document_embeddings
            WHERE document_id IN (
                SELECT id FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
                OR project_id = %s
            )
            """, 
            (project_id, project_id)
        )
        
        # Step 2: Delete document metadata rows.
        await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s) OR project_id = %s", (project_id, project_id))
        
        # Step 3: Delete chat message history records.
        # We delete messages linked to sessions belonging to agents of the project.
        await run_in_threadpool(
            cursor.execute,
            """
            DELETE FROM chat_messages 
            WHERE session_id IN (
                SELECT id FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)
            )
            """, 
            (project_id,)
        )
        
        # Step 4: Delete the chat sessions themselves.
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)", (project_id,))
        # Step 5: Delete all agent configurations belonging to the project.
        await run_in_threadpool(cursor.execute, "DELETE FROM agents WHERE project_id = %s", (project_id,))
        # Step 6: Delete the core project record.
        await run_in_threadpool(cursor.execute, "DELETE FROM agent_projects WHERE id = %s", (project_id,))
        
        # return the rowcount indicating how many projects were deleted (should be 1).
        return cursor.rowcount


async def get_project_tools(project_id: str):
    """
    Retrieves all custom tools defined for a specific project.

    Purpose:
        Fetches configurations of custom tools (such as APIs, database querying engines, etc.)
        used by agents in the project.

    Parameters:
        project_id (str): The project identifier.

    Returns:
        list of tuples: A list of tool records, ordered chronologically (oldest first).

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id, name, config, blueprint_tool_id FROM agent_tools WHERE project_id = %s ORDER BY created_at ASC",
            (project_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def update_project_tool(tool_id: str, name: str, config: dict):
    """
    Updates the configuration parameters or name of a project tool.

    Purpose:
        Allows modifying a tool's user-facing name and schema configurations (e.g. endpoint parameters).

    Parameters:
        tool_id (str): The unique ID of the tool to update.
        name (str): The updated name for the tool.
        config (dict): The updated tool configuration parameters (JSON structure).

    Returns:
        int: The number of rows affected by the update statement (typically 1).

    Side Effects / State Changes:
        - Modifies a row in `agent_tools`.
        - Serializes config to a JSON string.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE agent_tools SET name = %s, config = %s WHERE id = %s RETURNING id;",
            (name, json.dumps(config), tool_id)
        )
        return cursor.rowcount


async def create_project_tool(project_id: str, name: str, config: dict):
    """
    Creates a new custom tool for a project network.

    Purpose:
        Saves a new tool configuration linked to a project and its workspace.
        Automatically generates a standard namespace blueprint identifier from the tool name.

    Parameters:
        project_id (str): The project identifier.
        name (str): User-defined name of the tool (e.g., "Google Search").
        config (dict): Configuration dictionary containing schema and connection definitions.

    Returns:
        str | None: The database identifier of the new tool, or None if the project does not exist.

    Side Effects / State Changes:
        - Inserts a new row into the `agent_tools` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database constraint violations if the project_id is invalid.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Resolve the workspace_id associated with this project.
        # This ensures the tool is correctly scoped to the parent workspace.
        await run_in_threadpool(cursor.execute, "SELECT workspace_id FROM agent_projects WHERE id = %s", (project_id,))
        project_row = await run_in_threadpool(cursor.fetchone)
        if not project_row:
            return None
            
        workspace_id = project_row[0]

        # Generate a structured blueprint tool ID.
        # E.g. name "Google Search" becomes "custom_tool_google_search".
        blueprint_tool_id = "custom_tool_" + name.lower().replace(" ", "_")

        # Insert the custom tool configuration.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (project_id, workspace_id, blueprint_tool_id, name, json.dumps(config))
        )
        # Return the new tool's unique primary key ID.
        return (await run_in_threadpool(cursor.fetchone))[0]

