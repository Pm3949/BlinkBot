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
from typing import Optional
from pydantic import BaseModel
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
    handle_create_project_tool
)

# Set standard module logger.
logger = logging.getLogger(__name__)

# Initialize router with tag categories for automatic Swagger docs.
router = APIRouter(tags=["agents"])

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class AgentCreate(BaseModel):
    """
    Validation schema for creating a new AI Agent.
    """
    name: str # Display name of the agent
    description: Optional[str] = "" # Optional explanation of what the agent does
    llm_provider: str # LLM provider service (e.g. 'openai', 'groq', 'gemini')
    llm_model: str # The specific LLM model ID
    embedding_model: Optional[str] = "text-embedding-3-small" # RAG embedding model ID
    chunk_strategy: Optional[str] = "semantic" # Strategy used to partition files (e.g., 'sentence', 'semantic')
    system_prompt: Optional[str] = "" # Core system instruction guidelines
    output_format: Optional[str] = "" # Output constraint rules
    api_key: Optional[str] = "" # Option to pass a custom provider API key
    language: Optional[str] = "en" # Language locale parameter
    workspace_id: str # Target workspace UUID
    web_search_enabled: bool = False # Toggles live web search integration
    project_id: Optional[str] = None # Optional parent project UUID
    parent_agent_id: Optional[str] = None # Optional parent agent UUID for hierarchical routing
    endpoints: Optional[list] = [] # Optional list of custom REST API endpoints
    databases: Optional[list] = [] # Optional list of connected database objects
    code_interpreter_enabled: bool = False # Toggles local sandboxed python code execution capabilities
    native_integrations: Optional[list] = [] # List of native integrations (e.g., Google Drive)


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
    name: str # Project title
    description: Optional[str] = "" # Project details summary
    workspace_id: str # Parent workspace identifier


class ToolCreate(BaseModel):
    """
    Validation schema for creating custom API tools linked to project networks.
    """
    name: str # Custom tool display name
    config: dict # Integration configurations (headers, URL endpoints, formats)


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
async def get_agents(workspace_id: str, include_gateways: bool = False, current_user: dict = Depends(get_current_user)):
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
async def create_agent(agent: AgentCreate, current_user: dict = Depends(get_current_user)):
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
async def update_agent(agent_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
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
async def create_agent_project(project: AgentProjectCreate, current_user: dict = Depends(get_current_user)):
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
async def get_agent_projects(workspace_id: str, current_user: dict = Depends(get_current_user)):
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
async def get_project_sub_agents(project_id: str, current_user: dict = Depends(get_current_user)):
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
async def delete_agent_project(project_id: str, current_user: dict = Depends(get_current_user)):
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
async def get_project_tools(project_id: str, current_user: dict = Depends(get_current_user)):
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
async def update_project_tool(tool_id: str, payload: ToolUpdate, current_user: dict = Depends(get_current_user)):
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
async def create_project_tool(project_id: str, payload: ToolCreate, current_user: dict = Depends(get_current_user)):
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


class PromptOptimizeRequest(BaseModel):
    draft_prompt: str
    llm_provider: Optional[str] = "groq"
    llm_model: Optional[str] = "llama-3.3-70b-versatile"
    custom_api_key: Optional[str] = ""


@router.post("/api/agents/optimize-prompt")
async def optimize_agent_prompt(payload: PromptOptimizeRequest, current_user: dict = Depends(get_current_user)):
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
            user_id=current_user["sub"]
        )

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=f"Draft Prompt: {payload.draft_prompt}")
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

        optimized_text = content.strip()

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


