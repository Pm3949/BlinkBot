from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from meta_agent_schemas import AgentBlueprint, DeployRequest, SingleAgentResponse
from database import get_db_connection

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/meta-agent",
    tags=["Meta-Agent"]
)

class GenerateBlueprintRequest(BaseModel):
    prompt: str

@router.post("/generate", response_model=AgentBlueprint)
async def generate_blueprint(req: GenerateBlueprintRequest):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY or GOOGLE_API_KEY not configured")

    try:
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "You are the Master Builder LLM for a No-Code Agent-Builder Platform. "
            "Your job is to analyze the client's prompt and output a structured JSON blueprint "
            "detailing the sub-agents, tools, and knowledge bases required to build their desired agent network. "
            "Ensure the output strictly follows the schema. "
            "Based on the client's use-case, generate strict Markdown formatting rules for each specific agent in output_format_instructions. "
            "For example, if it's an e-commerce agent, instruct it to output product images ![alt](url) and links [text](url)."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=req.prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AgentBlueprint,
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
        
        # The response text should be a valid JSON matching the AgentBlueprint model
        return AgentBlueprint.model_validate_json(response.text)

    except Exception as e:
        logger.error(f"Error generating blueprint with Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate blueprint: {str(e)}")

@router.post("/generate-single", response_model=SingleAgentResponse)
async def generate_single_agent(req: GenerateBlueprintRequest):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY or GOOGLE_API_KEY not configured")

    try:
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "You are an expert AI Agent Configurator. "
            "Your job is to analyze the client's request and output a structured JSON configuring a single AI Agent. "
            "Generate a catchy name, a clear description, a very detailed system prompt defining its persona and core rules, "
            "and strict formatting instructions for how it should output responses."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=req.prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SingleAgentResponse,
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
        
        return SingleAgentResponse.model_validate_json(response.text)

    except Exception as e:
        logger.error(f"Error generating single agent with Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate agent: {str(e)}")

@router.post("/deploy")
async def deploy_agent(req: DeployRequest):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Insert into agent_projects
        cursor.execute(
            """
            INSERT INTO agent_projects (workspace_id, name, description, status, blueprint_json)
            VALUES (%s, %s, %s, 'deployed', %s)
            RETURNING id;
            """,
            (req.workspace_id, req.blueprint.project_name, req.blueprint.description, req.blueprint.model_dump_json())
        )
        project_id = cursor.fetchone()[0]

        # 2. Insert into documents (formerly knowledge_bases)
        enabled_kb = req.config_data.get("enabled_knowledge", {})
        for kb in req.blueprint.required_knowledge:
            if enabled_kb.get(kb.id):
                cursor.execute(
                    """
                    INSERT INTO documents (project_id, blueprint_knowledge_id, filename, type, source_uri, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """,
                    (project_id, kb.id, kb.name, kb.type, "")
                )

        # 3. Insert into agent_tools
        enabled_tools = req.config_data.get("enabled_tools", {})
        tools_config = req.config_data.get("tools", {})
        for tool in req.blueprint.required_tools:
            tool_config_data = tools_config.get(tool.id, {})
            # Store the enabled state inside the config so we know if it was skipped
            tool_config_data["is_enabled"] = bool(enabled_tools.get(tool.id))
            # Pre-fill empty fields for query format and headers
            if "query_format" not in tool_config_data:
                tool_config_data["query_format"] = "{}"
            if "headers" not in tool_config_data:
                tool_config_data["headers"] = "{}"
                
            cursor.execute(
                """
                INSERT INTO agent_tools (project_id, workspace_id, blueprint_tool_id, name, config)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (project_id, req.workspace_id, tool.id, tool.name, json.dumps(tool_config_data))
            )

        # 4. Insert Sub-Agents into the main 'agents' table
        # We need to do this in two passes to handle parent_agent_id linking properly
        # First pass: Insert all agents and keep a map of blueprint_id -> real_uuid
        agent_id_map = {}
        for sub_agent in req.blueprint.sub_agents:
            cursor.execute(
                """
                INSERT INTO agents (name, description, system_prompt, output_format, user_id, workspace_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    sub_agent.role, 
                    sub_agent.goal, 
                    sub_agent.backstory,
                    sub_agent.output_format_instructions,
                    req.user_id, 
                    req.workspace_id, 
                    project_id
                )
            )
            real_uuid = cursor.fetchone()[0]
            agent_id_map[sub_agent.id] = real_uuid

        # Second pass: Update parent_agent_id
        for sub_agent in req.blueprint.sub_agents:
            if getattr(sub_agent, 'parent_agent_id', None) and sub_agent.parent_agent_id in agent_id_map:
                real_uuid = agent_id_map[sub_agent.id]
                parent_real_uuid = agent_id_map[sub_agent.parent_agent_id]
                cursor.execute(
                    """
                    UPDATE agents SET parent_agent_id = %s WHERE id = %s
                    """,
                    (parent_real_uuid, real_uuid)
                )

        # 5. Fetch the inserted tools to get their real UUIDs
        cursor.execute("SELECT blueprint_tool_id, id FROM agent_tools WHERE project_id = %s", (project_id,))
        tool_id_map = {row[0]: row[1] for row in cursor.fetchall()}

        conn.commit()
        return {
            "status": "success", 
            "project_id": project_id, 
            "agent_id_map": agent_id_map,
            "tool_id_map": tool_id_map
        }
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error deploying agent network: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
