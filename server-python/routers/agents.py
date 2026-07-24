"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all AI Agent and Project
management actions in the RAGMate backend. It maps incoming HTTP REST requests
directly to the underlying business logic executors defined inside the agent handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard typing libraries (Optional), Pydantic schemas,
   FastAPI endpoints routing components, and JWT authentication modules.
2. Routing Initialization: Declares the APIRouter for 'agents' tag groupings.
3. Input Payload Validation Schemas:
   - `AgentCreate` & `AgentUpdate`: Validates JSON body inputs for creating/updating agents.
   - `AgentProjectCreate`: Validates options for multi-agent supervisor projects.
   - `ToolCreate` & `ToolUpdate`: Validates inputs for workspace API tools.
4. HTTP Routes:
   - GET `/api/agents`: Lists agents configured in a workspace.
   - POST `/api/agents`: Creates a new agent.
   - PUT `/api/agents/{agent_id}`: Modifies agent settings.
   - POST `/api/agent-projects`: Registers supervisor coordinator engines.
   - GET `/api/agent-projects`: Lists active projects.
   - GET `/api/agent-projects/{id}/sub-agents`: Lists sub-agents grouped under projects.
   - DELETE `/api/agent-projects/{id}`: Wipes supervisor projects.
   - GET `/api/agent-projects/{id}/tools`: Lists tools linked to projects.
   - POST/PUT `/api/tools`: Creates or updates custom integration tools.
"""

import logging  # Import python logging library
from typing import Optional  # Import typing for optional arguments
from pydantic import BaseModel  # Import Pydantic models for request payload validation
from fastapi import APIRouter, Depends  # FastAPI Router object and Dependency Injection tools
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import agent logic handlers
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

# Instantiate a scoped file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for agent endpoints, grouping with tags
router = APIRouter(tags=["agents"])

class AgentCreate(BaseModel):
    """
    Validates payload options for creating a new AI Agent.
    """
    name: str                                                 # Agent display name
    description: Optional[str] = ""                           # Detailed description
    llm_provider: str                                         # LLM Provider name (e.g. OpenAI, Groq)
    llm_model: str                                            # LLM Model ID (e.g. gpt-4o)
    embedding_model: Optional[str] = "text-embedding-3-small" # Target text embedding model for RAG search
    chunk_strategy: Optional[str] = "semantic"                # Target text parser chunk strategy
    system_prompt: Optional[str] = ""                         # Core instruction prompt
    output_format: Optional[str] = ""                         # Enforced output format prompt
    api_key: Optional[str] = ""                               # User key override
    language: Optional[str] = "en"                            # Core conversational language
    workspace_id: str                                         # Workspace UUID
    web_search_enabled: bool = False                          # Flag for enabling web search tools
    project_id: Optional[str] = None                          # Multi-agent project UUID (if sub-agent)
    parent_agent_id: Optional[str] = None                     # Coordinator agent UUID (if sub-agent)
    endpoints: Optional[list] = []                            # API endpoints / webhooks list
    databases: Optional[list] = []                            # Target database credentials mapping list
    code_interpreter_enabled: bool = False                    # Flag for enabling sandbox python execution tools
    native_integrations: Optional[list] = []                  # Slack, Gmail, etc. native connections list

class AgentUpdate(BaseModel):
    """
    Validates optional payload options for modifying an existing AI Agent.
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
    Validates payload options for creating a Multi-Agent project supervisor.
    """
    name: str                                                 # Project display name
    description: Optional[str] = ""                           # Project description
    workspace_id: str                                         # Target workspace UUID

class ToolCreate(BaseModel):
    """
    Validates payload options for creating a custom integration tool.
    """
    name: str                                                 # Tool name label
    config: dict                                              # Credentials / parameters dictionary mapping

class ToolUpdate(BaseModel):
    """
    Validates payload options for updating a custom integration tool.
    """
    name: str
    config: dict


@router.get("/api/agents")
async def get_agents(workspace_id: str, include_gateways: bool = False, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list AI agents in a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID query param.
        include_gateways (bool, optional): If true, includes master coordinator supervisor agents.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of agent dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if SQL database queries crash.
    """
    # Route execution task to handlers layer
    return await handle_get_agents(workspace_id, include_gateways)


@router.post("/api/agents")
async def create_agent(agent: AgentCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to create a new AI agent.

    Parameters:
        agent (AgentCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Newly registered agent details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if SQL database writes crash.
    """
    data = agent.dict()  # Convert Pydantic request structure to dictionary
    data["user_id"] = current_user["sub"]  # Inject user ID subject from JWT
    # Route task execution to handlers layer
    return await handle_create_agent(data)


@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    """
    HTTP PUT endpoint to update an agent's settings dynamically.

    Parameters:
        agent_id (str): Target Agent UUID path parameter.
        payload (dict): A dictionary of parameters to update.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: The updated agent details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(404): Raised if agent not found.
        HTTPException(500): Raised if SQL updates fail.
    """
    # Route task execution to handlers layer
    return await handle_update_agent(agent_id, payload)


@router.post("/api/agent-projects")
async def create_agent_project(project: AgentProjectCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to register a new Multi-Agent project supervisor.

    Parameters:
        project (AgentProjectCreate): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Created project UUID.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database inserts crash.
    """
    # Route task execution to handlers layer
    return await handle_create_agent_project(
        project.name, project.description, project.workspace_id, current_user["sub"]
    )


@router.get("/api/agent-projects")
async def get_agent_projects(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list all projects in a workspace.

    Parameters:
        workspace_id (str): Target Workspace UUID.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of project dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if queries crash.
    """
    # Route task execution to handlers layer
    return await handle_get_agent_projects(workspace_id)


@router.get("/api/agent-projects/{project_id}/sub-agents")
async def get_project_sub_agents(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list all agents tied to a specific project.

    Parameters:
        project_id (str): Target Project UUID.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of sub-agent dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    # Route task execution to handlers layer
    return await handle_get_project_sub_agents(project_id)


@router.delete("/api/agent-projects/{project_id}")
async def delete_agent_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP DELETE endpoint to delete a project and all its sub-agents.

    Parameters:
        project_id (str): Target Project UUID.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database wipes crash.
    """
    # Route task execution to handlers layer
    return await handle_delete_agent_project(project_id)


@router.get("/api/agent-projects/{project_id}/tools")
async def get_project_tools(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    HTTP GET endpoint to list custom integration tools configured for a project.

    Parameters:
        project_id (str): Target Project UUID.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        list: A list of tool dictionaries.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database queries fail.
    """
    # Route task execution to handlers layer
    return await handle_get_project_tools(project_id)


@router.put("/api/tools/{tool_id}")
async def update_project_tool(tool_id: str, payload: ToolUpdate, current_user: dict = Depends(get_current_user)):
    """
    HTTP PUT endpoint to update custom tool configs.

    Parameters:
        tool_id (str): Target Tool UUID.
        payload (ToolUpdate): Pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if updates fail.
    """
    # Route task execution to handlers layer
    return await handle_update_project_tool(tool_id, payload.name, payload.config)


@router.post("/api/agent-projects/{project_id}/tools")
async def create_project_tool(project_id: str, payload: ToolCreate, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint to create a new custom tool.

    Parameters:
        project_id (str): Target Project UUID.
        payload (ToolCreate): Pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Created tool UUID.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database writes crash.
    """
    # Route task execution to handlers layer
    return await handle_create_project_tool(project_id, payload.name, payload.config)
