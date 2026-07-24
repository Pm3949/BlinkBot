"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core generation and deployment handler for Meta-Agents in RAGMate.
It uses Google Gemini models (with Groq as a fallback) to dynamically build 
single-agent configurations or complex multi-agent network topologies ("blueprints") 
based on a user's natural language requests.

From top to bottom, the file performs the following tasks:
1. Imports: Standard libraries, Google GenAI SDK, local schemas, repositories,
   and dotenv configurations.
2. Logging: Initializes an "agent" department logger to audit generation events.
3. Private LLM Connectors:
   - `_generate_with_gemini`: Contacts Google Gemini models, using structured schema outputs
     and applying an exponential backoff retry mechanism on HTTP 503 Service Unavailable errors.
   - `_generate_with_groq`: Fallback structured generation querying Llama-3.3-70b-versatile
     with pydantic schema specifications compiled in the system instructions.
4. Blueprint Gen Handlers:
   - `handle_generate_blueprint`: Builds multi-agent network architectures, falling back
     to Groq if Gemini returns errors.
   - `handle_generate_single_agent`: Generates configuration settings for a single AI agent.
5. Deployment Handler:
   - `handle_deploy_agent`: Validates generated blueprints, masks API keys and tokens, 
     and writes agent structures into database workspace tables.
