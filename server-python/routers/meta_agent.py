import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from core.auth import get_current_user
from meta_agent_schemas import AgentBlueprint, DeployRequest, SingleAgentResponse

from handlers.meta_agent_handler import (
    handle_generate_blueprint,
    handle_generate_single_agent,
    handle_deploy_agent
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/meta-agent",
    tags=["Meta-Agent"]
)

class GenerateBlueprintRequest(BaseModel):
    prompt: str


@router.post("/generate", response_model=AgentBlueprint)
async def generate_blueprint(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint that analyzes a user's prompt and returns a complex, multi-agent JSON blueprint.
    Args:
        req (GenerateBlueprintRequest): The generation request.
    Returns: The generated blueprint.
    """
    return await handle_generate_blueprint(req.prompt)

@router.post("/generate-single", response_model=SingleAgentResponse)
async def generate_single_agent(req: GenerateBlueprintRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint that generates a single, simple chatbot.
    Args:
        req (GenerateBlueprintRequest): The generation request.
    Returns: The single agent blueprint.
    """
    return await handle_generate_single_agent(req.prompt)

@router.post("/deploy")
async def deploy_agent(req: DeployRequest, current_user: dict = Depends(get_current_user)):
    """
    What it does: HTTP endpoint that instantiates a generated blueprint into the database.
    Args:
        req (DeployRequest): The deployment payload.
    Returns: The deployment status.
    """
    # Convert the pydantic model to dict for the handler
    req_dict = req.dict()
    req_dict["user_id"] = current_user["sub"]
    # The blueprint field is complex and handled as dict inside the handler, but we need to ensure it's serializable or passed correctly.
    # req.dict() works perfectly.
    return await handle_deploy_agent(req_dict)
