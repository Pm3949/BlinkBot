import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user

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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    llm_provider: str
    llm_model: str
    embedding_model: Optional[str] = "text-embedding-3-small"
    chunk_strategy: Optional[str] = "semantic"
    system_prompt: Optional[str] = ""
    output_format: Optional[str] = ""
    api_key: Optional[str] = ""
    language: Optional[str] = "en"
    workspace_id: str
    web_search_enabled: bool = False
    project_id: Optional[str] = None
    parent_agent_id: Optional[str] = None
    endpoints: Optional[list] = []
    databases: Optional[list] = []
    code_interpreter_enabled: bool = False
    native_integrations: Optional[list] = []

class AgentUpdate(BaseModel):
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
    name: str
    description: Optional[str] = ""
    workspace_id: str

class ToolCreate(BaseModel):
    name: str
    config: dict

class ToolUpdate(BaseModel):
    name: str
    config: dict

@router.get("/api/agents")
async def get_agents(workspace_id: str, include_gateways: bool = False, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to retrieve a list of AI agents for a workspace.
    Args:
        workspace_id (str): The workspace to query.
        include_gateways (bool): Whether to include master router agents.
    Returns: A list of agents.
    """
    return await handle_get_agents(workspace_id, include_gateways)

@router.post("/api/agents")
async def create_agent(agent: AgentCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create a new AI agent.
    Args:
        agent (AgentCreate): The validated JSON payload containing the agent configuration.
    Returns: The newly created agent data.
    """
    data = agent.dict()
    data["user_id"] = current_user["sub"]
    return await handle_create_agent(data)

@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to dynamically update an agent's settings.
    Args:
        agent_id (str): The ID of the agent to edit.
        payload (dict): A dictionary of the fields to update.
    Returns: The updated agent data.
    """
    return await handle_update_agent(agent_id, payload)

@router.post("/api/agent-projects")
async def create_agent_project(project: AgentProjectCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create a new Multi-Agent Project and its master router.
    Args:
        project (AgentProjectCreate): The new project details.
    Returns: A success object with the new project ID.
    """
    return await handle_create_agent_project(
        project.name, project.description, project.workspace_id, current_user["sub"]
    )

@router.get("/api/agent-projects")
async def get_agent_projects(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to list all projects in a workspace.
    Args:
        workspace_id (str): The workspace to query.
    Returns: A list of projects.
    """
    return await handle_get_agent_projects(workspace_id)

@router.get("/api/agent-projects/{project_id}/sub-agents")
async def get_project_sub_agents(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to list all agents tied to a specific project.
    Args:
        project_id (str): The project to query.
    Returns: A list of agents.
    """
    return await handle_get_project_sub_agents(project_id)

@router.delete("/api/agent-projects/{project_id}")
async def delete_agent_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to entirely delete a project and all its data.
    Args:
        project_id (str): The project to destroy.
    Returns: A success message.
    """
    return await handle_delete_agent_project(project_id)

@router.get("/api/agent-projects/{project_id}/tools")
async def get_project_tools(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to retrieve the tools configured for a project.
    Args:
        project_id (str): The project to query.
    Returns: A list of tools.
    """
    return await handle_get_project_tools(project_id)

@router.put("/api/tools/{tool_id}")
async def update_project_tool(tool_id: str, payload: ToolUpdate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to modify an existing custom tool.
    Args:
        tool_id (str): The ID of the tool to update.
        payload (ToolUpdate): The new tool name and config.
    Returns: A success message.
    """
    return await handle_update_project_tool(tool_id, payload.name, payload.config)

@router.post("/api/agent-projects/{project_id}/tools")
async def create_project_tool(project_id: str, payload: ToolCreate, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint to create a new custom tool.
    Args:
        project_id (str): The project to attach the tool to.
        payload (ToolCreate): The tool name and config.
    Returns: A success object with the new tool ID.
    """
    return await handle_create_project_tool(project_id, payload.name, payload.config)
