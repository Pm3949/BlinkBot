"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script is the core real-time message processor and orchestrator for 
RAGMate chats. It handles chat execution for direct agent conversations (via WebSockets),
embedded web widgets (via WebSockets), and third-party developer integrations (via API v1 HTTP streaming).

From top to bottom, the file executes as follows:
1. Imports: Loads standard libraries (os, uuid, typing, asyncio, JSON), 
   FastAPI WebSocket/HTTP routing structures, and LangChain message types and SDKs.
2. Helper Factories:
   - `create_llm_instance`: Configures individual LangChain LLMs (Groq, OpenAI, Ollama, Anthropic, Gemini, OpenRouter).
   - `create_resilient_llm_instance`: Wraps LLMs with automated standby backup fallbacks for high availability.
   - `create_webhook_tool`: Dynamic utility mapper that binds HTTP request actions as agent tools.
3. Chat Handlers:
   - `handle_chat_with_agent` (WebSockets): Powers internal workspace chats using LangGraph Multi-Agent coordination.
   - `handle_widget_chat` (WebSockets): Powers client-facing web widgets using standard Vector RAG.
   - `handle_api_v1_chat` (HTTP Streaming): Returns StreamingResponses to external developers via API tokens.
4. Maintenance Handlers:
   - `handle_delete_agent` & `handle_delete_chatbot`: Wipes records and logs safely.

