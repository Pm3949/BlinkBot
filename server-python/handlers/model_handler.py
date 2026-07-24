"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core business logic handler for managing AI models
(LLMs) and checking credentials connectivity in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard HTTP client libraries (aiohttp), FastAPI exceptions,
   and model database repositories.
2. Logging: Initializes a department logger named "system" to log model activations,
   registrations, and health test results.
3. Database Model Handlers:
   - `handle_get_active_models`: Retrieves active models and groups them by provider
     (OpenAI, Anthropic, Gemini, Groq, Ollama, etc.) for UI dropdowns.
   - `handle_get_all_models`: Fetches all models for administrative configurations.
   - `handle_create_model`, `handle_update_model`, `handle_delete_model`: Performs standard
     CRUD operations in the model settings tables.
4. Provider Connectivity Testing (`handle_test_provider_key`): Initiates test requests
   to each provider's endpoints (e.g. Google Gemini, Anthropic, OpenAI, HuggingFace) to verify 
   API key validity, automatically seeding Ollama local models when Ollama connection succeeds.
5. Model Invocation Testing (`handle_test_single_model`): Tests direct inference calls
   and checks tool-binding capability, returning user-friendly validation messages on quota or authentication failure.
"""

import logging  # Import python logging library
import aiohttp  # Import HTTP client to perform asynchronous web requests
from fastapi import HTTPException  # Raise clean HTTP errors to the client
from db import model_repository  # Database access repository for model settings

# Logger utility
from utils.logger import get_department_logger

# Set up department logger specifically scoped to "system" activities
logger = get_department_logger("system")


async def handle_get_active_models(user_id: str = None):
    """
    Retrieves all active models and groups them by provider for the frontend interface.

    Parameters:
        user_id (str, optional): The unique database UUID identifying the user.

    Returns:
        dict: A dictionary containing 'providers' (grouped list) and 'models' (flat list).

    Exceptions Raised:
        HTTPException(500): Raised if SQL database queries fail.
    """
    try:
        # Fetch active models list from the repository
        models = await model_repository.get_active_models(user_id=user_id)
        grouped = {}
        
        # Group models by their respective providers
        for m in models:
            prov = m["provider"]
            if prov not in grouped:
                grouped[prov] = []
            grouped[prov].append(m)
            
        return {"providers": grouped, "models": models}
    except Exception as e:
        logger.error(f"Error fetching active models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_get_all_models(user_id: str = None):
    """
    Retrieves all models in the system. Restricted to administrators.

    Parameters:
        user_id (str, optional): The unique database UUID identifying the administrator.

    Returns:
        dict: A dictionary containing 'models' list.

    Exceptions Raised:
        HTTPException(500): Raised if SQL queries fail.
    """
    try:
        # Fetch all models from the repository
        models = await model_repository.get_all_models(user_id=user_id)
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching all models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_create_model(payload: dict, user_id: str = None):
    """
    Creates and registers a new model entry in the database.

    Parameters:
        payload (dict): Payload containing:
            - 'name' (str): Model label display name.
            - 'model_id' (str): Provider-specific model ID.
            - 'provider' (str): Model provider name.
        user_id (str, optional): Creator's User ID.

    Returns:
        dict: A status confirmation message and the newly registered model object.

    Exceptions Raised:
        HTTPException(400): Raised if required fields ('name', 'model_id', 'provider') are missing.
        HTTPException(500): Raised if SQL database insert crashes.
    """
    try:
        # Check required fields
        if not payload.get("name") or not payload.get("model_id") or not payload.get("provider"):
            raise HTTPException(status_code=400, detail="name, model_id, and provider are required")
        
        # Write record to the DB
        model = await model_repository.create_model(payload, user_id=user_id)
        return {"status": "success", "model": model}
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_update_model(model_id: str, payload: dict, user_id: str = None):
    """
    Updates the parameters of an existing model configuration.

    Parameters:
        model_id (str): The unique database UUID identifying the model.
        payload (dict): Update parameter dictionary.
        user_id (str, optional): The requesting user's UUID.

    Returns:
        dict: A success message and the updated model details.

    Exceptions Raised:
        HTTPException(404): Raised if the target model ID is not found.
        HTTPException(500): Raised if database updates fail.
    """
    try:
        # Call update query in database repository
        updated = await model_repository.update_model(model_id, payload, user_id=user_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"status": "success", "model": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_delete_model(model_id: str, user_id: str = None):
    """
    Removes a model configuration from the database.

    Parameters:
        model_id (str): The unique database UUID of the target model.
        user_id (str, optional): User ID requesting deletion.

    Returns:
        dict: Deletion status confirmation message.

    Exceptions Raised:
        HTTPException(404): Raised if the model ID is not found.
        HTTPException(500): Raised if database deletions fail.
    """
    try:
        # Call deletion scripts in database repository
        count = await model_repository.delete_model(model_id, user_id=user_id)
        if count == 0:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"status": "success", "message": "Model deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_test_provider_key(provider: str, api_key: str, base_url: str = None):
    """
    Verifies connection credentials to an external provider's endpoints (e.g. OpenAI, Google Gemini, Ollama).
    Automatically syncs local models from local Ollama instances on connection success.

    Parameters:
        provider (str): Provider identity name.
        api_key (str): Provider credential key.
        base_url (str, optional): Target URL (for local models).

    Returns:
        dict: Connection status configuration and message.

    Exceptions Raised:
        HTTPException(400): Raised if provider parameter is missing.
    """
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")

    try:
        async with aiohttp.ClientSession() as session:
            # 1. OpenAI Connectivity Check
            if provider == "openai":
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "OpenAI API Key is valid!"}
                    return {"status": "error", "message": f"OpenAI authentication failed (HTTP {resp.status})"}

            # 2. Groq Connectivity Check
            elif provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "Groq API Key is valid!"}
                    return {"status": "error", "message": f"Groq authentication failed (HTTP {resp.status})"}

            # 3. OpenRouter Connectivity Check
            elif provider == "openrouter":
                url = "https://openrouter.ai/api/v1/auth/key"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "OpenRouter API Key is valid!"}
                    return {"status": "error", "message": f"OpenRouter authentication failed (HTTP {resp.status})"}

            # 4. HuggingFace Connectivity Check
            elif provider == "huggingface":
                url = "https://huggingface.co/api/whoami-v2"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "HuggingFace Token is valid!"}
                    return {"status": "error", "message": f"HuggingFace authentication failed (HTTP {resp.status})"}

            # 5. Local Ollama Server Connectivity Check & Auto-Seeding
            elif provider == "ollama":
                target_url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
                async with session.get(target_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get("models", [])
                        model_names = [m.get("name") for m in models if m.get("name")]

                        # Auto-seed retrieved local models into system models tables
                        for name in model_names:
                            try:
                                await model_repository.create_model({
                                    "provider": "ollama",
                                    "model_id": name,
                                    "name": f"{name} (Local)",
                                    "description": f"Local model '{name}' running on local Ollama instance",
                                    "requires_key": False,
                                    "category": "General"
                                })
                            except Exception:
                                pass # Silently ignore duplicates if already registered in database

                        count_str = f" Synced {len(model_names)} local models: {', '.join(model_names)}" if model_names else ""
                        return {"status": "connected", "message": f"Ollama server is reachable!{count_str}"}
                    return {"status": "error", "message": f"Ollama connection failed (HTTP {resp.status})"}

            # 6. Anthropic Claude Connectivity Check
            elif provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {"model": "claude-3-5-sonnet-20241022", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
                async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
                    if resp.status in [200, 400]: # 400 Bad Request indicates key verified but request format was incomplete (which is fine for authentication test)
                        return {"status": "connected", "message": "Anthropic API Key is valid!"}
                    return {"status": "error", "message": f"Anthropic authentication failed (HTTP {resp.status})"}

            # 7. Google Gemini Connectivity Check
            elif provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "Google Gemini API Key is valid!"}
                    return {"status": "error", "message": f"Gemini authentication failed (HTTP {resp.status})"}

            else:
                return {"status": "connected", "message": f"Provider '{provider}' configured."}

    except Exception as e:
        logger.error(f"Error testing provider key for {provider}: {e}")
        return {"status": "error", "message": f"Connection error: {str(e)}"}


async def handle_test_single_model(payload: dict, user_id: str = None):
    """
    Tests live invocation completions of a single model, and checks for tool-binding support.
    Automatically decrypts custom API keys, and formats user-friendly error messages
    on credentials / quota errors.

    Parameters:
        payload (dict): Options containing 'provider', 'model_id', 'api_key', 'base_url'.
        user_id (str, optional): Target User UUID.

    Returns:
        dict: Completion status response payload.

    Exceptions Raised:
        HTTPException(400): Raised if required parameters ('provider', 'model_id') are missing.
    """
    provider = payload.get("provider")
    model_id = payload.get("model_id")
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")

    if not provider or not model_id:
        raise HTTPException(status_code=400, detail="provider and model_id are required")

    # If the key is masked (represented as asterisks) and is custom_openai, fetch/decrypt the original key from DB
    if (not api_key or api_key.startswith("********")) and provider == "custom_openai":
        try:
            from database import get_db_cursor_async
            from fastapi.concurrency import run_in_threadpool
            async with get_db_cursor_async(commit=False) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "SELECT api_key, base_url FROM ai_models WHERE model_id = %s AND (user_id IS NULL OR user_id = %s)",
                    (model_id, user_id)
                )
                row = await run_in_threadpool(cursor.fetchone)
                if row:
                    from core.security import decrypt_key
                    if row[0]:
                        api_key = decrypt_key(row[0])
                    if row[1] and not base_url:
                        base_url = row[1]
        except Exception as e:
            logger.error(f"Error fetching custom model key for testing: {e}")

    # Fetch user's saved API key if not explicitly provided
    if not api_key:
        try:
            from db import settings_repository
            from core.security import decrypt_key
            settings = await settings_repository.get_effective_user_settings(user_id) if user_id else None
            if settings:
                provider_index_map = {
                    "openai": 0,
                    "groq": 1,
                    "gemini": 2,
                    "openrouter": 3,
                    "anthropic": 4,
                    "huggingface": 5
                }
                idx = provider_index_map.get(provider.lower())
                if idx is not None and settings[idx]:
                    api_key = decrypt_key(settings[idx])
        except Exception as e:
            logger.error(f"Error fetching/decrypting key for test model: {e}")

    try:
        from handlers.chat_handler import create_llm_instance
        # Create LLM instance (disable retries to return errors immediately)
        llm = create_llm_instance(provider, model_id, api_key=api_key, base_url=base_url, max_retries=0)
        
        # Test live invocation with tool binding verification
        from langchain_core.messages import HumanMessage
        from langchain_core.tools import tool
        
        @tool
        def ping_test_tool() -> str:
            """Internal verification tool."""
            return "pong"

        has_tool_support = True
        try:
            # Bind the ping test tool to the LLM to verify agent tools execution capability
            llm_to_test = llm.bind_tools([ping_test_tool])
            response = await llm_to_test.ainvoke([HumanMessage(content="Respond with: OK")])
        except Exception as tool_err:
            has_tool_support = False
            logger.warning(f"Model '{model_id}' ({provider}) tool binding ping failed ({tool_err}), testing basic completion...")
            # Fall back to testing basic text completion
            response = await llm.ainvoke([HumanMessage(content="Respond with: OK")])
            
        text_out = getattr(response, "content", str(response)).strip()
        
        capability_msg = " (Supports Tool & RAG Execution)" if has_tool_support else " (Text Only - Limited Tool Support)"
        return {
            "status": "success",
            "message": f"Model '{model_id}' is active and responding cleanly!{capability_msg}",
            "response": text_out,
            "has_tool_support": has_tool_support
        }
    except Exception as e:
        logger.error(f"Error testing model {model_id} ({provider}): {e}")
        err_msg = str(e)
        # Parse API error statuses and translate to user-friendly notifications
        if "404" in err_msg or "not found" in err_msg.lower():
            if provider == "openrouter" and not api_key:
                err_msg = f"OpenRouter API Key required (HTTP 404). Please enter your OpenRouter API key in Provider Credentials & Keys tab to activate."
            else:
                err_msg = f"Model ID '{model_id}' not found on {provider} API (HTTP 404)."
        elif "402" in err_msg or "credits" in err_msg.lower() or "payment" in err_msg.lower():
            err_msg = f"Insufficient OpenRouter credits / account balance (HTTP 402). Please add credits to your OpenRouter account."
        elif "401" in err_msg or "unauthorized" in err_msg.lower() or "authentication header" in err_msg.lower() or "invalid api key" in err_msg.lower():
            err_msg = f"API Key required or invalid for {provider.capitalize()} (Please submit an API key in Credentials tab)."
        elif "429" in err_msg or "resource_exhausted" in err_msg.lower() or "quota" in err_msg.lower():
            return {
                "status": "warning",
                "message": f"Model '{model_id}' is valid & connected, but {provider.capitalize()} Rate Limit / Quota was reached (HTTP 429). Please retry shortly."
            }
        return {
            "status": "error",
            "message": f"Model Test Failed: {err_msg}"
        }
