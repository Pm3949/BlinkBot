import json
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from core.security import encrypt_key
from prompts.system_agent_prompts import GENERAL_ASSISTANT_SYSTEM_PROMPT

async def get_agents(workspace_id: str, include_gateways: bool = False):
    async with get_db_cursor_async(commit=False) as cursor:
        if include_gateways:
            condition = "WHERE workspace_id = %s AND (project_id IS NULL OR parent_agent_id IS NULL)"
        else:
            condition = "WHERE workspace_id = %s AND project_id IS NULL"
            
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
        return await run_in_threadpool(cursor.fetchall)

async def create_agent(payload_data: dict):
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
                encrypt_key(payload_data.get("api_key", "")), 
                payload_data.get("language", "en"), 
                payload_data.get("user_id"), 
                payload_data.get("workspace_id"), 
                payload_data.get("web_search_enabled", False), 
                payload_data.get("project_id"), 
                payload_data.get("parent_agent_id"), 
                json.dumps(payload_data.get("endpoints", [])),
                payload_data.get("code_interpreter_enabled", False),
                encrypt_key(json.dumps(payload_data.get("databases", []))),
                encrypt_key(json.dumps(payload_data.get("native_integrations", [])))
            )
        )
        return await run_in_threadpool(cursor.fetchone)

async def update_agent(agent_id: str, payload: dict):
    async with get_db_cursor_async(commit=True) as cursor:
        set_clauses = []
        values = []
        for key, value in payload.items():
            if key in ["name", "description", "llm_provider", "llm_model", "embedding_model", "chunk_strategy", "system_prompt", "output_format", "api_key", "language", "web_search_enabled", "is_active", "endpoints", "code_interpreter_enabled", "databases", "native_integrations", "parent_agent_id"]:
                set_clauses.append(f"{key} = %s")
                if key == "api_key":
                    values.append(encrypt_key(value))
                elif key == "endpoints":
                    values.append(json.dumps(value))
                elif key == "databases" or key == "native_integrations":
                    values.append(encrypt_key(json.dumps(value)))
                else:
                    values.append(value)
                
        if not set_clauses:
            return None
            
        values.append(agent_id)
        
        query = f"UPDATE agents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, name, description, llm_provider, llm_model, embedding_model, chunk_strategy, system_prompt, output_format, api_key, language, user_id, workspace_id, created_at, web_search_enabled, is_active, endpoints, code_interpreter_enabled, databases, native_integrations, parent_agent_id;"
        
        await run_in_threadpool(cursor.execute, query, tuple(values))
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

async def create_agent_project(name: str, description: str, workspace_id: str, user_id: str):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_projects (name, description, status, workspace_id, blueprint_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (name, description, "active", workspace_id, json.dumps({}))
        )
        project_id = (await run_in_threadpool(cursor.fetchone))[0]
        
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
                None, 
                json.dumps([]),
                False,
                encrypt_key(json.dumps([])),
                encrypt_key(json.dumps([]))
            )
        )
        manager_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Create General Assistant
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
                GENERAL_ASSISTANT_SYSTEM_PROMPT, 
                "",
                encrypt_key(""), 
                "en", 
                user_id, 
                workspace_id, 
                False, # Web search disabled by default
                project_id, 
                manager_id, 
                json.dumps([]),
                False,
                encrypt_key(json.dumps([])),
                encrypt_key(json.dumps([]))
            )
        )

        return project_id

async def get_agent_projects(workspace_id: str):
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
    async with get_db_cursor_async(commit=True) as cursor:
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
        
        await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s) OR project_id = %s", (project_id, project_id))
        
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
        
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id IN (SELECT id FROM agents WHERE project_id = %s)", (project_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM agents WHERE project_id = %s", (project_id,))
        await run_in_threadpool(cursor.execute, "DELETE FROM agent_projects WHERE id = %s", (project_id,))
        
        return cursor.rowcount

async def get_project_tools(project_id: str):
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id, name, config, blueprint_tool_id FROM agent_tools WHERE project_id = %s ORDER BY created_at ASC",
            (project_id,)
        )
        return await run_in_threadpool(cursor.fetchall)

async def update_project_tool(tool_id: str, name: str, config: dict):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE agent_tools SET name = %s, config = %s WHERE id = %s RETURNING id;",
            (name, json.dumps(config), tool_id)
        )
        return cursor.rowcount

async def create_project_tool(project_id: str, name: str, config: dict):
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT workspace_id FROM agent_projects WHERE id = %s", (project_id,))
        project_row = await run_in_threadpool(cursor.fetchone)
        if not project_row:
            return None
            
        workspace_id = project_row[0]

        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (project_id, workspace_id, "custom_tool_" + name.lower().replace(" ", "_"), name, json.dumps(config))
        )
        return (await run_in_threadpool(cursor.fetchone))[0]