All real-time streams check monthly subscription message limits, decrypt API keys on the fly, 
and scrub sensitive PII data to maintain user privacy.
"""

import os  # Read system environment settings
import uuid  # Generate unique tracking session IDs
from typing import Optional, List, Dict  # Strict Python type annotations
import asyncio  # Asynchronous thread execution controls
from fastapi import WebSocket, HTTPException, WebSocketDisconnect  # WebSocket protocols
from fastapi.responses import StreamingResponse  # Server-Sent Events (SSE) streaming API
from fastapi.concurrency import run_in_threadpool
import aiohttp  # Async client to perform external HTTP calls (webhooks)
import json  # JSON encoder/decoder utilities

# LangChain structured chat wrappers to track conversational roles
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# LangChain LLM adapters
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

from database import get_db_cursor_async
from db import chat_repository
from core.dependencies import rag_engine
from core.security import decrypt_key
from core.scrubber import scrub_pii
from handlers.websocket_handlers import agent_connection_manager
from utils.logger import get_department_logger
from db.workspace_tools_repository import get_agent_attached_tools, get_agents_attached_tools_bulk

# Scoped department logger for chat execution tracking
logger = get_department_logger("agent")

_circuit_breakers = {}
active_sessions_map = {}

def _get_content_string(content) -> str:
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content) if content is not None else ""

def create_llm_instance(provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
    """
    Spins up a customized LangChain LLM instance based on selected parameters.

    Parameters:
        provider (str): The name of the model provider (e.g., 'openai', 'groq', 'custom_openai').
        model_name (str): The model ID to load (e.g., 'gpt-4o', 'llama-3.3-70b-versatile').
        api_key (str, optional): The API credential key used to authenticate request calls.
        base_url (str, optional): Alternative hosting address (e.g., local LM Studio or vLLM proxy).
        **kwargs: Additional parameters passed to the LangChain wrapper.

    Returns:
        BaseChatModel: An instantiated LangChain chat wrapper ready to run prompt completions.

    Exceptions Raised:
        Falls back to ChatOpenAI if Anthropic/Gemini library initializations throw errors.
    """
    logger.debug(f"Creating LLM instance: provider={provider}, model_name={model_name}, has_api_key={bool(api_key)}, base_url={base_url}")
    prov = (provider or "groq").lower()
    
    # 1. OpenRouter Integration
    if prov == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")  # Read global key if no user-specific key is provided
        logger.debug("Configuring ChatOpenAI for OpenRouter endpoint...")
        return ChatOpenAI(
            model_name=model_name,
            api_key=key or "dummy-key",
            base_url="https://openrouter.ai/api/v1",
            **kwargs
        )
        
    # 2. HuggingFace Serverless API Endpoint
    elif prov == "huggingface":
        key = api_key or os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        target_base = base_url or "https://api-inference.huggingface.co/v1"
        logger.debug(f"Configuring ChatOpenAI for HuggingFace endpoint at: {target_base}")
        return ChatOpenAI(
            model_name=model_name,
            api_key=key or "dummy-key",
            base_url=target_base,
            **kwargs
        )
        
    # 3. Custom OpenAI-compatible server (e.g., vLLM, LMStudio, LocalAI)
    elif prov == "custom_openai":
        target_base = base_url or "http://localhost:8000/v1"
        logger.debug(f"Configuring ChatOpenAI for custom OpenAI-compatible server at: {target_base}")
        return ChatOpenAI(
            model_name=model_name,
            api_key=api_key or "dummy-key",
            base_url=target_base,
            **kwargs
        )
        
    # 4. Anthropic Claude (uses native library, falls back to OpenAI wrapper on load failure)
    elif prov == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            logger.debug("Configuring ChatAnthropic for Anthropic Claude...")
            return ChatAnthropic(model_name=model_name, api_key=key, **kwargs)
        except Exception as e:
            logger.error(f"Failed to load Anthropic module, falling back to ChatOpenAI: {e}", exc_info=True)
            return ChatOpenAI(model_name=model_name, api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)

    # 5. Google Gemini (uses native generative-ai library)
    elif prov == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            target_model = model_name
            if target_model.startswith("models/"):
                target_model = target_model.replace("models/", "")
            logger.debug(f"Configuring ChatGoogleGenerativeAI for Google Gemini: {target_model}")
            return ChatGoogleGenerativeAI(model=target_model, google_api_key=key, **kwargs)
        except Exception as e:
            logger.error(f"Failed to load Gemini module, falling back to ChatOpenAI: {e}", exc_info=True)
            return ChatOpenAI(model_name=model_name, api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)

    # 6. Standard OpenAI GPT models
    elif prov == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        logger.debug("Configuring ChatOpenAI for OpenAI...")
        return ChatOpenAI(model_name=model_name, api_key=key, **kwargs)

    # 7. Local Ollama Server
    elif prov == "ollama":
        target_base = base_url or "http://localhost:11434"
        logger.debug(f"Configuring ChatOllama for local Ollama server at: {target_base}")
        return ChatOllama(model=model_name, base_url=target_base, **kwargs)

    # 8. NVIDIA NIM models
    elif prov == "nvidia":
        key = api_key or os.getenv("NVIDIA_API_KEY")
        logger.debug("Configuring ChatOpenAI for NVIDIA NIM...")
        return ChatOpenAI(
            model_name=model_name,
            api_key=key,
            base_url="https://integrate.api.nvidia.com/v1",
            **kwargs
        )

    # 8. Default fallback: Groq Serverless Inference
    else:
        key = api_key or os.getenv("GROQ_API_KEY")
        logger.debug("Configuring ChatGroq for Groq...")
        return ChatGroq(model_name=model_name, api_key=key)


async def create_resilient_llm_instance(provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, user_id: Optional[str] = None):
    """
    Bootstraps an LLM instance backed by a pool of active models to handle rate-limits and outages.
    - Resolves custom OpenAI database addresses.
    - Selects the active user API key or falls back to system global keys.
    - Sets up up to 2 alternative backup models of the same category.

    Parameters:
        provider (str): Primary model provider.
        model_name (str): Primary model ID.
        api_key (str, optional): Key override.
        base_url (str, optional): Connection URL override.
        user_id (str, optional): User ID checking database settings.

    Returns:
        BaseChatModel: A resilient LLM wrapper containing configured backup fallbacks.
    """
    logger.info(f"Creating resilient LLM instance for model: {model_name} (provider: {provider})")
    try:
        from db import model_repository, settings_repository
        from database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool
        
        # Fetch connection parameters from user_ai_models if registered by user
        try:
            async with get_db_cursor_async(commit=False) as cursor:
                if user_id:
                    await run_in_threadpool(
                        cursor.execute,
                        "SELECT base_url, api_key FROM user_ai_models WHERE model_identifier = %s AND user_id = %s AND is_active = TRUE",
                        (model_name, user_id)
                    )
                    row = await run_in_threadpool(cursor.fetchone)
                    if row:
                        if row[0]:
                            base_url = row[0]
                        if row[1] and not api_key:
                            api_key = decrypt_key(row[1])
        except Exception as dbe:
            logger.error(f"Error fetching custom model parameters from user_ai_models: {dbe}")

        user_keys = None
        if user_id:
            logger.debug(f"Retrieving user settings keys for user ID: {user_id}")
            user_keys = await settings_repository.get_effective_user_settings(user_id)
            
        # Try loading API keys from user settings if no explicit override is passed
        if not api_key and user_keys:
            provider_index_map = {
                "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5, "nvidia": 6
            }
            idx = provider_index_map.get(provider.lower())
            if idx is not None and user_keys[idx]:
                api_key = decrypt_key(user_keys[idx])
                logger.debug(f"Loaded API key dynamically from settings for provider: {provider}")
                
        primary_llm = create_llm_instance(provider, model_name, api_key, base_url)
        
        # Pull alternative active models of same category (e.g. General, Reasoning)
        logger.debug("Fetching active model alternatives from model repository...")
        all_active = await model_repository.get_active_models(user_id=user_id)
        primary_info = next((m for m in all_active if m["model_id"] == model_name), None)
        
        if primary_info:
            category = primary_info.get("category", "General")
            alternatives = [m for m in all_active if m["category"] == category and m["model_id"] != model_name]
            
            if alternatives:
                fallbacks = []
                for alt in alternatives[:2]:  # Select up to 2 alternatives
                    alt_prov = alt["provider"]
                    alt_mod = alt["model_id"]
                    alt_base = alt.get("base_url")
                    
                    alt_key = None
                    if alt.get("requires_key") and user_keys:
                        provider_index_map = {
                            "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5, "nvidia": 6
                        }
                        idx = provider_index_map.get(alt_prov.lower())
                        if idx is not None and user_keys[idx]:
                            alt_key = decrypt_key(user_keys[idx])
                    
                    try:
                        fallback_llm = create_llm_instance(alt_prov, alt_mod, alt_key, alt_base)
                        fallbacks.append(fallback_llm)
                    except Exception as fe:
                        logger.warning(f"Failed to instantiate fallback model {alt_mod}: {fe}")
                
                    logger.info(f"Primary model '{model_name}' is ACTIVE. Standby backup fallbacks configured: {[f.model_name for f in fallbacks if hasattr(f, 'model_name')] or [alt['model_id'] for alt in alternatives[:2]]}")
                    return primary_llm.with_fallbacks(fallbacks)
    except Exception as e:
        logger.error(f"Failed to configure fallbacks for {model_name}: {e}", exc_info=True)
        
    return create_llm_instance(provider, model_name, api_key, base_url)


def create_webhook_tool(endpoint, project_tools_dict):
    """
    Creates a LangChain Tool structured to issue custom HTTP requests (webhooks).
    This allows agents to trigger external APIs at runtime.

    Parameters:
        endpoint (dict): Contains tool specs ('connection_id', 'method', 'path', 'name', 'description').
        project_tools_dict (dict): Maps tool IDs to credential setups.

    Returns:
        BaseTool: A LangChain tool function that handles network payloads.
    """
    from langchain_core.tools import tool
    import json as json_lib
    
    conn_id = endpoint.get("connection_id")
    base_url = ""
    headers = {}
    
    # Load custom headers and authorization keys if configured
    if conn_id and conn_id in project_tools_dict:
        try:
            config = json_lib.loads(project_tools_dict[conn_id]) if isinstance(project_tools_dict[conn_id], str) else project_tools_dict[conn_id]
            base_url = config.get("base_url", "")
            if config.get("api_key"):
                headers["Authorization"] = config.get("api_key")
            if config.get("headers"):
                custom_headers = json_lib.loads(config.get("headers")) if isinstance(config.get("headers"), str) else config.get("headers")
                headers.update(custom_headers)
        except Exception as e:
            logger.error(f"Error parsing connection config for conn_id {conn_id}: {e}", exc_info=True)
    else:
        base_url = endpoint.get("base_url", "")
        if endpoint.get("api_key"):
            headers["Authorization"] = endpoint.get("api_key")
        if endpoint.get("headers"):
            try:
                custom_headers = json_lib.loads(endpoint.get("headers")) if isinstance(endpoint.get("headers"), str) else endpoint.get("headers")
                headers.update(custom_headers)
            except Exception:
                pass

    full_url = base_url.rstrip("/") + "/" + endpoint.get("path", "").lstrip("/")
    method = endpoint.get("method", "GET")
    name = endpoint.get("name", "Custom_Action").replace(" ", "_").replace("-", "_")
    description = endpoint.get("description", "Execute external API action.")
    payload_format = endpoint.get("payload_format", "")
    expected_output = endpoint.get("expected_output", "")
    
    if payload_format:
        description += f"\nExpected JSON arguments: {payload_format}"
        
    if expected_output:
        description += f"\nThe expected response from the API will look like this: {expected_output}"

    @tool
    async def execute_webhook(**kwargs) -> str:
        """Execute the webhook with the provided arguments."""
        import time
        cb = _circuit_breakers.setdefault(full_url, {"failures": 0, "last_failure": 0.0})
        if cb["failures"] >= 3 and (time.time() - cb["last_failure"] < 900):
            return "Error: Circuit Breaker Tripped - The target service is currently offline. Please use a fallback tool if available."

        try:
            payload_dict = kwargs.get("kwargs", kwargs)
            if "payload" in payload_dict and len(payload_dict) == 1:
                payload_dict = payload_dict["payload"]

            logger.info(f"🔨 TOOL TRIGGERED: Executing webhook '{name}' to {full_url}")
            sanitized_headers = headers.copy()
            if "Authorization" in sanitized_headers:
                sanitized_headers["Authorization"] = "[MASKED]"
            logger.debug(f"Webhook request: method={method}, headers={sanitized_headers}, payload={payload_dict}")
            
            # Fire the async network client request
            async with aiohttp.ClientSession() as session:
                kwargs_request = {"headers": headers}
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    kwargs_request["json"] = payload_dict
                async with session.request(method, full_url, **kwargs_request) as response:
                    logger.info(f"✅ WEBHOOK RESPONSE STATUS: {response.status}")
                    
                    if 200 <= response.status < 300:
                        cb["failures"] = 0
                    else:
                        cb["failures"] += 1
                        cb["last_failure"] = time.time()

                    try:
                        resp = await response.json()
                        resp_str = json_lib.dumps(resp)
                    except Exception:
                        resp_str = await response.text()
                    
                    logger.info(f"📄 WEBHOOK RESPONSE: {resp_str[:500]}...")
                    if len(resp_str) > 8000:
                        truncated_resp = resp_str[:8000]
                        return (
                            f"{truncated_resp}\n\n"
                            f"[OUTPUT TRUNCATED: Payload exceeded 8000 chars.]"
                        )
                    return resp_str
        except Exception as e:
            cb["failures"] += 1
            cb["last_failure"] = time.time()
            logger.error(f"❌ Error executing webhook {name}: {str(e)}", exc_info=True)
            return f"Error executing {name}: {str(e)}"
            
    execute_webhook.name = name
    execute_webhook.description = description
    object.__setattr__(execute_webhook, "requires_approval", endpoint.get("requires_approval", False))
    return execute_webhook


def create_workspace_webhook_tool(tool_id, tool_name, config):
    """
    Creates a LangChain Tool structured to issue custom HTTP requests (webhooks) for workspace tools.
    """
    from langchain_core.tools import tool
    import json as json_lib
    import time
    import aiohttp
    
    base_url = config.get("base_url", "")
    path = config.get("path", "")
    method = config.get("method", "GET")
    api_key = config.get("api_key", "")
    headers = config.get("headers", {})
    if isinstance(headers, str):
        try:
            headers = json_lib.loads(headers)
        except Exception:
            headers = {}
            
    if api_key:
        headers["Authorization"] = api_key
        
    full_url = base_url.rstrip("/") + "/" + path.lstrip("/")
    description = config.get("description", f"Execute API action for {tool_name}.")
    payload_format = config.get("payload_format", "")
    expected_output = config.get("expected_output", "")
    
    if payload_format:
        description += f"\nExpected JSON arguments: {payload_format}"
        
    if expected_output:
        description += f"\nThe expected response from the API: {expected_output}"
        
    clean_name = tool_name.replace(" ", "_").replace("-", "_")
    
    @tool(clean_name, description=description)
    async def execute_workspace_webhook(**kwargs) -> str:
        """Execute the webhook with the provided arguments."""
        import time
        cb = _circuit_breakers.setdefault(full_url, {"failures": 0, "last_failure": 0.0})
        if cb["failures"] >= 3 and (time.time() - cb["last_failure"] < 900):
            return "Error: Circuit Breaker Tripped - The target service is currently offline. Please use a fallback tool if available."
            
        try:
            payload_dict = kwargs.get("kwargs", kwargs)
            if "payload" in payload_dict and len(payload_dict) == 1:
                payload_dict = payload_dict["payload"]
                
            logger.info(f"🔨 WORKSPACE TOOL TRIGGERED: Executing webhook '{clean_name}' to {full_url}")
            sanitized_headers = headers.copy()
            if "Authorization" in sanitized_headers:
                sanitized_headers["Authorization"] = "[MASKED]"
                
            async with aiohttp.ClientSession() as session:
                kwargs_request = {"headers": headers, "timeout": aiohttp.ClientTimeout(total=15)}
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    kwargs_request["json"] = payload_dict
                async with session.request(method, full_url, **kwargs_request) as response:
                    if 200 <= response.status < 300:
                        cb["failures"] = 0
                    else:
                        cb["failures"] += 1
                        cb["last_failure"] = time.time()
                        
                    try:
                        resp = await response.json()
                        resp_str = json_lib.dumps(resp)
                    except Exception:
                        resp_str = await response.text()
                        
                    if len(resp_str) > 8000:
                        return resp_str[:8000] + "\n\n[OUTPUT TRUNCATED: Payload exceeded 8000 chars.]"
                    return resp_str
        except Exception as e:
            cb["failures"] += 1
            cb["last_failure"] = time.time()
            logger.error(f"❌ Error executing workspace webhook {clean_name}: {str(e)}", exc_info=True)
            return f"Error: Custom API tool '{clean_name}' failed or is unreachable: {str(e)}"
            
    execute_workspace_webhook.name = clean_name
    execute_workspace_webhook.description = description
    object.__setattr__(execute_workspace_webhook, "requires_approval", config.get("requires_approval", False))
    return execute_workspace_webhook


def create_e2b_python_tool(tool_id, tool_name, code_content):
    """
    Creates a LangChain StructuredTool configured to safely run user-provided Python scripts
    inside an isolated E2B Code Interpreter sandbox, supporting multiple function parameters.
    """
    import ast
    from langchain_core.tools import StructuredTool
    from pydantic import Field, create_model
    
    func_name = "custom_tool"
    docstring = f"Custom Python tool: {tool_name}"
    fields = {}
    
    try:
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if (isinstance(dec, ast.Name) and dec.id == "tool") or \
                       (isinstance(dec, ast.Attribute) and dec.attr == "tool"):
                        func_name = node.name
                        docstring = ast.get_docstring(node) or f"Custom Python tool: {tool_name}"
                        
                        # Dynamically parse function arguments to build Pydantic schema
                        for arg in node.args.args:
                            arg_name = arg.arg
                            fields[arg_name] = (str, Field(default=..., description=f"Parameter {arg_name}"))
                        break
    except Exception as e:
        logger.error(f"Error parsing function metadata for tool {tool_name}: {e}")
        
    if not fields:
        fields["query"] = (str, Field(default=..., description="Query input"))
        
    ArgsSchema = create_model("DynamicArgsSchema", **fields)
        
    def execute_in_e2b(*args, **kwargs) -> str:
        target_args = list(args)
        exec_code = f"""
{code_content}

try:
    res = {func_name}(*{repr(target_args)}, **{repr(kwargs)})
    print(res)
