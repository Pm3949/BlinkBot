import json
from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

SYSTEM_TOOLS = [
    {
        "name": "Web Search Fallback",
        "tool_type": "api_webhook",
        "configuration": {
            "system_identifier": "web_search",
            "description": "Allow the agent to search the internet if the answer isn't in documents."
        }
    },
    {
        "name": "Python Code Sandbox (CSV Analyzer)",
        "tool_type": "database",
        "configuration": {
            "system_identifier": "code_interpreter",
            "description": "Allow the agent to natively parse, query, and perform statistical analysis on uploaded CSV and Excel spreadsheet files."
        }
    },
    {
        "name": "Image Reader (OCR)",
        "tool_type": "api_webhook",
        "configuration": {
            "system_identifier": "ocr_reader",
            "description": "Perform optical character recognition (OCR) fallback routines for scanned PDFs or images."
        }
    }
]

async def seed_system_tools_if_missing(workspace_id: str):
    """
    Ensures that the 3 system tools are seeded for the given workspace.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Check which system identifiers already exist
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT configuration->>'system_identifier' 
            FROM workspace_tools 
            WHERE workspace_id = %s AND is_system = true
            """,
            (workspace_id,)
        )
        existing_identifiers = {row[0] for row in await run_in_threadpool(cursor.fetchall) if row[0]}
        
        for sys_tool in SYSTEM_TOOLS:
            ident = sys_tool["configuration"]["system_identifier"]
            if ident not in existing_identifiers:
                await run_in_threadpool(
                    cursor.execute,
                    """
                    INSERT INTO workspace_tools (workspace_id, name, tool_type, configuration, is_system)
                    VALUES (%s, %s, %s, %s, true)
                    """,
                    (workspace_id, sys_tool["name"], sys_tool["tool_type"], json.dumps(sys_tool["configuration"]))
                )

async def get_workspace_tools(workspace_id: str):
    """
    Retrieves all custom and system tools configured for a workspace.
    Auto-seeds system tools if they are missing.
    """
    await seed_system_tools_if_missing(workspace_id)
    
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, workspace_id, name, tool_type, configuration, created_at, is_system, code_content
            FROM workspace_tools
            WHERE workspace_id = %s
            ORDER BY is_system DESC, created_at DESC
            """,
            (workspace_id,)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": str(r[0]),
                "workspace_id": str(r[1]),
                "name": r[2],
                "tool_type": r[3],
                "configuration": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                "created_at": r[5].isoformat() if r[5] else None,
                "is_system": bool(r[6]),
                "code_content": r[7]
            }
            for r in rows
        ]

async def create_workspace_tool(workspace_id: str, name: str, tool_type: str, configuration: dict, code_content: str = None):
    """
    Creates a new custom workspace tool (always is_system = false).
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_tools (workspace_id, name, tool_type, configuration, is_system, code_content)
            VALUES (%s, %s, %s, %s, false, %s)
            RETURNING id, workspace_id, name, tool_type, configuration, created_at, is_system, code_content;
            """,
            (workspace_id, name, tool_type, json.dumps(configuration), code_content)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return {
                "id": str(row[0]),
                "workspace_id": str(row[1]),
                "name": row[2],
                "tool_type": row[3],
                "configuration": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                "created_at": row[5].isoformat() if row[5] else None,
                "is_system": bool(row[6]),
                "code_content": row[7]
            }
        return None

async def update_workspace_tool(tool_id: str, name: str, configuration: dict, code_content: str = None):
    """
    Updates the configuration, name, or code of an existing workspace tool.
    Blocks update if the tool is a system tool.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Check if is_system
        await run_in_threadpool(
            cursor.execute,
            "SELECT is_system FROM workspace_tools WHERE id = %s",
            (tool_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if not row:
            return None
        if row[0]:
            raise PermissionError("Cannot update system tools.")
            
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE workspace_tools
            SET name = %s, configuration = %s, code_content = %s
            WHERE id = %s AND is_system = false
            RETURNING id, workspace_id, name, tool_type, configuration, created_at, is_system, code_content;
            """,
            (name, json.dumps(configuration), code_content, tool_id)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return {
                "id": str(row[0]),
                "workspace_id": str(row[1]),
                "name": row[2],
                "tool_type": row[3],
                "configuration": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                "created_at": row[5].isoformat() if row[5] else None,
                "is_system": bool(row[6]),
                "code_content": row[7]
            }
        return None

async def delete_workspace_tool(tool_id: str):
    """
    Deletes a workspace tool.
    Blocks deletion if the tool is a system tool.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT is_system FROM workspace_tools WHERE id = %s",
            (tool_id,)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if not row:
            return False
        if row[0]:
            raise PermissionError("Cannot delete system tools.")
            
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM workspace_tools WHERE id = %s AND is_system = false;",
            (tool_id,)
        )
        return cursor.rowcount > 0

async def attach_tool_to_agent(agent_id: str, tool_id: str):
    """
    Links a tool to an agent.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO agent_tools_junction (agent_id, tool_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (agent_id, tool_id)
        )
        return True

async def detach_tool_from_agent(agent_id: str, tool_id: str):
    """
    Unlinks a tool from an agent.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM agent_tools_junction WHERE agent_id = %s AND tool_id = %s;",
            (agent_id, tool_id)
        )
        return cursor.rowcount > 0

async def get_agent_attached_tools(agent_id: str):
    """
    Retrieves all workspace tools linked to a given agent.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT t.id, t.workspace_id, t.name, t.tool_type, t.configuration, t.created_at, t.is_system, t.code_content
            FROM workspace_tools t
            JOIN agent_tools_junction j ON t.id = j.tool_id
            WHERE j.agent_id = %s
            ORDER BY t.is_system DESC, t.created_at DESC;
            """,
            (agent_id,)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        return [
            {
                "id": str(r[0]),
                "workspace_id": str(r[1]),
                "name": r[2],
                "tool_type": r[3],
                "configuration": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                "created_at": r[5].isoformat() if r[5] else None,
                "is_system": bool(r[6]),
                "code_content": r[7]
            }
            for r in rows
        ]
