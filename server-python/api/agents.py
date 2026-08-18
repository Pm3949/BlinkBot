"""
================================================================================
AGENT MANAGEMENT CONTROLLER LAYER (agents.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module defines the HTTP endpoint routing structure for creating, updating,
deleting, and listing AI agents and Multi-Agent projects. It acts as the gateway
for configuring RAG settings, LLM providers (e.g. Groq, OpenAI), embedding models,
and parent-child agent topologies.

HOW SINGLE vs MULTI-AGENT ARCHITECTURES WORK:
1. Single Agents: Independent assistants designed with isolated system prompts,
   embedding contexts, and RAG chunk configurations.
2. Multi-Agent Projects (`agent-projects`): Hierarchical workspaces consisting of:
   - A central "Network Manager" (router agent).
   - A "General Assistant" (greeting agent).
   - Custom sub-agents with specific tasks and system prompts.
   - Project-level shared tools and integrations (REST APIs, databases).

DATA FLOW PATTERNS:
- User actions map to endpoint routers. Pydantic models validate input formats.
- The router extracts the owner's `user_id` from JWT session payloads and delegates
  processing to `handlers/agent_handler.py` modules.
"""

import logging
from utils.logger import get_department_logger
from typing import Optional
from pydantic import BaseModel
from core.config import DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL
from fastapi import APIRouter, Depends
from core.auth import get_current_user

# Import agent and project business logic handler functions.
from handlers.agent_handler import (
    handle_get_agents,
    handle_create_agent,
    handle_update_agent,
    handle_create_agent_project,
    handle_get_agent_projects,
    handle_get_project_sub_agents,
    handle_delete_agent_project,
    handle_get_project_tools,
    handle_update_project_tool,
    handle_create_project_tool,
)

# Set standard module logger.
logger = get_department_logger("agent")