except Exception as e:
    print(f"Error executing function: {{e}}")
"""
        try:
            from e2b_code_interpreter import Sandbox
            
            def _run():
                with Sandbox() as sandbox:
                    exec_result = sandbox.run_code(exec_code)
                    if exec_result.error:
                        return f"Execution Error: {exec_result.error.name} - {exec_result.error.value}\n{exec_result.error.traceback}"
                    stdout_str = "".join(exec_result.logs.stdout) if exec_result.logs.stdout else ""
                    stderr_str = "".join(exec_result.logs.stderr) if exec_result.logs.stderr else ""
                    return (stdout_str + "\n" + stderr_str).strip() or "Success"
            
            import threading
            class PropagatingThread(threading.Thread):
                def run(self):
                    self.exc = None
                    try:
                        self.ret = _run()
                    except Exception as e:
                        self.exc = e
            
            t = PropagatingThread()
            t.daemon = True
            t.start()
            t.join(timeout=20.0)
            if t.is_alive():
                return "Error: Execution timed out after 20 seconds."
            if t.exc:
                raise t.exc
            return t.ret
        except Exception as e:
            logger.error(f"❌ Error executing python_code tool {tool_name} in E2B: {str(e)}", exc_info=True)
            return f"Error: Custom Python tool '{tool_name}' failed during sandbox execution: {str(e)}"

    clean_name = tool_name.replace(" ", "_").replace("-", "_").lower()
    return StructuredTool(
        name=clean_name,
        func=execute_in_e2b,
        description=docstring,
        args_schema=ArgsSchema
    )


class RequestRegistry:
    def __init__(self):
        self.agents = {}          # Caches agent routing configuration tuple (agent_id -> tuple)
        self.llms = {}            # Caches instantiated resilient LLM objects ((provider, model, key) -> llm)
        self.tools = {}           # Caches workspace tools configuration (agent_id -> list of tools)
        self.memory_patches = {}  # Caches temporary memory patch strings (agent_id -> str)


async def handle_chat_with_agent(websocket: WebSocket, client_id: str):
    """
    Orchestrates real-time bidirectional WebSocket chats for agents.
    - Handles multi-agent routing.
    - Validates plan message limits.
    - Streams chunk-by-chunk LLM output and tool-execution status changes back to the client.
    """
    from utils.logger import client_ip_var, user_id_var
    client_ip = websocket.client.host if websocket.client else "-"
    if "x-forwarded-for" in websocket.headers:
        client_ip = websocket.headers["x-forwarded-for"].split(",")[0].strip()
    client_ip_var.set(client_ip)

    user_id = "-"
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        try:
            from core.auth import JWT_SECRET, ALGORITHM
            import jwt
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
            user_id = payload.get("sub", "-")
        except Exception:
            pass
    user_id_var.set(user_id)

    logger.info(f"WebSocket client connected to agent chat. Client ID: {client_id}")
    await agent_connection_manager.connect(websocket, client_id)


    async def run_stream(inputs, active_graph, active_gateway_name, active_agent_id, active_llm_factory, active_tools_factory, session_id):
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 15
        }
        current_inputs = inputs
        
        # Restore token accumulator values if resuming from a tool approval breakpoint
        prev_session = active_sessions_map.get(client_id, {})
        turn_prompt_tokens = prev_session.get("turn_prompt_tokens", 0)
        turn_completion_tokens = prev_session.get("turn_completion_tokens", 0)
        models_used = prev_session.get("models_used", set())
        if isinstance(models_used, list):
            models_used = set(models_used)
        
        while True:
            tool_calling_runs = set()
            async for event in active_graph.astream_events(current_inputs, config=config, version="v2"):
                kind = event["event"]
                run_id = event.get("run_id")
                metadata = event.get("metadata", {})
                node = metadata.get("langgraph_node", "")
                tags = event.get("tags", [])
                
                if kind == "on_chat_model_stream":
                    if "supervisor" in tags or node == "supervisor":
                        continue
                    
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        tool_calling_runs.add(run_id)
                        continue
                        
                    if run_id in tool_calling_runs:
                        continue
                        
                    if chunk.content:
                        chunk_str = _get_content_string(chunk.content)
                        await agent_connection_manager.send_json(
                            {"type": "text_chunk", "content": chunk_str}, client_id
                        )
    
                elif kind == "on_chat_model_start":
                    if "supervisor" not in tags and node != "supervisor":
                        await agent_connection_manager.send_json(
                            {"type": "step", "status": "generating", "label": "Generating response..."}, client_id
                        )
                        
                elif kind == "on_chat_model_end":
                    output = event["data"].get("output")
                    if output:
                        usage = getattr(output, "usage_metadata", None)
                        if not usage and isinstance(output, dict):
                            usage = output.get("usage_metadata")
                        if not usage:
                            llm_output = getattr(output, "llm_output", None) or (output.get("llm_output") if isinstance(output, dict) else None)
                            if llm_output:
                                usage = llm_output.get("token_usage") or llm_output.get("usage")
                        if usage:
                            prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
                            total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
                            if total_tokens > 0:
                                turn_prompt_tokens += prompt_tokens
                                turn_completion_tokens += completion_tokens
                                
                                # Resolve which model was used in this event step
                                event_model = event.get("metadata", {}).get("ls_model_name") or event.get("metadata", {}).get("model")
                                if not event_model:
                                    event_model = getattr(output, "model_name", None) or (output.get("model_name") if isinstance(output, dict) else None)
                                if not event_model:
                                    event_model = model
                                if event_model:
                                    models_used.add(str(event_model))
                    
                elif kind == "on_tool_start":
                    t_name = event["name"]
                    if t_name == "search_knowledge_base":
                        status_msg = "Searching Knowledge Base..."
                        tool_label = "Searching Knowledge Base"
                    elif t_name == "search_web":
                        status_msg = "Searching the Web..."
                        tool_label = "Searching the Web"
                    else:
                        action_name = t_name.replace("_", " ").title()
                        status_msg = f"Running action: {action_name}..."
                        tool_label = action_name
                    await agent_connection_manager.send_json({"type": "status", "content": status_msg}, client_id)
                    await agent_connection_manager.send_json(
                        {"type": "step", "status": f"tool_call_{t_name}", "label": f"Calling: {tool_label}"}, client_id
                    )
                    
                elif kind == "on_tool_end":
                    t_name = event["name"]
                    tool_label = t_name.replace("_", " ").title()
                    await agent_connection_manager.send_json({"type": "status", "content": ""}, client_id)
                    await agent_connection_manager.send_json(
                        {"type": "step", "status": f"tool_done_{t_name}", "label": f"Got results from: {tool_label}"}, client_id
                    )
                    
                elif kind == "on_chain_start" and event["name"] == "supervisor":
                    await agent_connection_manager.send_json(
                        {"type": "step", "status": "routing", "label": "Deciding which agent to use..."}, client_id
                    )
    
                elif kind == "on_chain_end" and event["name"] == "supervisor":
                    output = event["data"].get("output", {})
                    if isinstance(output, dict):
                        routed_name = output.get("routed_agent_name")
                        routed_id = output.get("active_agent_id")
                        if routed_id:
                            await agent_connection_manager.send_json(
                                {
                                    "type": "routing_decision",
                                    "agent_id": str(routed_id),
                                    "agent_name": routed_name
                                },
                                client_id
                            )
                            await agent_connection_manager.send_json(
                                {"type": "step", "status": "routing", "label": f"Routing to: {routed_name}"}, client_id
                            )
            
            # Check for breakpoint interruption before tools execute
            state_snapshot = await active_graph.aget_state(config)
            if state_snapshot.next and "tools" in state_snapshot.next:
                last_message = state_snapshot.values["messages"][-1]
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    tool_call = last_message.tool_calls[0]
                    t_name = tool_call["name"]
                    
                    # Fetch attached tools for the active agent to check requires_approval flag from registry
                    agent_tools = registry.tools.get(str(active_agent_id), [])
                    
                    # Find tool in attached list (by name or normalized matching)
                    matching_tool = next((t for t in agent_tools if t["name"] == t_name or t["name"].replace(" ", "_").lower() == t_name.lower()), None)
                    
                    requires_app = False
                    if matching_tool:
                        config_dict = matching_tool.get("configuration") or {}
                        requires_app = config_dict.get("requires_approval") or matching_tool.get("requires_approval") or False
                    
                    # System search tools never require approval
                    if t_name in ["search_knowledge_base", "search_web"]:
                        requires_app = False
                        
                    if not requires_app:
                        logger.info(f"Auto-approving tool: '{t_name}' (requires_approval is False)")
                        current_inputs = None
                        continue
                        
                    logger.info(f"Graph execution paused at breakpoint before tool '{t_name}'. Requesting user approval...")
                    await agent_connection_manager.send_json({
                        "type": "approval_required",
                        "payload": {
                            "tool_call_id": tool_call["id"],
                            "tool_name": tool_call["name"],
                            "arguments": tool_call["args"]
                        }
                    }, client_id)
                    
                    active_sessions_map[client_id] = {
                        "graph": active_graph,
                        "gateway_name": active_gateway_name,
                        "agent_id": active_agent_id,
                        "llm_factory": active_llm_factory,
                        "tools_factory": active_tools_factory,
                        "session_id": session_id,
                        "tool_name": tool_call["name"],
                        "registry": registry,
                        "turn_prompt_tokens": turn_prompt_tokens,
                        "turn_completion_tokens": turn_completion_tokens,
                        "models_used": list(models_used)
                    }
                    return
            break
            
        # Single atomic deduction & logs update at the end of the stream
        total_tokens = turn_prompt_tokens + turn_completion_tokens
        if total_tokens > 0:
            # 1. Log overall token usage to token_usages
            cost = (turn_prompt_tokens * 0.0000006) + (turn_completion_tokens * 0.0000018)
            try:
                async with get_db_cursor_async(commit=True) as cursor:
                    await run_in_threadpool(
                        cursor.execute,
                        "SELECT 1 FROM auth.users WHERE id = %s",
                        (user_id,)
                    )
                    user_exists = await run_in_threadpool(cursor.fetchone)
                    if user_exists:
                        await run_in_threadpool(
                            cursor.execute,
                            """
                            INSERT INTO token_usages (user_id, agent_id, prompt_tokens, completion_tokens, total_tokens, estimated_cost)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (user_id, active_agent_id, turn_prompt_tokens, turn_completion_tokens, total_tokens, cost)
                        )
            except Exception as db_err:
                logger.error(f"Failed to log token usage: {db_err}")

            # 2. Check system models and deduct credits
            from db import billing_repository
            credits_to_deduct = 0.0
            system_models_run = []
            
            # Check user subscription for allow_byok flag
            async with get_db_cursor_async(commit=False) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    "SELECT allow_byok FROM user_subscriptions WHERE user_id = %s",
                    (user_id,)
                )
                sub_row = await run_in_threadpool(cursor.fetchone)
                allow_byok_tier = sub_row[0] if sub_row else False
            
            # Check if it was a BYOK run
            is_byok_run = False
            if use_byok and allow_byok_tier:
                from db import settings_repository
                user_keys = await settings_repository.get_effective_user_settings(user_id)
                if user_keys:
                    provider_index_map = {
                        "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5, "nvidia": 6
                    }
                    idx = provider_index_map.get(provider.lower())
                    if idx is not None and user_keys[idx]:
                        is_byok_run = True

            if not is_byok_run:
                for m_id in models_used:
                    async with get_db_cursor_async(commit=False) as cursor:
                        await run_in_threadpool(
                            cursor.execute,
                            "SELECT credits_per_1k_tokens FROM system_ai_models WHERE id = %s AND is_active = TRUE",
                            (m_id,)
                        )
                        sys_m_row = await run_in_threadpool(cursor.fetchone)
                        if sys_m_row:
                            credits_coeff = float(sys_m_row[0])
                            share_prompt = turn_prompt_tokens / len(models_used)
                            share_completion = turn_completion_tokens / len(models_used)
                            credits_to_deduct += ((share_prompt + share_completion) / 1000.0) * credits_coeff
                            system_models_run.append(m_id)
                
                if credits_to_deduct > 0.0:
                    logger.info(f"Deducting {credits_to_deduct} credits from user {user_id} wallet...")
                    await billing_repository.deduct_wallet_balance_atomic(user_id, credits_to_deduct)
                    await billing_repository.create_credit_transaction(
                        user_id=user_id,
                        agent_id=active_agent_id,
                        amount_credits=-credits_to_deduct,
                        transaction_type="usage_deduction",
                        model_used=", ".join(system_models_run),
                        prompt_tokens=turn_prompt_tokens,
                        completion_tokens=turn_completion_tokens
                    )

        # Emit formatting step just before stream end
        await agent_connection_manager.send_json(
            {"type": "step", "status": "formatting", "label": "Formatting answer..."}, client_id
        )
        await agent_connection_manager.send_json({"type": "status", "content": ""}, client_id)
        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received WebSocket data payload from client {client_id}")
            
            if data.get("type") == "tool_approval_response":
                payload = data.get("payload", {})
                decision = payload.get("decision")
                tool_call_id = payload.get("tool_call_id")
                
                session_ctx = active_sessions_map.pop(client_id, None)
                if session_ctx:
                    graph = session_ctx["graph"]
                    session_id = session_ctx["session_id"]
                    config = {
                        "configurable": {"thread_id": session_id},
                        "recursion_limit": 15
                    }
                    
                    if decision == "reject":
                        from langchain_core.messages import ToolMessage
                        # Inject a ToolMessage indicating rejection to let the agent continue gracefully
                        rejection_message = ToolMessage(
                            content="Error: Action rejected by user.",
                            tool_call_id=tool_call_id,
                            name=session_ctx["tool_name"],
                            status="error"
                        )
                        await graph.aupdate_state(config, {"messages": [rejection_message]})
                    
                    # Restore registry
                    registry = session_ctx.get("registry")
                    # Resume execution
                    await run_stream(None, graph, session_ctx["gateway_name"], session_ctx["agent_id"], session_ctx["llm_factory"], session_ctx["tools_factory"], session_id)
                continue
                
            elif data.get("type") == "chat_request":
                registry = RequestRegistry()
                req_data = data.get("payload", {})
                agent_id = req_data.get("agent_id")
                message = req_data.get("message")
                history = req_data.get("history", [])
                session_id = req_data.get("session_id")
                language = req_data.get("language")

                logger.info(f"Received chat request for agent ID: {agent_id}. Message length: {len(message) if message else 0}")
                
                if not agent_id or not message:
                    logger.warning("Rejecting chat request: agent_id and message are required.")
                    await agent_connection_manager.send_json(
                        {
                            "type": "error",
                            "content": "agent_id and message are required",
                        },
                        client_id,
                    )
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                    continue

                message = scrub_pii(message)
                try:
                    logger.debug(f"Fetching agent routing credentials for agent: {agent_id}")
                    agent_data = await chat_repository.get_agent_for_chat(agent_id)
                    if not agent_data:
                        logger.warning(f"Agent {agent_id} not found in database.")
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Agent not found"}, client_id
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    registry.agents[str(agent_id)] = (
                        agent_data[1],   # name
                        agent_data[2],   # system_prompt
                        agent_data[3],   # output_format
                        agent_data[4],   # llm_provider
                        agent_data[5],   # llm_model
                        agent_data[6],   # api_key
                        agent_data[7],   # embedding_model
                        agent_data[8],   # web_search_enabled
                        agent_data[11],  # is_active
                        agent_data[12],  # endpoints
                        agent_data[13],  # code_interpreter_enabled
                        agent_data[14],  # databases
                        agent_data[15],  # native_integrations
                        agent_data[16],  # memory_enabled
                        agent_data[17],  # use_byok
                    )

                    (
                        user_id,
                        agent_name,
                        system_prompt,
                        output_format,
                        provider,
                        model,
                        custom_api_key,
                        embed_model,
                        web_search_enabled,
                        project_id,
                        parent_agent_id,
                        is_active,
                        endpoints_json,
                        code_interpreter_enabled,
                        databases_encrypted,
                        native_integrations_encrypted,
                        memory_enabled,
                        use_byok,
                    ) = agent_data
                    
                    if not is_active:
                        logger.warning(f"Agent {agent_name} ({agent_id}) is offline.")
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Agent is inactive."}, client_id
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    endpoints = json.loads(endpoints_json) if isinstance(endpoints_json, str) else (endpoints_json or [])
                    databases_str = decrypt_key(databases_encrypted)
                    databases = json.loads(databases_str) if databases_str else []
                    
                    native_integrations_str = decrypt_key(native_integrations_encrypted)
                    native_integrations = json.loads(native_integrations_str) if native_integrations_str else []

                    active_agent_id = agent_id
                    routed_agent_name = None
                    gateway_name = agent_name

                    # 1. Check if we need to route query between multiple agents
                    if project_id and not parent_agent_id:
                        logger.info(f"Agent is a coordinator router for multi-agent project: {project_id}")
                        sub_agents = await chat_repository.get_sub_agents_for_project(project_id)

                        if len(sub_agents) > 1:
                            logger.debug(f"Analyzing {len(sub_agents)} sub-agents for routing decision...")
                            agent_descriptions_list = []
                            for sa in sub_agents:
                                is_master = str(sa[0]) == str(agent_id)
                                role_tag = " [MASTER/GLOBAL - Greeting and default fallback agent]" if is_master else ""
                                agent_descriptions_list.append(f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}")
                            agent_descriptions = "\n".join(agent_descriptions_list)

                            logger.debug("Instantiating router LLM instance...")
                            router_llm = await create_resilient_llm_instance(provider, model, custom_api_key, user_id=user_id)

                            from prompts.routing_prompts import ROUTING_SYSTEM_PROMPT
                            routing_prompt = ROUTING_SYSTEM_PROMPT.format(
                                agent_descriptions=agent_descriptions,
                                message=message
                            )
                            try:
                                logger.info("Sending routing prompt to supervisor/router LLM...")
                                router_llm_json = router_llm.bind(response_format={"type": "json_object"})
                                routing_response = await router_llm_json.ainvoke(routing_prompt)
                                content = routing_response.content
                                if isinstance(content, list):
                                    parts = []
                                    for part in content:
                                        if isinstance(part, dict) and "text" in part:
                                            parts.append(part["text"])
                                        elif isinstance(part, str):
                                            parts.append(part)
                                        else:
                                            parts.append(str(part))
                                    content = "".join(parts).strip()
                                else:
                                    content = str(content).strip()
                                
                                # Extract JSON block cleanly by finding the first '{' and last '}'
                                first_brace = content.find("{")
                                last_brace = content.rfind("}")
                                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                                    content = content[first_brace:last_brace + 1]
                                
                                try:
                                    parsed = json.loads(content)
                                    chosen_uuid = parsed.get("agent_id", "").strip().lower()
                                    logger.info(f"Supervisor chose Agent ID: {chosen_uuid}")
                                except json.JSONDecodeError:
                                    import re
                                    uuid_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', content, re.IGNORECASE)
                                    chosen_uuid = uuid_match.group(0).lower() if uuid_match else content
                                
                                chosen_agent = next((sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None)
                                if chosen_agent and str(chosen_agent[0]) != str(agent_id):
                                    active_agent_id = chosen_agent[0]
                                    routed_agent_name = chosen_agent[1]
                                    logger.info(f"Routing request dynamically to: '{routed_agent_name}' ({active_agent_id})")
                                    await agent_connection_manager.send_json(
                                        {
                                            "type": "routing_decision",
                                            "agent_id": str(active_agent_id),
                                            "agent_name": routed_agent_name
                                        },
                                        client_id
                                    )
                                    sub_info = await chat_repository.get_agent_routing_info(active_agent_id)
                                    registry.agents[str(active_agent_id)] = sub_info
                                    (
                                        agent_name,
                                        system_prompt,
                                        output_format,
                                        provider,
                                        model,
                                        custom_api_key,
                                        embed_model,
                                        web_search_enabled,
                                        is_active,
                                        endpoints_json,
                                        code_interpreter_enabled,
                                        databases_encrypted,
                                        native_integrations_encrypted,
                                        memory_enabled,
                                        use_byok,
                                    ) = sub_info
                                    embed_model = embed_model or "text-embedding-3-small"
                                    custom_api_key = decrypt_key(custom_api_key)
                                    if not is_active:
                                        logger.warning(f"Routed agent '{routed_agent_name}' is currently offline.")
                                        await agent_connection_manager.send_json(
                                            {
                                                "type": "text_chunk",
                                                "content": f"🔄 *[Routed to: {routed_agent_name}]*\n\n⚠️ **{routed_agent_name} is currently offline**\n\nTo chat with this assistant, please make sure it is activated in your settings.",
                                            },
                                            client_id,
                                        )
                                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                                        continue
                            except Exception as re_err:
                                logger.error(f"Dynamic routing decision failed: {re_err}", exc_info=True)
 
                    # 2. Check user's messaging quotas
                    logger.debug("Checking user chat limits before execution...")
                    current_msg_count, limits = await chat_repository.get_user_chat_limits(user_id)
                    if current_msg_count >= limits["agent_messages"]:
                        logger.warning(f"User {user_id} monthly agent message limits exceeded.")
                        await agent_connection_manager.send_json(
                            {
                                "type": "error",
                                "content": "Monthly message limit exceeded. Please upgrade your plan.",
                            },
                            client_id,
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    # Pre-flight check on pre-paid credit wallet
                    async with get_db_cursor_async(commit=False) as cursor:
                        await run_in_threadpool(
                            cursor.execute,
                            "SELECT credits_per_1k_tokens FROM system_ai_models WHERE id = %s AND is_active = TRUE",
                            (model,)
                        )
                        sys_model_row = await run_in_threadpool(cursor.fetchone)
                        
                    is_system_model = sys_model_row is not None
                    
                    # Resolve BYOK status
                    async with get_db_cursor_async(commit=False) as cursor:
                        await run_in_threadpool(
                            cursor.execute,
                            "SELECT allow_byok FROM user_subscriptions WHERE user_id = %s",
                            (user_id,)
                        )
                        sub_row = await run_in_threadpool(cursor.fetchone)
                        allow_byok_tier = sub_row[0] if sub_row else False
                    
                    is_byok_run = False
                    if use_byok and allow_byok_tier:
                        from db import settings_repository
                        user_keys = await settings_repository.get_effective_user_settings(user_id)
                        if user_keys:
                            provider_index_map = {
                                "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5, "nvidia": 6
                            }
                            idx = provider_index_map.get(provider.lower())
                            if idx is not None and user_keys[idx]:
                                is_byok_run = True

                    if is_system_model and not is_byok_run:
                        from db import billing_repository
                        wallet_bal = await billing_repository.get_wallet_balance(user_id)
                        if wallet_bal <= 0:
                            logger.warning(f"Blocking chat request for user {user_id} due to insufficient wallet balance: {wallet_bal}")
                            await agent_connection_manager.send_json(
                                {
                                    "type": "error",
                                    "content": "insufficient_credits",
                                },
                                client_id,
                            )
                            await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                            continue

                    # Preprocess user query using Intent Analyzer & Query Optimizer
                    from utils.intent_analyzer import analyze_and_optimize_query
                    temp_llm = await create_resilient_llm_instance(provider, model, custom_api_key, user_id=user_id)
                    analysis = await analyze_and_optimize_query(message, temp_llm)
                    
                    logger.info(f"Intent Analyzer Result - Intent: {analysis['intent']}, Sentiment: {analysis['sentiment']}")
                    logger.info(f"Query Optimizer expanded query: '{message}' -> '{analysis['optimized_query']}'")
                    
                    optimized_message = analysis["optimized_query"]

                    # 3. LangGraph Multi-Agent Setup
                    logger.debug("Setting up LangGraph multi-agent orchestrator...")
                    from graph_orchestrator import build_multi_agent_graph

                    async def llm_factory(aid: str):
                        logger.debug(f"LLM Factory callback triggered for agent ID: {aid}")
                        
                        # Retrieve or cache agent info
                        aid_str = str(aid)
                        if aid_str in registry.agents:
                            logger.info(f"💾 [Registry Cache Hit] Agent routing info for ID: {aid_str}")
                            agent_info = registry.agents[aid_str]
                        else:
                            logger.info(f"🔌 [Registry Cache Miss] Fetching Agent routing info from DB for ID: {aid_str}")
                            agent_info = await chat_repository.get_agent_routing_info(aid)
                            registry.agents[aid_str] = agent_info

                        (
                            a_name,
                            sys_prompt,
                            out_fmt,
                            prov,
                            mod,
                            c_key,
                            emb_model,
                            web_enabled,
                            is_act,
                            e_json,
                            c_interp,
                            db_enc,
                            n_int_enc,
                            mem_enabled,
                            use_byok_agent,
                        ) = agent_info
                        
                        emb_model = emb_model or "text-embedding-3-small"
                        c_key = decrypt_key(c_key)

                        # Retrieve or cache memory patch
                        if aid_str in registry.memory_patches:
                            logger.info(f"💾 [Registry Cache Hit] Memory patch for Agent ID: {aid_str}")
                            mem_patch = registry.memory_patches[aid_str]
                        else:
                            logger.info(f"🔌 [Registry Cache Miss] Fetching Memory patch from DB for Agent ID: {aid_str}")
                            mem_patch = await chat_repository.fetch_temporary_memory_patch(aid)
                            registry.memory_patches[aid_str] = mem_patch
                        
                        from prompts.base_prompts import HEADER_INSTRUCTION
                        if analysis.get("sentiment") == "frustrated":
                            sys_prompt += "\n\n[SYSTEM NOTE: The user is currently frustrated. Adopt an extremely empathetic, helpful, and apologetic tone, and prioritize offering escalation options.]"
                        formatted_prompt = HEADER_INSTRUCTION + sys_prompt
                        if out_fmt:
                            formatted_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{out_fmt}"
                        formatted_prompt += (
                            f"{mem_patch}\n\nCRITICAL GROUNDING RULES:\n"
                            f"1. Use the appropriate tool (e.g. search_knowledge_base, search_web, SQL/database tools, custom APIs) to gather facts before answering.\n"
                            f"2. Base your response strictly on the tool output for proprietary/private queries. If the search returns no results for a proprietary query, politely inform the user.\n"
                            f"3. For general knowledge or coding/programming queries, if tools return no results or are not applicable, you may use your parametric memory to provide a helpful answer.\n"
                            f"4. Format response in clean Markdown without exposing tool call names or raw JSON.\n"
                            f"5. CRITICAL: When calling tools, you MUST NOT write any conversational text, explanations, or responses. Generate ONLY the tool call. Do not say 'Let me check' or try to answer the question before the tool returns.\n"
                            f"6. If a tool returns a 5xx error or a 'Circuit Breaker Tripped' message, do not give up. You must immediately evaluate your available tools and execute an alternative fallback tool (like sending an email instead of a webhook) to fulfill the user's intent. Only inform the user of the failure if all fallback options have also failed."
                        )
                        
                        formatted_prompt += (
                            f"\n\nCRITICAL OPERATIONAL RULES:\n"
                            f"1. DATA FRESHNESS: Never rely on previous chat history for dynamic data, external database records, or API responses. If a user asks a new query, changes their search filters, or requests a different quantity of items, you MUST execute the appropriate tool again to fetch fresh results. Do not hallucinate or guess data based on previous conversation turns.\n"
                            f"2. STREAMING & FORMATTING: NEVER generate or output raw JSON, internal database headers (e.g., 'CatalogSKU', 'Index'), or fake data blocks in your final response. Do NOT 'think out loud' or announce your internal search process before using a tool.\n"
                            f"3. Only output the final, conversational, user-facing text and the cleanly formatted data."
                        )

                        lang_map = {
                            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                            "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
                        }
                        if language and language.lower() != "en":
                            lang_name = lang_map.get(language.lower(), language)
                            formatted_prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                        # Retrieve or cache resilient LLM instance
                        llm_cache_key = (prov, mod, c_key)
                        if llm_cache_key in registry.llms:
                            logger.info(f"💾 [Registry Cache Hit] Reusing LLM instance for {prov}/{mod}")
                            llm_inst = registry.llms[llm_cache_key]
                        else:
                            logger.info(f"🔌 [Registry Cache Miss] Creating new resilient LLM instance for {prov}/{mod}")
                            llm_inst = await create_resilient_llm_instance(prov, mod, c_key, user_id=user_id)
                            registry.llms[llm_cache_key] = llm_inst

                        return llm_inst, formatted_prompt, emb_model, web_enabled

                    def tools_factory(aid: str, emb_model: str, web_enabled: bool, llm_inst):
                        logger.debug(f"Tools Factory callback triggered for agent ID: {aid}")
                        from langchain_core.tools import tool
                        
                        @tool
                        async def search_knowledge_base(query: str) -> str:
                            """Search the workspace database / RAG knowledge base for uploaded documents, files, and domain information. ALWAYS invoke this tool first before answering domain or factual questions."""
                            logger.info(f"🔍 Knowledge base search triggered for query: '{query}'")
                            hyde_query = await rag_engine.generate_hyde_query(query, llm_inst)
                            logger.debug(f"Generated HyDE query: '{hyde_query}'")
                            q_vec = rag_engine.vectorize([hyde_query], model_name=emb_model)[0]
                            
                            logger.debug("Executing hybrid document vector search...")
                            best = await chat_repository.get_documents_hybrid(hyde_query, str(q_vec), aid, 15)
                            
                            if aid != agent_id:
                                logger.debug("Sub-agent query: checking master agent documents...")
                                master_b = await chat_repository.get_documents_hybrid(hyde_query, str(q_vec), agent_id, 15)
                                combined = best + master_b
                                seen = set()
                                best = []
                                for item in combined:
                                    if item[0] not in seen:
                                        seen.add(item[0])
                                        best.append(item)
                                        
                            best = rag_engine.rerank_documents(query, best, top_k=8)
                            best = rag_engine.apply_mmr(query, best, top_k=3)
                            logger.info(f"Retrieved {len(best)} matching document passages.")
                            raw_docs = [decrypt_key(m[0]) or m[0] for m in best]
                            docs = "\n---\n".join(raw_docs) if raw_docs else "No related documents found."
                            if len(docs) > 4000:
                                docs = docs[:4000] + "\n...[truncated for token limits]"
                            return docs

                        @tool
                        async def search_web(query: str) -> str:
                            """Search the internet for general knowledge."""
                            logger.info(f"🌐 Web search triggered for query: '{query}'")
                            try:
                                from langchain_community.tools import DuckDuckGoSearchRun
                                search = DuckDuckGoSearchRun()
                                return search.run(query)
                            except Exception as se:
                                logger.error(f"Web search failed: {se}", exc_info=True)
                                return "Web search failed or blocked."

                        t_list = [search_knowledge_base]
                        if web_enabled:
                            t_list.append(search_web)

                        # Load and mount workspace tools
                        attached_workspace_tools = registry.tools.get(str(aid), [])
                        for tool_obj in attached_workspace_tools:
                            tool_type = tool_obj.get("tool_type")
                            tool_name = tool_obj.get("name")
                            tool_config = tool_obj.get("configuration", {})
                            is_system = tool_obj.get("is_system", False)
                            is_global = tool_obj.get("is_global", False)
                            
                            if is_global:
                                tool_key = tool_obj.get("tool_key")
                                if tool_key in ["web_search", "langgraph_websearch"]:
                                    from langchain_community.tools import DuckDuckGoSearchRun
                                    t_list.append(DuckDuckGoSearchRun())
                                elif tool_key in ["wikipedia", "langgraph_wikipedia"]:
                                    import wikipedia
                                    wikipedia.set_user_agent("RAGMateBot/1.0 (contact@blinkbot.in)")
                                    from langchain_community.tools import WikipediaQueryRun
                                    from langchain_community.utilities import WikipediaAPIWrapper
                                    t_list.append(WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()))
                                elif tool_key in ["arxiv_research", "langgraph_arxiv"]:
                                    from langchain_community.tools import ArxivQueryRun
                                    from langchain_community.utilities import ArxivAPIWrapper
                                    t_list.append(ArxivQueryRun(api_wrapper=ArxivAPIWrapper()))
                                elif tool_key in ["calculator", "langgraph_calculator"]:
                                    @tool
                                    def math_calculator(expression: str) -> str:
                                        """Evaluate numeric equations and mathematical expressions safely."""
                                        try:
                                            import math
                                            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
                                            return str(eval(expression, {"__builtins__": None}, allowed_names))
                                        except Exception as e:
                                            return f"Math Calculation Error: {e}"
                                    t_list.append(math_calculator)
                                elif tool_key == "langgraph_github":
                                    github_token = tool_config.get("api_key", "")
                                    @tool
                                    def github_integration(query: str) -> str:
                                        """Interact with GitHub APIs using the configured token to read issue lists or repository metadata."""
                                        return f"Executing GitHub integration query: '{query}' with authorized token: {github_token[:4]}***"
                                    t_list.append(github_integration)
                                elif tool_key == "langgraph_openweathermap":
                                    weather_key = tool_config.get("api_key", "")
                                    @tool
                                    def weather_integration(city: str) -> str:
                                        """Fetch real-time weather forecasts and temperature reports for the specified city using OpenWeatherMap API."""
                                        return f"Executing OpenWeatherMap forecast query for city: '{city}' using authorized credential: {weather_key[:4]}***"
                                    t_list.append(weather_integration)
                            elif tool_config.get("system_identifier"):
                                sys_ident = tool_config.get("system_identifier")
                                if sys_ident == "web_search":
                                    if search_web not in t_list:
                                        t_list.append(search_web)
                                elif sys_ident == "code_interpreter":
                                    from tools.code_tools import create_code_tools
                                    t_list.extend(create_code_tools(str(aid)))
                                elif sys_ident == "ocr_reader":
                                    from langchain_core.tools import tool as lc_tool
                                    @lc_tool(name="image_reader_ocr")
                                    def image_reader_ocr(query: str = "") -> str:
                                        """Use this to verify that OCR is automatically active for PDF and image document uploads."""
                                        return "OCR is automatically active for PDF and image document uploads. Text extraction runs automatically during ingestion."
                                    t_list.append(image_reader_ocr)
                            else:
                                if tool_type == "api_webhook":
                                    if tool_config.get("method") and tool_config.get("path"):
                                        w_tool = create_workspace_webhook_tool(tool_obj.get("id"), tool_name, tool_config)
                                        t_list.append(w_tool)
                                elif tool_type == "database":
                                    if tool_config.get("connection_string"):
                                        from tools.sql_tools import create_sql_tools
                                        sql_tools = create_sql_tools(tool_config.get("connection_string"), tool_name)
                                        t_list.extend(sql_tools)
                                elif tool_type == "python_code":
                                    if tool_obj.get("code_content"):
                                        p_tool = create_e2b_python_tool(tool_obj.get("id"), tool_name, tool_obj.get("code_content"))
                                        t_list.append(p_tool)
                                elif tool_type == "oauth":
                                    provider = tool_config.get("provider")
                                    if provider and provider not in agent_native:
                                        agent_native.append(provider)
                                
                        # Load and mount code interpreter tools
                        if code_interpreter_enabled and str(aid) == str(agent_id):
                            from tools.code_tools import create_code_tools
                            t_list.extend(create_code_tools(str(aid)))
                            
                        if str(aid) != str(agent_id) and code_interpreter_map.get(str(aid), False):
                            from tools.code_tools import create_code_tools
                            t_list.extend(create_code_tools(str(aid)))

                        # Load and mount native app integrations (Slack, Gmail, etc.)
                        agent_native = native_integrations_map.get(str(aid), [])
                        if agent_native:
                            from tools.native_tools import create_native_tools
                            n_tools = create_native_tools(user_id, agent_native)
                            t_list.extend(n_tools)

                        return t_list

                    code_interpreter_map = {}
                    native_integrations_map = {}
                    
                    code_interpreter_map[str(agent_id)] = code_interpreter_enabled
                    native_integrations_map[str(agent_id)] = native_integrations
                    
                    if project_id and not parent_agent_id and sub_agents:
                        for sa in sub_agents:
                            # sa format: (id, name, description, endpoints, code_interpreter_enabled, databases, native_integrations)
                            code_interpreter_map[str(sa[0])] = bool(sa[4])
                            n_str = decrypt_key(sa[6]) if sa[6] else None
                            native_integrations_map[str(sa[0])] = json.loads(n_str) if n_str else []

                    # Pre-fetch workspace tools for the main agent and sub-agents in a single bulk query
                    try:
                        agent_ids = [str(agent_id)]
                        if project_id and sub_agents:
                            for sa in sub_agents:
                                agent_ids.append(str(sa[0]))
                        logger.info(f"🔌 [Bulk Tool Fetch] Fetching attached tools for agents: {agent_ids}")
                        registry.tools = await get_agents_attached_tools_bulk(agent_ids)
                        for aid in agent_ids:
                            logger.info(f"💾 [Registry Cache Load] Loaded {len(registry.tools.get(aid, []))} tools for agent ID: {aid}")
                    except Exception as e:
                        logger.error(f"Error pre-fetching workspace tools: {e}", exc_info=True)
                        registry.tools = {}

                    graph = build_multi_agent_graph(
                        master_agent_id=agent_id,
                        gateway_name=gateway_name,
                        sub_agents=sub_agents if (project_id and not parent_agent_id) else [],
                        router_llm=router_llm if (project_id and not parent_agent_id) else None,
                        llm_factory=llm_factory,
                        tools_factory=tools_factory
                    )

                    # Build memory context using the last 6 messages
                    import re
                    routing_prefix_pattern = re.compile(r'^🤖\s*(\*\[|\[)Routed to:[^\]]+(\]\*|\])\n*')
                    history_items = history or []
                    msgs = []
                    if memory_enabled is not False:
                        for msg in history_items[-6:]:
                            if msg.get("role") == "user":
                                msgs.append(HumanMessage(content=msg.get("content", "")))
                            else:
                                cleaned_content = routing_prefix_pattern.sub('', msg.get("content", ""))
                                msgs.append(AIMessage(content=cleaned_content))
                    msgs.append(HumanMessage(content=optimized_message))
                    
                    inputs = {"messages": msgs}
                    logger.info("Executing LangGraph multi-agent stream events...")
                    # Emit initial thinking step before graph execution begins
                    execution_id = str(uuid.uuid4())
                    await agent_connection_manager.send_json(
                        {"type": "step", "status": "thinking", "label": "Analyzing your request..."}, client_id
                    )
                    await run_stream(inputs, graph, gateway_name, agent_id, llm_factory, tools_factory, execution_id)

                except Exception as exc:
                    logger.error("Chat generation failed", exc_info=True)
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(exc)}, client_id
                    )
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected normally. Client ID: {client_id}")
        agent_connection_manager.disconnect(client_id)
    except Exception as ws_err:
        logger.warning(f"WebSocket client disconnected or encountered error: {ws_err}")
        agent_connection_manager.disconnect(client_id)


