import json
from meta_agent_schemas import AgentBlueprint
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def deploy_agent_blueprint_to_db(workspace_id: str, user_id: str, blueprint: AgentBlueprint, config_data: dict):
    """
    Deploys a generated agent blueprint to the database.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_projects (workspace_id, name, description, status, blueprint_json)
            VALUES (%s, %s, %s, 'deployed', %s)
            RETURNING id;
            """,
            (workspace_id, blueprint.project_name, blueprint.description, blueprint.model_dump_json())
        )
        project_id = (await run_in_threadpool(cursor.fetchone))[0]

        enabled_kb = config_data.get("enabled_knowledge", {})
        for kb in blueprint.required_knowledge:
            if enabled_kb.get(kb.id):
                await run_in_threadpool(
                    cursor.execute,
                    """
                    INSERT INTO documents (project_id, blueprint_knowledge_id, filename, type, source_uri, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """,
                    (project_id, kb.id, kb.name, kb.type, "")
                )

        enabled_tools = config_data.get("enabled_tools", {})
        tools_config = config_data.get("tools", {})
        for tool in blueprint.required_tools:
            tool_config_data = tools_config.get(tool.id, {})
            tool_config_data["is_enabled"] = bool(enabled_tools.get(tool.id))
            
            if "query_format" not in tool_config_data:
                tool_config_data["query_format"] = "{}"
            if "headers" not in tool_config_data:
                tool_config_data["headers"] = "{}"
                
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (project_id, workspace_id, tool.id, tool.name, json.dumps(tool_config_data))
            )

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
            real_uuid = (await run_in_threadpool(cursor.fetchone))[0]
            agent_id_map[sub_agent.id] = real_uuid

        for sub_agent in blueprint.sub_agents:
            if getattr(sub_agent, 'parent_agent_id', None) and sub_agent.parent_agent_id in agent_id_map:
                real_uuid = agent_id_map[sub_agent.id]
                parent_real_uuid = agent_id_map[sub_agent.parent_agent_id]
                await run_in_threadpool(
                    cursor.execute,
                    """
                    UPDATE agents SET parent_agent_id = %s WHERE id = %s
                    """,
                    (parent_real_uuid, real_uuid)
                )

        await run_in_threadpool(cursor.execute, "SELECT blueprint_tool_id, id FROM agent_tools WHERE project_id = %s", (project_id,))
        tool_id_map = {row[0]: row[1] for row in (await run_in_threadpool(cursor.fetchall))}

        return {
            "status": "success", 
            "project_id": project_id, 
            "agent_id_map": agent_id_map,
            "tool_id_map": tool_id_map
        }
