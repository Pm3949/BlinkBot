import logging
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from core.auth import get_current_user
from db import workspace_tools_repository
from utils.security import validate_python_tool_code

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workspace_tools"])

class ToolCreate(BaseModel):
    name: str
    tool_type: str  # 'api_webhook', 'database', 'oauth', 'python_code'
    configuration: dict
    code_content: Optional[str] = None

class ToolUpdate(BaseModel):
    name: str
    configuration: dict
    code_content: Optional[str] = None

@router.get("/api/workspaces/{workspace_id}/tools")
async def get_workspace_tools(workspace_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return await workspace_tools_repository.get_workspace_tools(workspace_id)
    except Exception as e:
        logger.error(f"Error fetching tools for workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/workspaces/{workspace_id}/tools")
async def create_workspace_tool(workspace_id: str, payload: ToolCreate, current_user: dict = Depends(get_current_user)):
    if payload.tool_type not in ('api_webhook', 'database', 'oauth', 'python_code'):
        return JSONResponse(status_code=400, content={"error": "Invalid tool_type. Must be api_webhook, database, oauth, or python_code."})
    
    if payload.tool_type == "python_code":
        if not payload.code_content:
            return JSONResponse(status_code=400, content={"error": "Python script content is required for python_code tool type."})
        try:
            validate_python_tool_code(payload.code_content)
        except ValueError as ve:
            return JSONResponse(status_code=400, content={"error": str(ve)})
            
    try:
        tool = await workspace_tools_repository.create_workspace_tool(
            workspace_id=workspace_id,
            name=payload.name,
            tool_type=payload.tool_type,
            configuration=payload.configuration,
            code_content=payload.code_content
        )
        if not tool:
            raise HTTPException(status_code=500, detail="Failed to create workspace tool.")
        return tool
    except Exception as e:
        logger.error(f"Error creating tool in workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/workspaces/{workspace_id}/tools/{tool_id}")
async def update_workspace_tool(workspace_id: str, tool_id: str, payload: ToolUpdate, current_user: dict = Depends(get_current_user)):
    if payload.code_content is not None:
        try:
            validate_python_tool_code(payload.code_content)
        except ValueError as ve:
            return JSONResponse(status_code=400, content={"error": str(ve)})
            
    try:
        tool = await workspace_tools_repository.update_workspace_tool(
            tool_id=tool_id,
            name=payload.name,
            configuration=payload.configuration,
            code_content=payload.code_content
        )
        if not tool:
            raise HTTPException(status_code=404, detail="Workspace tool not found.")
        return tool
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"Error updating tool {tool_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/workspaces/{workspace_id}/tools/{tool_id}")
async def delete_workspace_tool(workspace_id: str, tool_id: str, current_user: dict = Depends(get_current_user)):
    try:
        success = await workspace_tools_repository.delete_workspace_tool(tool_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workspace tool not found.")
        return {"status": "success", "message": "Workspace tool deleted successfully."}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"Error deleting tool {tool_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/agents/{agent_id}/tools")
async def get_agent_attached_tools(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return await workspace_tools_repository.get_agent_attached_tools(agent_id)
    except Exception as e:
        logger.error(f"Error fetching tools for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/agents/{agent_id}/tools/{tool_id}")
async def attach_tool_to_agent(agent_id: str, tool_id: str, current_user: dict = Depends(get_current_user)):
    try:
        await workspace_tools_repository.attach_tool_to_agent(agent_id, tool_id)
        return {"status": "success", "message": "Tool attached successfully."}
    except Exception as e:
        logger.error(f"Error attaching tool {tool_id} to agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/agents/{agent_id}/tools/{tool_id}")
async def detach_tool_from_agent(agent_id: str, tool_id: str, current_user: dict = Depends(get_current_user)):
    try:
        success = await workspace_tools_repository.detach_tool_from_agent(agent_id, tool_id)
        if not success:
            raise HTTPException(status_code=404, detail="Attachment or tool not found.")
        return {"status": "success", "message": "Tool detached successfully."}
    except Exception as e:
        logger.error(f"Error detaching tool {tool_id} from agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


GLOBAL_TOOLS_REGISTRY = [
    {
        "id": "web_search",
        "name": "Web Search (DuckDuckGo)",
        "tool_type": "api_webhook",
        "description": "Search the internet for real-time information using DuckDuckGo.",
        "is_global": True,
        "tool_key": "web_search"
    },
    {
        "id": "wikipedia",
        "name": "Wikipedia Search",
        "tool_type": "api_webhook",
        "description": "Query Wikipedia articles for historical, geographical, or general information.",
        "is_global": True,
        "tool_key": "wikipedia"
    },
    {
        "id": "arxiv_research",
        "name": "ArXiv Scientific Papers",
        "tool_type": "api_webhook",
        "description": "Query ArXiv directory for scientific research papers and publications.",
        "is_global": True,
        "tool_key": "arxiv_research"
    },
    {
        "id": "calculator",
        "name": "Math Calculator",
        "tool_type": "api_webhook",
        "description": "Natively compute complex math calculations and numeric operations.",
        "is_global": True,
        "tool_key": "calculator"
    }
]


@router.get("/api/tools/global-registry")
async def get_global_registry(current_user: dict = Depends(get_current_user)):
    return GLOBAL_TOOLS_REGISTRY


class ProvisionPayload(BaseModel):
    template_id: str
    workspace_id: str


@router.get("/api/tools/templates")
async def get_tool_templates(current_user: dict = Depends(get_current_user)):
    try:
        import os
        import json as json_lib
        templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tool_templates.json")
        if not os.path.exists(templates_path):
            return []
        with open(templates_path, "r", encoding="utf-8") as f:
            return json_lib.load(f)
    except Exception as e:
        logger.error(f"Error loading tool templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tools/provision")
async def provision_tool(payload: ProvisionPayload, current_user: dict = Depends(get_current_user)):
    try:
        import os
        import json as json_lib
        
        # 1. Check if it's a global tool
        global_tool = None
        for t in GLOBAL_TOOLS_REGISTRY:
            if t["id"] == payload.template_id:
                global_tool = t
                break
                
        if global_tool:
            new_tool = await workspace_tools_repository.create_workspace_tool(
                workspace_id=payload.workspace_id,
                name=global_tool["name"],
                tool_type=global_tool["tool_type"],
                configuration={"description": global_tool["description"]},
                code_content=None,
                is_global=True,
                tool_key=global_tool["tool_key"]
            )
            if not new_tool:
                raise HTTPException(status_code=500, detail="Failed to provision global tool.")
            return new_tool
            
        # 2. Check templates if not a global tool
        templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tool_templates.json")
        if not os.path.exists(templates_path):
            raise HTTPException(status_code=404, detail="Templates registry not found.")
            
        with open(templates_path, "r", encoding="utf-8") as f:
            templates = json_lib.load(f)
            
        target_template = None
        for t in templates:
            if t["id"] == payload.template_id:
                target_template = t
                break
                
        if not target_template:
            raise HTTPException(status_code=404, detail=f"Template/Global tool with ID '{payload.template_id}' not found.")
            
        # Provision the tool under the workspace
        new_tool = await workspace_tools_repository.create_workspace_tool(
            workspace_id=payload.workspace_id,
            name=target_template["name"],
            tool_type=target_template["tool_type"],
            configuration=target_template.get("configuration", {}),
            code_content=target_template.get("code_content")
        )
        if not new_tool:
            raise HTTPException(status_code=500, detail="Failed to provision workspace tool from template.")
        return new_tool
    except Exception as e:
        logger.error(f"Error provisioning tool template {payload.template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
