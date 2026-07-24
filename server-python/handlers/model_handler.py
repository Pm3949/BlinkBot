import logging
import aiohttp
from fastapi import HTTPException
from db import model_repository

from utils.logger import get_department_logger

logger = get_department_logger("system")

async def handle_get_active_models():
    """Returns active models grouped by provider for frontend dropdowns."""
    try:
        models = await model_repository.get_active_models()
        grouped = {}
        for m in models:
            prov = m["provider"]
            if prov not in grouped:
                grouped[prov] = []
            grouped[prov].append(m)
        return {"providers": grouped, "models": models}
    except Exception as e:
        logger.error(f"Error fetching active models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_get_all_models():
    """Returns all models for admin management."""
    try:
        models = await model_repository.get_all_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching all models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_create_model(payload: dict):
    """Creates a new model entry in the database."""
    try:
        if not payload.get("name") or not payload.get("model_id") or not payload.get("provider"):
            raise HTTPException(status_code=400, detail="name, model_id, and provider are required")
        
        model = await model_repository.create_model(payload)
        return {"status": "success", "model": model}
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_update_model(model_id: str, payload: dict):
    """Updates an existing model entry."""
    try:
        updated = await model_repository.update_model(model_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"status": "success", "model": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_delete_model(model_id: str):
    """Deletes a model entry."""
    try:
        count = await model_repository.delete_model(model_id)
        if count == 0:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"status": "success", "message": "Model deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_test_provider_key(provider: str, api_key: str, base_url: str = None):
    """Tests connectivity to a provider API key or custom server endpoint."""
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")

    try:
        async with aiohttp.ClientSession() as session:
            if provider == "openai":
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "OpenAI API Key is valid!"}
                    return {"status": "error", "message": f"OpenAI authentication failed (HTTP {resp.status})"}

            elif provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "Groq API Key is valid!"}
                    return {"status": "error", "message": f"Groq authentication failed (HTTP {resp.status})"}

            elif provider == "openrouter":
                url = "https://openrouter.ai/api/v1/auth/key"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "OpenRouter API Key is valid!"}
                    return {"status": "error", "message": f"OpenRouter authentication failed (HTTP {resp.status})"}

            elif provider == "huggingface":
                url = "https://huggingface.co/api/whoami-v2"
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return {"status": "connected", "message": "HuggingFace Token is valid!"}
                    return {"status": "error", "message": f"HuggingFace authentication failed (HTTP {resp.status})"}

            elif provider == "ollama":
                target_url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
                async with session.get(target_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get("models", [])
                        model_names = [m.get("name") for m in models if m.get("name")]

                        # Auto-seed synced models into database
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
                                pass # Already exists

                        count_str = f" Synced {len(model_names)} local models: {', '.join(model_names)}" if model_names else ""
                        return {"status": "connected", "message": f"Ollama server is reachable!{count_str}"}
                    return {"status": "error", "message": f"Ollama connection failed (HTTP {resp.status})"}

            elif provider == "anthropic":
                # Anthropic API test ping
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {"model": "claude-3-5-sonnet-20241022", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}
                async with session.post(url, headers=headers, json=payload, timeout=10) as resp:
                    if resp.status in [200, 400]: # 400 may occur for quota/token format but key is authed
                        return {"status": "connected", "message": "Anthropic API Key is valid!"}
                    return {"status": "error", "message": f"Anthropic authentication failed (HTTP {resp.status})"}

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
    """Tests if a specific AI model can be invoked and returns live response."""
    provider = payload.get("provider")
    model_id = payload.get("model_id")
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")

    if not provider or not model_id:
        raise HTTPException(status_code=400, detail="provider and model_id are required")

    # Fetch user's saved provider key if not explicitly passed
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
            llm_to_test = llm.bind_tools([ping_test_tool])
            response = await llm_to_test.ainvoke([HumanMessage(content="Respond with: OK")])
        except Exception as tool_err:
            has_tool_support = False
            logger.warning(f"Model '{model_id}' ({provider}) tool binding ping failed ({tool_err}), testing basic completion...")
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