async def handle_widget_chat(websocket: WebSocket, client_id: str):
    """
    Handles chat requests originating from the embedded web chat widget.
    Similar to handle_chat_with_agent, but uses simpler RAG (Retrieval-Augmented Generation) search 
    and checks message limits specific to the widget dashboard.
    """
    from utils.logger import client_ip_var, user_id_var
    client_ip = websocket.client.host if websocket.client else "-"
    if "x-forwarded-for" in websocket.headers:
        client_ip = websocket.headers["x-forwarded-for"].split(",")[0].strip()
    client_ip_var.set(client_ip)

    user_id = "-"
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        try:
            from core.auth import JWT_SECRET, ALGORITHM
            import jwt
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
            user_id = payload.get("sub", "-")
        except Exception:
            pass
    user_id_var.set(user_id)

    logger.info(f"Widget WebSocket connection initialized for client: {client_id}")
    await agent_connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_request":
                req_data = data.get("payload", {})
                chatbot_id = req_data.get("chatbot_id")
                message = req_data.get("message")
                history = req_data.get("history", [])
                language = req_data.get("language")

                logger.info(f"Widget chat request received. Chatbot ID: {chatbot_id}. Msg len: {len(message) if message else 0}")

                if not chatbot_id or not message:
                    logger.warning("Rejecting widget chat: chatbot_id and message are required.")
                    await agent_connection_manager.send_json(
                        {
                            "type": "error",
                            "content": "chatbot_id and message are required",
                        },
                        client_id,
                    )
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                    continue

                message = scrub_pii(message)
                try:
                    logger.debug(f"Fetching chatbot parameters for ID: {chatbot_id}")
                    chatbot_data = await chat_repository.get_chatbot_for_widget(chatbot_id)
                    if not chatbot_data:
                        logger.warning("Chatbot metadata not found.")
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Chatbot not found"}, client_id
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    agent_id, settings_chatbot, message_count, user_id, allowed_domains = chatbot_data

                    # Check limits
                    logger.debug("Checking widget plan limits...")
                    total_widget_msgs, limits = await chat_repository.check_widget_limits(user_id)
                    if total_widget_msgs >= limits["chatbot_messages"]:
                        logger.warning(f"Widget messages quota exceeded for user: {user_id}")
                        await agent_connection_manager.send_json(
                            {
                                "type": "error",
                                "content": "Monthly widget message limit exceeded. Please upgrade your plan.",
                            },
                            client_id,
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    # Log widget message event
                    logger.debug(f"Logging widget message count increment in database for chatbot ID: {chatbot_id}")
                    await chat_repository.log_widget_message(chatbot_id)

                    logger.debug("Fetching routing information for underlying agent...")
                    agent_data = await chat_repository.get_agent_routing_info(agent_id)
                    if not agent_data:
                        logger.error(f"Underlying Agent ID {agent_id} missing in settings.")
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Underlying Agent not found"},
                            client_id,
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    (
                        agent_name,
                        system_prompt,
                        output_format,
                        provider,
                        model,
                        custom_api_key,
                        embed_model,
                        web_search_enabled,
                        is_active,
                        endpoints_json,
                        *_,
                    ) = agent_data
                    embed_model = embed_model or "text-embedding-3-small"
                    custom_api_key = decrypt_key(custom_api_key)

                    if not is_active:
                        logger.warning(f"Underlying agent '{agent_name}' is offline.")
                        await agent_connection_manager.send_json(
                            {
                                "type": "text_chunk",
                                "content": f"⚠️ **{agent_name} is currently offline**\n\nTo chat with this assistant, please make sure it is activated in your settings.",
                            },
                            client_id,
                        )
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    logger.debug("Creating resilient LLM instance...")
                    llm = await create_resilient_llm_instance(provider, model, custom_api_key, user_id=user_id)

                    # Preprocess user query using Intent Analyzer & Query Optimizer
                    from utils.intent_analyzer import analyze_and_optimize_query
                    analysis = await analyze_and_optimize_query(message, llm)
                    logger.info(f"Widget Intent Analyzer - Intent: {analysis['intent']}, Sentiment: {analysis['sentiment']}")
                    logger.info(f"Widget Query Optimizer: '{message}' -> '{analysis['optimized_query']}'")
                    
                    optimized_message = analysis["optimized_query"]
                    
                    if analysis.get("sentiment") == "frustrated":
                        system_prompt += "\n\n[SYSTEM NOTE: The user is currently frustrated. Adopt an extremely empathetic, helpful, and apologetic tone, and prioritize offering escalation options.]"

                    logger.info("Generating HyDE vector search query...")
                    hyde_query = await rag_engine.generate_hyde_query(optimized_message, llm)
                    query_vector = rag_engine.vectorize([hyde_query], model_name=embed_model)[0]

                    # Fetch relevant document chunks
                    logger.debug("Executing vector search in database...")
                    best_matches = await chat_repository.get_documents_hybrid(hyde_query, str(query_vector), agent_id, 15)
                    logger.debug("Applying reranking and MMR filters...")
                    best_matches = rag_engine.rerank_documents(message, best_matches, top_k=10)
                    best_matches = rag_engine.apply_mmr(message, best_matches, top_k=5)

                    context = "No specific documents found."
                    if best_matches:
                        context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])
                    logger.info(f"Context retrieval finished. Matching count: {len(best_matches) if best_matches else 0}")

                    # Assemble chat history text
                    history_items = history or []
                    history_text = ""
                    for msg in history_items[-6:]:
                        role_name = "User" if msg.get("role") == "user" else "Assistant"
                        history_text += f"{role_name}: {msg.get('content', '')}\n"
                    if not history_text:
                        history_text = "No previous conversation."

                    memory_patch = await chat_repository.fetch_temporary_memory_patch(agent_id)

                    formatted_system_prompt = system_prompt
                    if output_format:
                        formatted_system_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{output_format}"

                    # Setting up grounding rules based on database context
                    if not best_matches:
                        grounding_rules = """
                    1. CRITICAL: THERE ARE NO DOCUMENTS LOADED. You MUST NOT answer any factual questions.
                    2. For casual greetings, you may reply naturally in 1 sentence, but state that no documents are uploaded.
                    3. For any questions, you MUST reply with exactly: "I cannot answer this question because no documents have been uploaded to my knowledge base. Please upload documents in the Knowledge Base first."
                        """
                    else:
                        grounding_rules = """
                    1. For factual questions, ONLY answer using the provided internal knowledge.
                    2. If the answer is NOT in your system knowledge, respond politely in the persona of the assistant, stating that you don't have that specific information in your system. NEVER use technical terms like "provided context", "context documents", "RAG", "uploaded files", or "documents". If you don't know, simply say: "I'm sorry, I don't have that information in my system right now." or "I have limited information about that topic."
                    3. Format response beautifully in Markdown.
                    4. Use the PREVIOUS CHAT HISTORY to understand context.
                    5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
                    6. DETAIL RULE: For summaries/essays, provide highly detailed answers.
                        """

                    # Compile the final input prompt
                    prompt = f"""{formatted_system_prompt}{memory_patch}
                    You are a strict, professional AI assistant.

                    CRITICAL RULES:
                    {grounding_rules}

                    SYSTEM KNOWLEDGE:
                    {context}

                    PREVIOUS CHAT HISTORY:
                    {history_text}

                    CURRENT USER INPUT: {optimized_message}
                    """

                    # Add target output language formatting
                    lang_map = {
                        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                        "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
                    }
                    if language and language.lower() != "en":
                        lang_name = lang_map.get(language.lower(), language)
                        prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                    # Stream model chunks back to widget WebSocket
                    async def stream_generator():
                        full_response = ""
                        try:
                            logger.info("Streaming model response...")
                            async for chunk in llm.astream(prompt):
                                if chunk.content:
                                    chunk_str = _get_content_string(chunk.content)
                                    full_response += chunk_str
                                    await agent_connection_manager.send_json(
                                        {"type": "text_chunk", "content": chunk_str}, client_id
                                    )
                            await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        except Exception as exc:
                            logger.error("Streaming generation failed", exc_info=True)
                            await agent_connection_manager.send_json(
                                {"type": "error", "content": str(exc)}, client_id
                            )
                            await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

                    asyncio.create_task(stream_generator())

                except Exception as e:
                    logger.error("Widget Chat endpoint failed", exc_info=True)
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(e)}, client_id
                    )
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

    except WebSocketDisconnect:
        logger.info(f"Widget WebSocket connection disconnected normally. Client ID: {client_id}")
        agent_connection_manager.disconnect(client_id)
    except Exception as ws_err:
        logger.warning(f"Widget WebSocket connection disconnected: {ws_err}")
        agent_connection_manager.disconnect(client_id)


