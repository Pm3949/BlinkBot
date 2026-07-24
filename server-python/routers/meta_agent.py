"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Meta-Agent (AI-driven agent
builders / generators) in the RAGMate backend. It maps inbound HTTP REST requests
directly to the underlying business logic executors defined inside the meta agent
handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads logging libraries, Pydantic validation schemas, FastAPI APIRouter,
   JWT token checks, and local schema declarations.
2. Routing Initialization: Declares the APIRouter for 'Meta-Agent' namespaces.
3. Input Payload Validation Schema:
   - `GenerateBlueprintRequest`: Validates prompts submitted to instruct the LLM builder.
4. HTTP Routes:
   - POST `/generate`: Analyzes prompts and generates complex multi-agent blueprints.
   - POST `/generate-single`: Generates simple, single-agent configurations.
   - POST `/deploy`: Spawns the generated blueprints inside databases (instantiation).
"""

import logging  # Import python logging library
from pydantic import BaseModel  # Pydantic BaseModels for request validations
from fastapi import APIRouter, Depends  # FastAPI APIRouter and Dependency injection Depends
from core.auth import get_current_user  # JWT helper to authenticate requests

# Import meta-agent schemas
from meta_agent_schemas import AgentBlueprint, DeployRequest, SingleAgentResponse

# Import meta-agent logic handlers
from handlers.meta_agent_handler import (
    handle_generate_blueprint,
    handle_generate_single_agent,
    handle_deploy_agent
)

# Instantiate file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router for meta agent endpoints, prefixing all routes with '/api/meta-agent'
router = APIRouter(
    prefix="/api/meta-agent",
    tags=["Meta-Agent"]
)

class GenerateBlueprintRequest(BaseModel):
    """
    Validates payload options for creating agent blueprints.
    """
    prompt: str                                # Instructions describing desired agents behavior


@router.post("/generate", response_model=AgentBlueprint)
async def generate_blueprint(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint generating complex multi-agent blueprints from instructions.
    Checks JWT tokens in request headers.

    Parameters:
        req (GenerateBlueprintRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        AgentBlueprint: The generated blueprint details.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if LLM blueprint creation crashes.
    """
    # Route execution to handlers layer
    return await handle_generate_blueprint(req.prompt)


@router.post("/generate-single", response_model=SingleAgentResponse)
async def generate_single_agent(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint generating simple single chatbot configurations.
    Checks JWT tokens in request headers.

    Parameters:
        req (GenerateBlueprintRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        SingleAgentResponse: The single agent configuration.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if LLM creation crashes.
    """
    # Route execution to handlers layer
    return await handle_generate_single_agent(req.prompt)


@router.post("/deploy")
async def deploy_agent(req: DeployRequest, current_user: dict = Depends(get_current_user)):
    """
    HTTP POST endpoint installing/instantiating generated blueprints inside databases.
    Checks JWT tokens in request headers.

    Parameters:
        req (DeployRequest): The pydantic-validated request payload.
        current_user (dict): JWT payload automatically injected by authentication dependency.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(401): Raised if token is invalid.
        HTTPException(500): Raised if database inserts crash.
    """
    # Convert Pydantic request structure to dictionary
    req_dict = req.dict()
    # Inject user ID subject from JWT
    req_dict["user_id"] = current_user["sub"]
    # Route execution to handlers layer
    return await handle_deploy_agent(req_dict)
