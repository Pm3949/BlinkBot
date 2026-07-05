import os
import json
import logging
import asyncio
from fastapi import HTTPException
from dotenv import load_dotenv
from google import genai
from google.genai import types
from meta_agent_schemas import AgentBlueprint, SingleAgentResponse
from database_layer import meta_agent_repository

load_dotenv()

logger = logging.getLogger(__name__)

NETWORK_SYSTEM_PROMPT = (
    "You are the Master Builder LLM for a No-Code Agent-Builder Platform. "
    "Your job is to analyze the client's prompt and output a structured JSON blueprint "
    "detailing the sub-agents, tools, and knowledge bases required to build their desired agent network. "
    "Ensure the output strictly follows the schema. "
    "Based on the client's use-case, generate strict Markdown formatting rules for each specific agent in output_format_instructions. "
    "For example, if it's an e-commerce agent, instruct it to output product images ![alt](url) and links [text](url)."
)

SINGLE_SYSTEM_PROMPT = (
    "You are an expert AI Agent Configurator. "
    "Your job is to analyze the client's request and output a structured JSON configuring a single AI Agent. "
    "Generate a catchy name, a clear description, a very detailed system prompt defining its persona and core rules, "
    "and strict formatting instructions for how it should output responses."
)


async def _generate_with_gemini(prompt: str, response_schema, system_instruction: str):
    """
    What it does: Primary Generator: Uses Google's Gemini 2.5 Flash to generate structured output.
    Args:
        prompt (str): The user's prompt.
        response_schema: The pydantic schema.
        system_instruction (str): The system prompt.
    Returns: The generated JSON string.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)
    last_exc = None
    for attempt in range(1, 4):
        try:
            logger.info(f"Gemini attempt {attempt}/3")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    system_instruction=system_instruction,
                    temperature=0.2,
                ),
            )
            return response.text
        except Exception as e:
            last_exc = e
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                logger.warning(f"Gemini 503 on attempt {attempt}: {e}")
                if attempt < 3:
                    await asyncio.sleep(1.5 * attempt)
                    continue
            raise
    raise last_exc


async def _generate_with_groq(prompt: str, response_schema_class, system_instruction: str):
    """
    What it does: Fallback Generator: Uses Groq's Llama 3 API.
    Args:
        prompt (str): The user's prompt.
        response_schema_class: The pydantic schema class.
        system_instruction (str): The system prompt.
    Returns: The generated JSON string.
    """
    import httpx

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not configured")

    schema_json = json.dumps(response_schema_class.model_json_schema(), indent=2)
    full_system = (
        f"{system_instruction}\\n\\n"
        f"You MUST respond with ONLY valid JSON that exactly matches this schema:\\n{schema_json}"
    )

    logger.info("Falling back to Groq llama-3.3-70b-versatile")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def handle_generate_blueprint(prompt: str):
    """
    What it does: Analyzes a user's prompt and returns a complex, multi-agent JSON blueprint.
    Args:
        prompt (str): The user's prompt.
    Returns: The generated blueprint.
    """
    raw_json = None
    provider_used = "gemini"
    try:
        raw_json = await _generate_with_gemini(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
    except Exception as gemini_exc:
        logger.warning(f"Gemini failed after retries: {gemini_exc}. Switching to Groq.")
        provider_used = "groq"
        try:
            raw_json = await _generate_with_groq(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
        except Exception as groq_exc:
            logger.error(f"Groq also failed: {groq_exc}")
            raise HTTPException(status_code=500, detail=f"All providers failed. Gemini: {gemini_exc}. Groq: {groq_exc}")

    try:
        logger.info(f"Blueprint generated via {provider_used}")
        return AgentBlueprint.model_validate_json(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse blueprint JSON from {provider_used}: {e}\\nRaw: {raw_json[:500]}")
        raise HTTPException(status_code=500, detail=f"Failed to parse blueprint from {provider_used}")


async def handle_generate_single_agent(prompt: str):
    """
    What it does: Analyzes a user's request and outputs a structured JSON configuring a single AI Agent.
    Args:
        prompt (str): The user's prompt.
    Returns: The generated single agent configuration.
    """
    raw_json = None
    provider_used = "gemini"
    try:
        raw_json = await _generate_with_gemini(prompt, SingleAgentResponse, SINGLE_SYSTEM_PROMPT)
    except Exception as gemini_exc:
        logger.warning(f"Gemini failed after retries (single): {gemini_exc}. Switching to Groq.")
        provider_used = "groq"
        try:
            raw_json = await _generate_with_groq(prompt, SingleAgentResponse, SINGLE_SYSTEM_PROMPT)
        except Exception as groq_exc:
            logger.error(f"Groq also failed (single): {groq_exc}")
            raise HTTPException(status_code=500, detail=f"All providers failed. Gemini: {gemini_exc}. Groq: {groq_exc}")

    try:
        logger.info(f"Single agent generated via {provider_used}")
        return SingleAgentResponse.model_validate_json(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse single agent JSON from {provider_used}: {e}\\nRaw: {raw_json[:500]}")
        raise HTTPException(status_code=500, detail=f"Failed to parse single agent from {provider_used}")


async def handle_deploy_agent(req: dict):
    """
    What it does: Formally instantiates a generated blueprint in the database.
    Args:
        req (dict): The deployment payload.
    Returns: The deployment status and ID maps.
    """
    try:
        blueprint = AgentBlueprint(**req.get("blueprint"))
        workspace_id = req.get("workspace_id")
        user_id = req.get("user_id")
        config_data = req.get("config_data", {})
        
        result = await meta_agent_repository.deploy_agent_blueprint_to_db(
            workspace_id=workspace_id,
            user_id=user_id,
            blueprint=blueprint,
            config_data=config_data
        )
        return result
    except Exception as e:
        logger.error(f"Error deploying agent network: {e}")
        raise HTTPException(status_code=500, detail=str(e))
