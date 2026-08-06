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