"""

import os  # System utility to read environment settings
import json  # Parse and format JSON strings
import asyncio  # Asynchronous thread execution controls
from fastapi import HTTPException  # Raise clean HTTP error status codes to client
from dotenv import load_dotenv  # Load local environment settings from .env file
from google import genai  # Google GenAI SDK client
from google.genai import types  # Parameter configurations for Gemini models
from meta_agent_schemas import AgentBlueprint, SingleAgentResponse  # Pydantic schemas validating AI structures
from db import meta_agent_repository  # Database access layer for deploying blueprints

# Load environment configuration variables
load_dotenv()

# Logging utilities
from utils.logger import get_department_logger

# Scope a department logger specifically to "agent" activities
logger = get_department_logger("agent")

from prompts.meta_prompts import NETWORK_SYSTEM_PROMPT, SINGLE_SYSTEM_PROMPT


async def _generate_with_gemini(prompt: str, response_schema, system_instruction: str):
    """
    Sends requests to Google Gemini model (gemini-2.5-flash) to retrieve structured output
    that matches a given Pydantic schema class.
    Retries up to 3 times with exponential backoff on HTTP 503 errors.

    Parameters:
        prompt (str): Natural language user requirement input.
        response_schema (Type[BaseModel]): Pydantic schema structure to shape output JSON.
        system_instruction (str): Core instructions defining model behavior.

    Returns:
        str: Structured output JSON string matching response_schema requirements.

    Exceptions Raised:
        ValueError: Raised if Gemini/Google API keys are missing in env settings.
        Exceptions: Re-raises API exceptions if all retries fail.
    """
    logger.info("Generating content using Gemini API model...")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Gemini API call failed: API Key is missing in environment variables.")
        raise ValueError("GEMINI_API_KEY not configured")

    # Initialize client session with target key
    logger.debug("Initializing Google GenAI client...")
    client = genai.Client(api_key=api_key)
    last_exc = None
    
    # Retry loop to recover from temporary service overloads
    for attempt in range(1, 4):
        try:
            logger.info(f"Gemini API call attempt {attempt}/3 using gemini-2.5-flash...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",         # Enforces output content type JSON
                    response_schema=response_schema,               # Forces schema formatting
                    system_instruction=system_instruction,         # Sets core behavior prompt instructions
                    temperature=0.2,                               # Low temperature ensures output accuracy
                ),
            )
            logger.info("Successfully retrieved content response from Gemini API.")
            return response.text
        except Exception as e:
            last_exc = e
            error_str = str(e)
            # If server is overloaded (503 Service Unavailable / UNAVAILABLE), retry after sleep delay
            if "503" in error_str or "UNAVAILABLE" in error_str:
                logger.warning(f"Gemini API unavailable (503) on attempt {attempt}: {str(e)}")
                if attempt < 3:
                    # Exponential sleep delay based on attempt index
                    sleep_duration = 1.5 * attempt
                    logger.debug(f"Retrying Gemini call after sleeping {sleep_duration} seconds...")
                    await asyncio.sleep(sleep_duration)
                    continue
            raise
    raise last_exc


async def _generate_with_groq(prompt: str, response_schema_class, system_instruction: str):
    """
    Fallback query that requests structured JSON outputs from Llama-3.3-70b-versatile via Groq.

    Parameters:
        prompt (str): Natural language user requirement input.
        response_schema_class (Type[BaseModel]): Pydantic schema class.
        system_instruction (str): Core instructions defining model behavior.

    Returns:
        str: Output JSON string matching schema parameters.

    Exceptions Raised:
        ValueError: Raised if Groq keys are missing in env settings.
        HTTPException/Exception: Re-raises connection errors.
    """
    logger.info("Attempting fallback structured generation using Groq API...")
    import httpx

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        logger.error("Groq fallback failed: GROQ_API_KEY is not configured in environment variables.")
        raise ValueError("GROQ_API_KEY not configured")

    # Serialize target JSON schema definition to request block
    schema_json = json.dumps(response_schema_class.model_json_schema(), indent=2)
    full_system = (
        f"{system_instruction}\n\n"
        f"You MUST respond with ONLY valid JSON that exactly matches this schema:\n{schema_json}"
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
                # Request JSON output structure format
                "response_format": {"type": "json_object"}
            }
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Successfully received structured response from Groq API.")
        return data["choices"][0]["message"]["content"]


async def handle_generate_blueprint(prompt: str):
    """
    Generates a multi-agent network configuration blueprint.
    Queries Gemini as primary, falling back to Groq if Gemini returns errors.

    Parameters:
        prompt (str): Natural language user requirement description.

    Returns:
        AgentBlueprint: Instantiated pydantic AgentBlueprint configuration.

    Exceptions Raised:
        HTTPException(500): Raised if all AI model providers fail.
    """
    logger.info(f"Generating Multi-Agent network blueprint for user prompt length: {len(prompt) if prompt else 0}")
    raw_json = None
    provider_used = "gemini"
    try:
        # Trigger Gemini primary query
        raw_json = await _generate_with_gemini(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
    except Exception as gemini_exc:
        logger.warning(f"Primary Gemini generation failed: {str(gemini_exc)}. Switching to Groq fallback API.")
        provider_used = "groq"
        try:
            # Trigger Groq fallback query
            raw_json = await _generate_with_groq(prompt, AgentBlueprint, NETWORK_SYSTEM_PROMPT)
        except Exception as groq_exc:
            logger.error(f"Structured blueprint generation failed completely. Groq error: {str(groq_exc)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"All providers failed. Gemini: {gemini_exc}. Groq: {groq_exc}")

    try:
        logger.info(f"Blueprint successfully generated via provider: '{provider_used}'")
        # Validate and return pydantic object details
        return AgentBlueprint.model_validate_json(raw_json)
    except Exception as e:
        logger.error(f"Failed to parse generated JSON structure from {provider_used}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse blueprint from {provider_used}")


async def handle_generate_single_agent(prompt: str):
    """
    Generates a single AI agent configuration template.
    Queries Gemini as primary, falling back to Groq if Gemini returns errors.

    Parameters:
        prompt (str): Natural language user requirements.

    Returns:
        SingleAgentResponse: Validated pydantic SingleAgentResponse setup.

    Exceptions Raised:
        HTTPException(500): Raised if all AI model providers fail.
    """
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
    """
    Deploys a generated blueprint configuration network to the target workspace tables.
    Masks credential passwords and tokens in output logs before execution.

    Parameters:
        req (dict): Deployment options containing 'blueprint', 'workspace_id', 'user_id', 
                    and connection 'config_data'.

    Returns:
        dict/str: Output status message confirmation.

    Exceptions Raised:
        HTTPException(500): Raised if DB deployment inserts crash.
    """
    # Sanitize API credentials and passwords from debug configurations logs
    sanitized_req = req.copy()
    if "config_data" in sanitized_req and isinstance(sanitized_req["config_data"], dict):
        sanitized_config = sanitized_req["config_data"].copy()
        for k in sanitized_config:
            if "key" in k.lower() or "password" in k.lower() or "token" in k.lower():
                sanitized_config[k] = "[MASKED]"
        sanitized_req["config_data"] = sanitized_config
    
    logger.info(f"Deploying agent blueprint. Workspace ID: {req.get('workspace_id')}")
    try:
        # Load values
        blueprint = AgentBlueprint(**req.get("blueprint"))
        workspace_id = req.get("workspace_id")
        user_id = req.get("user_id")
        config_data = req.get("config_data", {})
        
        # Execute deployment script in meta_agent database repository
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
