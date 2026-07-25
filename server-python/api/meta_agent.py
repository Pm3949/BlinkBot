"""
================================================================================
META-AGENT GENERATOR & BLUEPRINT DEPLOYER ROUTER LAYER (meta_agent.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for the platform's Meta-Agent engine.
It leverages generative models to translate natural language prompts into structural agent definitions:
1. Multi-Agent Blueprints (/generate): Analyzes complex requirements and generates a JSON blueprint
   defining a multi-agent network (Network Manager, General Assistant, and specific task-based sub-agents).
2. Single-Agent Blueprints (/generate-single): Generates a simple, isolated agent configuration.
3. Deployment (/deploy): Instantiates the generated JSON blueprints into active database records,
   automatically setting up workspace associations, parent-child agent linkages, and default prompts.

DATA FLOW:
- Routes are protected by the `get_current_user` JWT dependency.
- Inputs are validated using schemas (`GenerateBlueprintRequest`, `DeployRequest`).
- Request parameters are passed to `handlers/meta_agent_handler.py` for LLM execution and database instantiation.
"""

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user
from meta_agent_schemas import AgentBlueprint, DeployRequest, SingleAgentResponse

# Import the meta-agent generation and deployment handlers.
from handlers.meta_agent_handler import (
    handle_generate_blueprint,
    handle_generate_single_agent,
    handle_deploy_agent
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tag categories and path prefixes.
router = APIRouter(
    prefix="/api/meta-agent",
    tags=["Meta-Agent"]
)

# ==========================================
# PYDANTIC INPUT VALIDATION SCHEMAS
# ==========================================

class GenerateBlueprintRequest(BaseModel):
    """
    Validation schema for prompting the meta-agent generation engine.
    """
    prompt: str # The user prompt describing the desired agent configuration


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.post("/generate", response_model=AgentBlueprint)
async def generate_blueprint(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates a multi-agent JSON blueprint from a prompt description.

    Purpose:
        Analyzes a prompt and returns a multi-agent blueprint definition
        specifying roles, sub-agents, system prompts, and tools.

    Parameters:
        req (GenerateBlueprintRequest): Contains the user prompt description.
        current_user (dict): JWT details.

    Returns:
        AgentBlueprint: The generated multi-agent blueprint model schema.

    Side Effects / State Changes:
        - None. Read-only generator.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification checks fail.
        - Raises 400 Bad Request if the prompt is empty or model generation fails.
    """
    # Generate the blueprint schema using the handler.
    return await handle_generate_blueprint(req.prompt)


@router.post("/generate-single", response_model=SingleAgentResponse)
async def generate_single_agent(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates a single-agent JSON blueprint from a prompt description.

    Purpose:
        Generates a blueprint for a simple, single-purpose assistant.

    Parameters:
        req (GenerateBlueprintRequest): Contains the user prompt description.
        current_user (dict): JWT details.

    Returns:
        SingleAgentResponse: The generated single-agent blueprint model schema.

    Side Effects / State Changes:
        - None. Read-only generator.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification checks fail.
        - Raises 400 Bad Request if model generation fails.
    """
    # Generate the single agent configuration.
    return await handle_generate_single_agent(req.prompt)


@router.post("/deploy")
async def deploy_agent(req: DeployRequest, current_user: dict = Depends(get_current_user)):
    """
    Instantiates a generated blueprint into active database records.

    Purpose:
        Saves a generated agent configuration to the database.

    Parameters:
        req (DeployRequest): Contains the target workspace ID and the JSON blueprint definition.
        current_user (dict): JWT details.

    Returns:
        dict: Success confirmation and deployment status.

    Side Effects / State Changes:
        - Writes new rows to the `agents`, `agent_projects`, and associated tables in the database.

    Errors / Exceptions:
        - Raises 401/403 if unauthorized.
        - Raises 400 if the blueprint structure is invalid or missing required keys.
    """
    # Convert Pydantic model parameters to a dictionary.
    req_dict = req.dict()
    # Inject the user's UUID.
    req_dict["user_id"] = current_user["sub"]
    # Deploy the agent configuration.
    return await handle_deploy_agent(req_dict)

