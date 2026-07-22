import os
import json
import asyncio
from fastapi import HTTPException
from dotenv import load_dotenv
from google import genai
from google.genai import types
from meta_agent_schemas import AgentBlueprint, SingleAgentResponse
from db import meta_agent_repository

load_dotenv()

from utils.logger import get_department_logger

logger = get_department_logger("agent")

from prompts.meta_prompts import NETWORK_SYSTEM_PROMPT, SINGLE_SYSTEM_PROMPT

async def _generate_with_gemini(prompt: str, response_schema, system_instruction: str):
    logger.info("Generating content using Gemini API model...")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Gemini API call failed: API Key is missing in environment variables.")
        raise ValueError("GEMINI_API_KEY not configured")

    logger.debug("Initializing Google GenAI client...")
    client = genai.Client(api_key=api_key)
    last_exc = None
    for attempt in range(1, 4):
        try:
            logger.info(f"Gemini API call attempt {attempt}/3 using gemini-2.5-flash...")
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
            logger.info("Successfully retrieved content response from Gemini API.")
            return response.text
        except Exception as e:
            last_exc = e
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                logger.warning(f"Gemini API unavailable (503) on attempt {attempt}: {str(e)}")
                if attempt < 3:
                    sleep_duration = 1.5 * attempt
                    logger.debug(f"Retrying Gemini call after sleeping {sleep_duration} seconds...")
                    await asyncio.sleep(sleep_duration)
                    continue
            raise
    raise last_exc


async def _generate_with_groq(prompt: str, response_schema_class, system_instruction: str):
    logger.info("Attempting fallback structured generation using Groq API...")
    import httpx

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        logger.error("Groq fallback failed: GROQ_API_KEY is not configured in environment variables.")
        raise ValueError("GROQ_API_KEY not configured")

    schema_json = json.dumps(response_schema_class.model_json_schema(), indent=2)
    full_system = (
        f"{system_instruction}\\n\\n"
        f"You MUST respond with ONLY valid JSON that exactly matches this schema:\\n{schema_json}"
    )

    logger.info("Sending request to Groq llama-3.3-70b-versatile...")
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
        logger.info("Successfully received structured response from Groq API.")
        return data["choices"][0]["message"]["content"]


async def handle_generate_blueprint(prompt: str):
    logger.info(f"Generating Multi-Agent network blueprint for user prompt length: {len(prompt) if prompt else 0}")
    raw_json = None
    provider_used = "gemini"
    try:
        raw_json = await _generate_with_gemini(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
    except Exception as gemini_exc:
        logger.warning(f"Primary Gemini generation failed: {str(gemini_exc)}. Switching to Groq fallback API.")
        provider_used = "groq"
        try:
            raw_json = await _generate_with_groq(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
        except Exception as groq_exc:
            logger.error(f"Structured blueprint generation failed completely. Groq error: {str(groq_exc)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"All providers failed. Gemini: {gemini_exc}. Groq: {groq_exc}")

    try:
        logger.info(f"Blueprint successfully generated via provider: '{provider_used}'")
        return AgentBlueprint.model_validate_json(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse generated JSON structure from {provider_used}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse blueprint from {provider_used}")


async def handle_generate_single_agent(prompt: str):
    logger.info(f"Generating single agent blueprint configuration for prompt length: {len(prompt) if prompt else 0}")
    raw_json = None
    provider_used = "gemini"
    try:
        raw_json = await _generate_with_gemini(prompt, SingleAgentResponse, SINGLE_SYSTEM_PROMPT)
    except Exception as gemini_exc:
        logger.warning(f"Primary Gemini single generation failed: {str(gemini_exc)}. Switching to Groq fallback API.")
        provider_used = "groq"
        try:
            raw_json = await _generate_with_groq(prompt, SingleAgentResponse, SINGLE_SYSTEM_PROMPT)
        except Exception as groq_exc:
            logger.error(f"Single agent generation failed completely. Groq error: {str(groq_exc)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"All providers failed. Gemini: {gemini_exc}. Groq: {groq_exc}")

    try:
        logger.info(f"Single agent configuration successfully generated via provider: '{provider_used}'")
        return SingleAgentResponse.model_validate_json(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse generated single agent JSON from {provider_used}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse single agent from {provider_used}")


async def handle_deploy_agent(req: dict):
    # Sanitize API keys from configuration details log
    sanitized_req = req.copy()
    if "config_data" in sanitized_req and isinstance(sanitized_req["config_data"], dict):
        sanitized_config = sanitized_req["config_data"].copy()
        for k in sanitized_config:
            if "key" in k.lower() or "password" in k.lower() or "token" in k.lower():
                sanitized_config[k] = "[MASKED]"
        sanitized_req["config_data"] = sanitized_config
    
    logger.info(f"Deploying agent blueprint. Workspace ID: {req.get('workspace_id')}")
    try:
        blueprint = AgentBlueprint(**req.get("blueprint"))
        workspace_id = req.get("workspace_id")
        user_id = req.get("user_id")
        config_data = req.get("config_data", {})
        
        logger.debug(f"Deploying blueprint configuration to DB workspace ID: {workspace_id}...")
        result = await meta_agent_repository.deploy_agent_blueprint_to_db(
            workspace_id=workspace_id,
            user_id=user_id,
            blueprint=blueprint,
            config_data=config_data
        )
        logger.info(f"Agent network successfully deployed. Deployment output: {result}")
        return result
    except Exception as e:
        logger.error(f"Error deploying agent network: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