# Initialize router with tag categories for automatic Swagger docs.
router = APIRouter(tags=["agents"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================


class AgentCreate(BaseModel):
    """
    Validation schema for creating a new AI Agent.
    """

    name: str  # Display name of the agent
    description: Optional[str] = ""  # Optional explanation of what the agent does
    llm_provider: str  # LLM provider service (e.g. 'openai', 'groq', 'gemini')
    llm_model: str  # The specific LLM model ID
    embedding_model: Optional[str] = "text-embedding-3-small"  # RAG embedding model ID
    chunk_strategy: Optional[str] = (
        "semantic"  # Strategy used to partition files (e.g., 'sentence', 'semantic')
    )
    system_prompt: Optional[str] = ""  # Core system instruction guidelines
    output_format: Optional[str] = ""  # Output constraint rules
    api_key: Optional[str] = ""  # Option to pass a custom provider API key
    language: Optional[str] = "en"  # Language locale parameter
    workspace_id: str  # Target workspace UUID
    web_search_enabled: bool = False  # Toggles live web search integration
    project_id: Optional[str] = None  # Optional parent project UUID
    parent_agent_id: Optional[str] = (
        None  # Optional parent agent UUID for hierarchical routing
    )
    endpoints: Optional[list] = []  # Optional list of custom REST API endpoints
    databases: Optional[list] = []  # Optional list of connected database objects
    code_interpreter_enabled: bool = (
        False  # Toggles local sandboxed python code execution capabilities
    )
    native_integrations: Optional[list] = (
        []
    )  # List of native integrations (e.g., Google Drive)


class AgentUpdate(BaseModel):
    """
    Validation schema for updating properties of an existing AI Agent.
    """

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
    databases: Optional[list] = None
    code_interpreter_enabled: Optional[bool] = None
    native_integrations: Optional[list] = None


class AgentProjectCreate(BaseModel):
    """
    Validation schema for establishing a multi-agent project group.
    """

    name: str  # Project title
    description: Optional[str] = ""  # Project details summary
    workspace_id: str  # Parent workspace identifier


class ToolCreate(BaseModel):
    """
    Validation schema for creating custom API tools linked to project networks.
    """

    name: str  # Custom tool display name
    config: dict  # Integration configurations (headers, URL endpoints, formats)


class ToolUpdate(BaseModel):
    """
    Validation schema for editing custom tool configurations.
    """

    name: str
    config: dict


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================


@router.get("/api/agents")
async def get_agents(
    workspace_id: str,
    include_gateways: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves all active agents configured under a target workspace.

    Purpose:
        Fetches the agents catalog, allowing users to list or select assistants for chat flows.

    Parameters:
        workspace_id (str): UUID of the parent workspace.
        include_gateways (bool): If True, returns system gateway routers (e.g., Network Managers) in the results.
        current_user (dict): JWT details.

    Returns:
        list of dict: Registered agent profiles in the workspace.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification checks fail.
    """
    # Delegate query tasks to the agent handler.
    return await handle_get_agents(workspace_id, include_gateways)


@router.post("/api/agents")
async def create_agent(
    agent: AgentCreate, current_user: dict = Depends(get_current_user)
):
    """
    Creates a new AI agent profile.

    Purpose:
        Registers a single custom assistant or hooks a new sub-agent to a parent project hierarchy.

    Parameters:
        agent (AgentCreate): Pydantic validated body containing agent configs.
        current_user (dict): JWT details.

    Returns:
        dict: The newly created agent database record attributes.

    Side Effects / State Changes:
        - Writes a new record to the `agents` table.

    Errors / Exceptions:
        - Raises 401 on authentication failures.
        - Raises 400 Bad Request if configurations (models, provider IDs) are invalid.
    """
    # Parse the Pydantic validator data to a standard Python dictionary.
    data = agent.dict()
    # Inject the creator's user UUID retrieved from the JWT subject ("sub") claim.
    data["user_id"] = current_user["sub"]
    # Execute database insertion and initialization through the handler.
    return await handle_create_agent(data)


@router.put("/api/agents/{agent_id}")
async def update_agent(
    agent_id: str, payload: dict, current_user: dict = Depends(get_current_user)
):
    """
    Updates the configuration settings of an existing agent.

    Purpose:
        Modifies agent parameters (such as switching LLM models, updating prompts, or adding APIs).

    Parameters:
        agent_id (str): The unique UUID of the target agent to update.
        payload (dict): A dictionary of the updated fields.

    Returns:
        dict: The updated agent database record attributes.

    Side Effects / State Changes:
        - Modifies columns on matching rows in the `agents` table.

    Errors / Exceptions:
        - Raises 401/403 for unauthorized requests.
        - Raises 404 Not Found if the agent does not exist.
    """
    # Execute updates through the handler.
    return await handle_update_agent(agent_id, payload)


@router.post("/api/agent-projects")
async def create_agent_project(
    project: AgentProjectCreate, current_user: dict = Depends(get_current_user)
):
    """
    Creates a new multi-agent project network.

    Purpose:
        Registers the project workspace and automatically spawns the default system
        coordinators (the Network Manager router and General Assistant).

    Parameters:
        project (AgentProjectCreate): Pydantic body containing the project name and workspace ID.
        current_user (dict): JWT details.

    Returns:
        dict: Success status and the newly created project ID.

    Side Effects / State Changes:
        - Writes records to the `agent_projects` and `agents` database tables.

    Errors / Exceptions:
        - Raises 401/403 on authorization issues.
    """
    # Delegate multi-stage initialization tasks to the handler.
    return await handle_create_agent_project(
        project.name, project.description, project.workspace_id, current_user["sub"]
    )


@router.get("/api/agent-projects")
async def get_agent_projects(
    workspace_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all multi-agent projects configured in a workspace.

    Purpose:
        Lists multi-agent projects on the workspace dashboards.

    Parameters:
        workspace_id (str): Target workspace UUID.
        current_user (dict): JWT details.

    Returns:
        list of dict: Registered projects catalog listings.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 Unauthorized if headers are invalid.
    """
    # Delegate query execution to handlers.
    return await handle_get_agent_projects(workspace_id)


@router.get("/api/agent-projects/{project_id}/sub-agents")
async def get_project_sub_agents(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all sub-agents linked to a specific multi-agent project.

    Purpose:
        Fetches sub-agents belonging to a project hierarchy.

    Parameters:
        project_id (str): The unique parent project UUID.
        current_user (dict): JWT details.

    Returns:
        list of dict: Sub-agent profile metadata records.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 on verification errors.
    """
    # Query sub-agents using the handler.
    return await handle_get_project_sub_agents(project_id)


@router.delete("/api/agent-projects/{project_id}")
async def delete_agent_project(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Deletes a multi-agent project and all associated sub-agents.

    Purpose:
        Wipes a project configuration and deletes associated sub-agents, tools, and configurations.

    Parameters:
        project_id (str): UUID of the project to delete.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation message.

    Side Effects / State Changes:
        - Deletes rows in `agent_projects`, `agents`, and `agent_tools` tables.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 Not Found if the project does not exist.
    """
    # Execute deletion process through the handler.
    return await handle_delete_agent_project(project_id)


@router.get("/api/agent-projects/{project_id}/tools")
async def get_project_tools(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieves all tools configured for a multi-agent project.

    Purpose:
        Lists custom tools available to the project's sub-agents.

    Parameters:
        project_id (str): The parent project UUID.
        current_user (dict): JWT details.

    Returns:
        list of dict: Tools database records containing configs, names, and IDs.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - Raises 401 on auth errors.
    """
    # Fetch tools via the handler.
    return await handle_get_project_tools(project_id)


@router.put("/api/tools/{tool_id}")
async def update_project_tool(
    tool_id: str, payload: ToolUpdate, current_user: dict = Depends(get_current_user)
):
    """
    Updates the configuration of an existing custom project tool.

    Purpose:
        Modifies integration details (e.g. updating target URLs or headers for custom APIs).

    Parameters:
        tool_id (str): The unique database UUID of the target tool.
        payload (ToolUpdate): Pydantic body containing the tool's name and configuration dictionary.
        current_user (dict): JWT details.

    Returns:
        dict: Success status confirmation.

    Side Effects / State Changes:
        - Updates the config and name columns in `agent_tools` table.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 404 if the tool is not found.
    """
    # Execute updates through the handler.
    return await handle_update_project_tool(tool_id, payload.name, payload.config)


@router.post("/api/agent-projects/{project_id}/tools")
async def create_project_tool(
    project_id: str, payload: ToolCreate, current_user: dict = Depends(get_current_user)
):
    """
    Creates a new custom tool and links it to a project.

    Purpose:
        Registers a new custom API tool, enabling sub-agents to access external services.

    Parameters:
        project_id (str): UUID of the project to link the tool to.
        payload (ToolCreate): Pydantic body containing the tool's name and config schema.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation containing the new tool ID.

    Side Effects / State Changes:
        - Writes a new row to the `agent_tools` table.

    Errors / Exceptions:
        - Raises 401/403 on authorization issues.
    """
    # Create the tool using the handler.
    return await handle_create_project_tool(project_id, payload.name, payload.config)


import re

def clean_reasoning_thoughts(text: str) -> str:
    if not isinstance(text, str):
        return text
    
    # 1. Normalize HTML entities (APIs often escape brackets)
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    
    # 2. Remove fully enclosed blocks (consolidated regex)
    text = re.sub(r"<(think|thought)>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\[(think|thought)\].*?\[/\1\]", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. Remove standalone text headers
    text = re.sub(r"(?i)^\s*(thinking process|thought|thinking):\s*", "", text)
    
    # 4. Remove leftover/unclosed tags WITHOUT deleting the rest of the text
    # (Your previous `r"<think>.*"` would delete the final answer if the tag was unclosed)
    text = re.sub(r"(?i)</?(think|thought)>", "", text)
    text = re.sub(r"(?i)\[/?(think|thought)\]", "", text)
    
    # 5. Clean up any leftover whitespace or newlines
    return text.strip()

class PromptOptimizeRequest(BaseModel):
    draft_prompt: str
    llm_provider: Optional[str] = DEFAULT_LLM_PROVIDER
    llm_model: Optional[str] = DEFAULT_LLM_MODEL
    custom_api_key: Optional[str] = ""


@router.post("/api/agents/optimize-prompt")
async def optimize_agent_prompt(
    payload: PromptOptimizeRequest, current_user: dict = Depends(get_current_user)
):
    """
    Optimizes a draft system prompt using an LLM.
    """
    logger.info("Starting system prompt optimization...")
    from handlers.chat_handler import create_resilient_llm_instance
    from langchain_core.messages import SystemMessage, HumanMessage

    from prompts.optimizer_prompts import PROMPT_OPTIMIZER_SYSTEM_INSTRUCTION

    system_instruction = PROMPT_OPTIMIZER_SYSTEM_INSTRUCTION

    try:
        # Create LLM instance
        llm = await create_resilient_llm_instance(
            provider=payload.llm_provider,
            model_name=payload.llm_model,
            api_key=payload.custom_api_key or None,
            user_id=current_user["sub"],
        )

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=f"Draft Prompt: {payload.draft_prompt}"),
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            content = "".join(parts)
        elif isinstance(content, dict):
            content = content.get("text", str(content))

        optimized_text = clean_reasoning_thoughts(content)

        # Clean code block indicators if model generated them
        if optimized_text.startswith("```"):
            lines = optimized_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            optimized_text = "\n".join(lines).strip()

        return {"optimized_prompt": optimized_text}
    except Exception as e:
        logger.error(f"Error optimizing prompt: {e}", exc_info=True)
        return {"optimized_prompt": payload.draft_prompt}


class ToolDescriptionRequest(BaseModel):
    tool_name: str
    path: str
    method: str
    payload_format: Optional[str] = ""
    expected_output: Optional[str] = ""
    llm_provider: Optional[str] = DEFAULT_LLM_PROVIDER
    llm_model: Optional[str] = DEFAULT_LLM_MODEL
    custom_api_key: Optional[str] = ""
    path_variables: Optional[list] = []
    query_parameters: Optional[list] = []


@router.post("/api/agents/generate-tool-description")
async def generate_tool_description(
    payload: ToolDescriptionRequest, current_user: dict = Depends(get_current_user)
):
    """
    Generates a concise tool instruction description and parameter-level descriptions using LLM.
    """
    logger.info("Generating dynamic tool and parameter descriptions...")
    from handlers.chat_handler import create_resilient_llm_instance
    from langchain_core.messages import SystemMessage, HumanMessage
    import json

    from prompts.optimizer_prompts import TOOL_DESCRIPTION_OPTIMIZER_INSTRUCTION
    system_instruction = TOOL_DESCRIPTION_OPTIMIZER_INSTRUCTION

    try:
        llm = await create_resilient_llm_instance(
            provider=payload.llm_provider,
            model_name=payload.llm_model,
            api_key=payload.custom_api_key or None,
            user_id=current_user["sub"],
        )

        user_content = (
            f"Tool Name: {payload.tool_name}\n"
            f"Path: {payload.path}\n"
            f"Method: {payload.method}\n"
            f"Payload Format: {payload.payload_format}\n"
            f"Expected Output: {payload.expected_output}\n"
            f"Path Variables: {payload.path_variables}\n"
            f"Query/Body Parameters: {payload.query_parameters}"
        )

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=user_content),
        ]

        response = await llm.ainvoke(messages)
        description_content = response.content

        if isinstance(description_content, list):
            parts = []
            for part in description_content:
                if isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            description_content = "".join(parts)
        elif isinstance(description_content, dict):
            description_content = description_content.get(
                "text", str(description_content)
            )

        description_content = clean_reasoning_thoughts(description_content)

        # Strip markdown codeblock if present
        if description_content.startswith("```"):
            lines = description_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            description_content = "\n".join(lines).strip()

        try:
            parsed_res = json.loads(description_content)
        except json.JSONDecodeError:
            # Try to extract JSON from the string if model wrapped it in text
            json_match = re.search(r"\{.*\}", description_content, re.DOTALL)
            if json_match:
                try:
                    parsed_res = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    parsed_res = None
            else:
                parsed_res = None

            if not parsed_res:
                # If model returned pure plain text description, map it to the expected schema format
                fallback_path_vars = {
                    v: f"Path parameter {v}" for v in (payload.path_variables or [])
                }
                fallback_query_params = {
                    q: f"Query parameter {q}" for q in (payload.query_parameters or [])
                }
                parsed_res = {
                    "description": description_content.strip() or f"Use this tool to interact with {payload.tool_name} at {payload.path}.",
                    "path_variables": fallback_path_vars,
                    "query_parameters": fallback_query_params,
                }

        # Recursively clean any leftover <think> blocks inside the parsed JSON values
        def clean_think_tags(val):
            if isinstance(val, str):
                return clean_reasoning_thoughts(val)
            elif isinstance(val, dict):
                return {k: clean_think_tags(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [clean_think_tags(x) for x in val]
            return val

        parsed_res = clean_think_tags(parsed_res)
        return parsed_res
    except Exception as e:
        logger.error(f"Error generating tool description: {e}", exc_info=True)
        # Return fallback structures matching the JSON schema
        fallback_path_vars = {
            v: f"Path parameter {v}" for v in (payload.path_variables or [])
        }
        fallback_query_params = {
            q: f"Query parameter {q}" for q in (payload.query_parameters or [])
        }
        return {
            "description": f"Use this tool to interact with {payload.tool_name} at {payload.path}.",
            "path_variables": fallback_path_vars,
            "query_parameters": fallback_query_params,
        }


@router.get("/api/agents/{agent_id}/analytics")
async def get_agent_token_analytics(
    agent_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get token usage and cost metrics for a specific agent.
    """
    from core.database import get_db_cursor_async
    from fastapi.concurrency import run_in_threadpool

    try:
        user_id = current_user["sub"]
        async with get_db_cursor_async(commit=False) as cursor:
            # Query cumulative metrics
            await run_in_threadpool(
                cursor.execute,
                """
                SELECT 
                    COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost), 0.000000) as total_cost
                FROM token_usages
                WHERE user_id = %s AND agent_id = %s
                """,
                (user_id, agent_id),
            )
            totals = await run_in_threadpool(cursor.fetchone)

            # Query daily metrics for charts (last 30 days)
            await run_in_threadpool(
                cursor.execute,
                """
                SELECT 
                    DATE(created_at) as date,
                    SUM(prompt_tokens) as daily_prompt,
                    SUM(completion_tokens) as daily_completion,
                    SUM(total_tokens) as daily_tokens,
                    SUM(estimated_cost) as daily_cost,
                    COUNT(*) as daily_calls
                FROM token_usages
                WHERE user_id = %s AND agent_id = %s AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at) ASC
                """,
                (user_id, agent_id),
            )
            daily_rows = await run_in_threadpool(cursor.fetchall)

            return {
                "totals": {
                    "prompt_tokens": totals[0],
                    "completion_tokens": totals[1],
                    "total_tokens": totals[2],
                    "estimated_cost": float(totals[3]),
                },
                "daily": [
                    {
                        "date": str(r[0]),
                        "prompt_tokens": r[1],
                        "completion_tokens": r[2],
                        "tokens": r[3],
                        "cost": float(r[4]),
                        "calls": r[5],
                    }
                    for r in daily_rows
                ],
            }
    except Exception as e:
        logger.error(f"Error fetching token analytics: {e}", exc_info=True)
        return {
            "totals": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
            },
            "daily": [],
        }