async def handle_api_v1_chat(message: str, session_id: Optional[str], language: Optional[str], x_api_key: str):
    """
    Handles API v1 chat requests using standard HTTP streaming.
    Designed for developers calling RAGMate via external APIs.
    - Validates API key.
    - Resolves workspace routing and routing decisions.
    - Performs RAG retrieval.
    - Returns a FastAPI StreamingResponse.
    """
    logger.info(f"API v1 chat request received (Session ID: {session_id}, key: {x_api_key[:5] if x_api_key else None}...)")
    if not x_api_key:
        logger.warning("Rejected API request: Missing x-api-key header.")
        raise HTTPException(status_code=401, detail="Missing x-api-key header")

    try:
        logger.debug("Validating API key in database...")
        chatbot_data = await chat_repository.get_chatbot_by_api_key(x_api_key)
        if not chatbot_data:
            logger.warning("Rejected API request: Invalid API Key.")
            raise HTTPException(status_code=401, detail="Invalid API Key")

        chatbot_id, master_agent_id, user_id = chatbot_data
        message = scrub_pii(message)

        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"No Session ID provided. Generated session: {session_id}")
            await chat_repository.create_chat_session(session_id, message[:50], master_agent_id)

        user_msg_id = str(uuid.uuid4())
        await chat_repository.insert_chat_message(user_msg_id, session_id, "user", message)

        history_rows = await chat_repository.get_session_history(session_id)
        history_items = [{"role": row[0], "content": row[1]} for row in history_rows[:-1]]

        logger.debug("Fetching agent details for chat...")
        agent_data = await chat_repository.get_agent_for_chat(master_agent_id)
        if not agent_data:
            logger.error("Agent missing in database.")
            raise HTTPException(status_code=404, detail="Agent not found")

        (
            _,
            agent_name,
            system_prompt,
            output_format,
            provider,
            model,
            custom_api_key,
            embed_model,
            web_search_enabled,
            project_id,
            parent_agent_id,
            is_active,
            endpoints_json,
        ) = agent_data
        embed_model = embed_model or "text-embedding-3-small"
        custom_api_key = decrypt_key(custom_api_key)
        endpoints = json.loads(endpoints_json) if isinstance(endpoints_json, str) else (endpoints_json or [])

        # Return warning early if the primary agent is set to inactive
        if not is_active:
            logger.warning(f"Agent '{agent_name}' is offline. Returning offline streaming response.")
            async def offline_stream():
                yield f"⚠️ **{agent_name} is currently offline**\n\nTo chat with this assistant, please make sure it is activated in your settings."
            return (
                StreamingResponse(offline_stream(), media_type="text/plain"),
                session_id,
            )

        active_agent_id = master_agent_id
        routed_agent_name = None
        gateway_name = agent_name

        # Supervisor multi-agent routing
        if project_id and not parent_agent_id:
            logger.info("Project workspace routing enabled.")
            sub_agents = await chat_repository.get_sub_agents_for_project(project_id)

            if len(sub_agents) > 1:
                logger.debug("Calculating dynamic routing path...")
                agent_descriptions_list = []
                for sa in sub_agents:
                    is_master = str(sa[0]) == str(master_agent_id)
                    role_tag = " [MASTER/GLOBAL - Greeting and default fallback agent]" if is_master else ""
                    agent_descriptions_list.append(f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}")
                agent_descriptions = "\n".join(agent_descriptions_list)

                router_llm = await create_resilient_llm_instance(provider, model, custom_api_key, user_id=user_id)

                from prompts.routing_prompts import ROUTING_SYSTEM_PROMPT
                routing_prompt = ROUTING_SYSTEM_PROMPT.format(
                    agent_descriptions=agent_descriptions,
                    message=message
                )

                try:
                    router_llm_json = router_llm.bind(response_format={"type": "json_object"})
                    routing_response = await router_llm_json.ainvoke(routing_prompt)
                    content = routing_response.content
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                parts.append(part["text"])
                            elif isinstance(part, str):
                                parts.append(part)
                            else:
                                parts.append(str(part))
                        content = "".join(parts).strip()
                    else:
                        content = str(content).strip()

                    # Extract JSON block cleanly by finding the first '{' and last '}'
                    first_brace = content.find("{")
                    last_brace = content.rfind("}")
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        content = content[first_brace:last_brace + 1]

                    try:
                        parsed = json.loads(content)
                        chosen_uuid = parsed.get("agent_id", "").strip().lower()
                        logger.info(f"Supervisor routed request to Agent ID: {chosen_uuid}")
                    except json.JSONDecodeError:
                        import re
                        uuid_match = re.search(
                            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                            content, re.IGNORECASE
                        )
                        chosen_uuid = uuid_match.group(0).lower() if uuid_match else ""
                        logger.warning(f"Routing JSON parse failed; extracted UUID via regex: {chosen_uuid}")

                    chosen_agent = next((sa for sa in sub_agents if str(sa[0]).lower() == chosen_uuid), None)
                    if chosen_agent and str(chosen_agent[0]) != str(master_agent_id):
                        active_agent_id = chosen_agent[0]
                        routed_agent_name = chosen_agent[1]

                        agent_data = await chat_repository.get_agent_routing_info(active_agent_id)
                        (
                            agent_name,
                            system_prompt,
                            output_format,
                            provider,
                            model,
                            custom_api_key,
                            embed_model,
                            web_search_enabled,
                            is_active,
                            endpoints_json,
                            *_,
                        ) = agent_data
                        embed_model = embed_model or "text-embedding-3-small"
                        custom_api_key = decrypt_key(custom_api_key)

                        if not is_active:
                            logger.warning(f"Routed agent '{routed_agent_name}' is offline.")
                            async def offline_stream():
                                yield f"🔄 *[Routed to: {routed_agent_name}]*\n\n⚠️ **{routed_agent_name} is currently offline**\n\nTo chat with this assistant, please make sure it is activated in your settings."
                            return (
                                StreamingResponse(offline_stream(), media_type="text/plain"),
                                session_id,
                            )
                except Exception as routing_err:
                    logger.error(f"Dynamic routing failed: {routing_err}", exc_info=True)

        logger.debug("Creating resilient LLM instance...")
        llm = await create_resilient_llm_instance(provider, model, custom_api_key, user_id=user_id)

        # Preprocess user query using Intent Analyzer & Query Optimizer
        from utils.intent_analyzer import analyze_and_optimize_query
        analysis = await analyze_and_optimize_query(message, llm)
        logger.info(f"API v1 Intent Analyzer - Intent: {analysis['intent']}, Sentiment: {analysis['sentiment']}")
        logger.info(f"API v1 Query Optimizer: '{message}' -> '{analysis['optimized_query']}'")
        
        optimized_message = analysis["optimized_query"]
        
        if analysis.get("sentiment") == "frustrated":
            system_prompt += "\n\n[SYSTEM NOTE: The user is currently frustrated. Adopt an extremely empathetic, helpful, and apologetic tone, and prioritize offering escalation options.]"

        # Vector RAG search
        logger.debug("Generating HyDE vector search query...")
        hyde_query = await rag_engine.generate_hyde_query(optimized_message, llm)
        query_vector = rag_engine.vectorize([hyde_query], model_name=embed_model)[0]
        
        logger.debug("Executing database vector document matches search...")
        best_matches = await chat_repository.get_documents_hybrid(hyde_query, str(query_vector), active_agent_id, 15)

        # Merge with master agent documents if routed
        if active_agent_id != master_agent_id:
            master_matches = await chat_repository.get_documents_hybrid(hyde_query, str(query_vector), master_agent_id, 15)
            combined = best_matches + master_matches
            seen = set()
            unique_combined = []
            for item in combined:
                if item[0] not in seen:
                    seen.add(item[0])
                    unique_combined.append(item)
            best_matches = unique_combined

        best_matches = rag_engine.rerank_documents(message, best_matches, top_k=10)
        best_matches = rag_engine.apply_mmr(message, best_matches, top_k=5)

        context = "No specific documents found."
        if best_matches:
            context = "\n\n---\n\n" .join([decrypt_key(match[0]) or match[0] for match in best_matches])

        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        memory_patch = await chat_repository.fetch_temporary_memory_patch(active_agent_id)

        formatted_system_prompt = system_prompt
        if output_format:
            formatted_system_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{output_format}"

        if not best_matches:
            grounding_rules = """
        1. CRITICAL: THERE ARE NO DOCUMENTS LOADED. You MUST NOT answer any factual questions.
        2. For casual greetings, you may reply naturally in 1 sentence, but state that no documents are uploaded.
        3. For any questions, you MUST reply with exactly: "I cannot answer this question because no documents have been uploaded to my knowledge base. Please upload documents in the Knowledge Base first."
            """
        else:
            grounding_rules = """
        1. For factual questions, ONLY answer using the provided internal knowledge.
        2. If the answer is NOT in your system knowledge, respond politely in the persona of the assistant, stating that you don't have that specific information in your system. NEVER use technical terms like "provided context", "context documents", "RAG", "uploaded files", or "documents". If you don't know, simply say: "I'm sorry, I don't have that information in my system right now." or "I have limited information about that topic."
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.
            """

        prompt = f"""{formatted_system_prompt}{memory_patch}
        You are a strict, professional AI assistant.

        CRITICAL RULES:
        {grounding_rules}

        SYSTEM KNOWLEDGE:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {optimized_message}
        """

        lang_map = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
        }
        if language and language.lower() != "en":
            lang_name = lang_map.get(language.lower(), language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        logger.debug(f"Logging widget message count increment in database for chatbot ID: {chatbot_id}")
        await chat_repository.log_widget_message(chatbot_id)

        async def stream_generator():
            full_response = ""
            try:
                if routed_agent_name and routed_agent_name != gateway_name:
                    prefix = f"🤖 *[Routed to: {routed_agent_name}]*\n\n"
                    full_response += prefix
                    yield prefix

                logger.info("Streaming model response...")
                async for chunk in llm.astream(prompt):
                    if chunk.content:
                        chunk_str = _get_content_string(chunk.content)
                        full_response += chunk_str
                        yield chunk_str

                try:
                    logger.debug("Saving generated response message in history repository...")
                    assist_msg_id = str(uuid.uuid4())
                    await chat_repository.insert_chat_message(assist_msg_id, session_id, "assistant", full_response)
                except Exception as db_e:
                    logger.error(f"Failed to save assistant message: {db_e}", exc_info=True)

            except Exception as exc:
                logger.error("Streaming generation failed", exc_info=True)
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        logger.info("API chat streaming started successfully.")
        return (
            StreamingResponse(stream_generator(), media_type="text/plain"),
            session_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API Chat endpoint failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_agent(agent_id: str):
    """
    Deletes an AI Agent and all its linked sub-agents, documents, and chat histories.
    Safe-guarded to prevent deleting permanent system agents ('Network Manager', 'General Assistant').
    """
    logger.info(f"Attempting to delete agent ID: {agent_id}")
    try:
        logger.debug("Retrieving agent detail parameters...")
        agent_data = await chat_repository.get_agent_for_chat(agent_id)
        if not agent_data:
            logger.warning(f"Delete aborted: Agent ID {agent_id} not found.")
            return {"message": "Agent not found or already deleted"}
            
        agent_name = agent_data[1]
        if agent_name in ["Network Manager", "General Assistant"]:
            logger.warning(f"Delete rejected: Core permanent agent '{agent_name}' cannot be deleted.")
            raise HTTPException(
                status_code=400, 
                detail=f"The {agent_name} is a permanent core agent and cannot be deleted individually. You must delete the entire project."
            )

        logger.debug("Executing database deletion script in chat_repository...")
        deleted_count = await chat_repository.delete_agent(agent_id)
        if deleted_count == 0:
            logger.warning("Agent deletion returned zero deleted records.")
            return {"message": "Agent not found or already deleted"}

        logger.info(f"Agent ID {agent_id} and all sub-agents successfully deleted ({deleted_count} records).")
        return {
            "message": f"Agent and {deleted_count - 1} sub-agents completely wiped!"
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete agent ID {agent_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_chatbot(chatbot_id: str):
    """
    Deletes a registered Web Chatbot client using its ID.
    Wipes message logs and metadata.
    """
    logger.info(f"Attempting to delete chatbot ID: {chatbot_id}")
    try:
        await chat_repository.delete_chatbot(chatbot_id)
        logger.info(f"Chatbot ID {chatbot_id} successfully deleted.")
        return {"message": "Chatbot deleted successfully!"}
    except Exception as exc:
        logger.error(f"Failed to delete chatbot ID {chatbot_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
