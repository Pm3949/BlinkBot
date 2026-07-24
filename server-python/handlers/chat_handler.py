import os
import uuid
from typing import Optional, List, Dict
import asyncio
from fastapi import WebSocket, HTTPException, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import aiohttp
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

from db import chat_repository
from core.dependencies import rag_engine
from core.security import decrypt_key
from core.scrubber import scrub_pii
from handlers.websocket_handlers import agent_connection_manager

from utils.logger import get_department_logger

logger = get_department_logger("agent")

def create_llm_instance(provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
    logger.debug(f"Creating LLM instance: provider={provider}, model_name={model_name}, has_api_key={bool(api_key)}, base_url={base_url}")
    prov = (provider or "groq").lower()
    
    # 1. OpenRouter
    if prov == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        logger.debug("Configuring ChatOpenAI for OpenRouter endpoint...")
        return ChatOpenAI(
            model_name=model_name,
            api_key=key or "dummy-key",
            base_url="https://openrouter.ai/api/v1",
            **kwargs
        )
        
    # 2. HuggingFace Serverless Inference / Endpoints
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
        
    # 3. Custom OpenAI-compatible server (vLLM, LMStudio, LocalAI)
    elif prov == "custom_openai":
        target_base = base_url or "http://localhost:8000/v1"
        logger.debug(f"Configuring ChatOpenAI for custom OpenAI-compatible server at: {target_base}")
        return ChatOpenAI(
            model_name=model_name,
            api_key=api_key or "dummy-key",
            base_url=target_base,
            **kwargs
        )
        
    # 4. Anthropic Claude
    elif prov == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            logger.debug("Configuring ChatAnthropic for Anthropic Claude...")
            return ChatAnthropic(model_name=model_name, api_key=key, **kwargs)
        except Exception as e:
            logger.error(f"Failed to load Anthropic module, falling back to ChatOpenAI: {e}", exc_info=True)
            return ChatOpenAI(model_name=model_name, api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)

    # 5. Google Gemini
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

    # 6. OpenAI
    elif prov == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        logger.debug("Configuring ChatOpenAI for OpenAI...")
        return ChatOpenAI(model_name=model_name, api_key=key, **kwargs)

    # 7. Ollama
    elif prov == "ollama":
        target_base = base_url or "http://localhost:11434"
        logger.debug(f"Configuring ChatOllama for local Ollama server at: {target_base}")
        return ChatOllama(model=model_name, base_url=target_base, **kwargs)

    # 8. Default: Groq
    else:
        key = api_key or os.getenv("GROQ_API_KEY")
        logger.debug("Configuring ChatGroq for Groq...")
        return ChatGroq(model_name=model_name, api_key=key)

async def create_resilient_llm_instance(provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, user_id: Optional[str] = None):
    logger.info(f"Creating resilient LLM instance for model: {model_name} (provider: {provider})")
    try:
        from db import model_repository, settings_repository
        from database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool
        
        # If it is custom_openai, retrieve its registered endpoint URL and encrypted key
        if provider.lower() == "custom_openai" and not base_url:
            try:
                async with get_db_cursor_async(commit=False) as cursor:
                    await run_in_threadpool(
                        cursor.execute,
                        "SELECT base_url, api_key FROM ai_models WHERE model_id = %s AND (user_id IS NULL OR user_id = %s)",
                        (model_name, user_id)
                    )
                    row = await run_in_threadpool(cursor.fetchone)
                    if row:
                        if row[0]:
                            base_url = row[0]
                        if row[1] and not api_key:
                            api_key = decrypt_key(row[1])
            except Exception as dbe:
                logger.error(f"Error fetching custom model parameters: {dbe}")

        user_keys = None
        if user_id:
            logger.debug(f"Retrieving user settings keys for user ID: {user_id}")
            user_keys = await settings_repository.get_effective_user_settings(user_id)
            
        # If no explicit api_key passed, try loading from user/shared keys
        if not api_key and user_keys:
            provider_index_map = {
                "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5
            }
            idx = provider_index_map.get(provider.lower())
            if idx is not None and user_keys[idx]:
                api_key = decrypt_key(user_keys[idx])
                logger.debug(f"Loaded API key dynamically from settings for provider: {provider}")
                
        primary_llm = create_llm_instance(provider, model_name, api_key, base_url)
        
        logger.debug("Fetching active model alternatives from model repository...")
        all_active = await model_repository.get_active_models(user_id=user_id)
        primary_info = next((m for m in all_active if m["model_id"] == model_name), None)
        
        if primary_info:
            category = primary_info.get("category", "General")
            alternatives = [m for m in all_active if m["category"] == category and m["model_id"] != model_name]
            
            if alternatives:
                fallbacks = []
                for alt in alternatives[:2]:
                    alt_prov = alt["provider"]
                    alt_mod = alt["model_id"]
                    alt_base = alt.get("base_url")
                    
                    alt_key = None
                    if alt.get("requires_key") and user_keys:
                        provider_index_map = {
                            "openai": 0, "groq": 1, "gemini": 2, "openrouter": 3, "anthropic": 4, "huggingface": 5
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
    from langchain_core.tools import tool
    import json as json_lib
    
    conn_id = endpoint.get("connection_id")
    base_url = ""
    headers = {}
    
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
        try:
            payload_dict = kwargs.get("kwargs", kwargs)
            if "payload" in payload_dict and len(payload_dict) == 1:
                payload_dict = payload_dict["payload"]

            logger.info(f"🔨 TOOL TRIGGERED: Executing webhook '{name}' to {full_url}")
            # Sanitize authorization headers in debug log
            sanitized_headers = headers.copy()
            if "Authorization" in sanitized_headers:
                sanitized_headers["Authorization"] = "[MASKED]"
            logger.debug(f"Webhook request: method={method}, headers={sanitized_headers}, payload={payload_dict}")
            
            async with aiohttp.ClientSession() as session:
                kwargs_request = {"headers": headers}
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    kwargs_request["json"] = payload_dict
                async with session.request(method, full_url, **kwargs_request) as response:
                    logger.info(f"✅ WEBHOOK RESPONSE STATUS: {response.status}")
                    try:
                        resp = await response.json()
                        logger.info(f"📄 WEBHOOK RESPONSE JSON: {json_lib.dumps(resp)}")
                        return json_lib.dumps(resp)
                    except Exception:
                        text_resp = await response.text()
                        logger.info(f"📄 WEBHOOK RESPONSE TEXT: {text_resp}")
                        return text_resp
        except Exception as e:
            logger.error(f"❌ Error executing webhook {name}: {str(e)}", exc_info=True)
            return f"Error executing {name}: {str(e)}"
            
    execute_webhook.name = name
    execute_webhook.description = description
    return execute_webhook


async def handle_chat_with_agent(websocket: WebSocket, client_id: str):
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
    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received WebSocket data payload from client {client_id}")
            
            if data.get("type") == "chat_request":
                req_data = data.get("payload", {})
                agent_id = req_data.get("agent_id")
                message = req_data.get("message")
                history = req_data.get("history", [])
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
                        continue

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
                    ) = agent_data
                    
                    if not is_active:
                        logger.warning(f"Agent {agent_name} ({agent_id}) is offline.")
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Agent is inactive."}, client_id
                        )
                        continue

                    endpoints = json.loads(endpoints_json) if isinstance(endpoints_json, str) else (endpoints_json or [])
                    databases_str = decrypt_key(databases_encrypted)
                    databases = json.loads(databases_str) if databases_str else []
                    
                    native_integrations_str = decrypt_key(native_integrations_encrypted)
                    native_integrations = json.loads(native_integrations_str) if native_integrations_str else []

                    from prompts import get_system_prompt
                    system_prompt = get_system_prompt({
                        "system_prompt": system_prompt,
                        "api_endpoints": endpoints,
                        "native_integrations": native_integrations,
                        "db_connections": databases,
                        "enable_code_interpreter": code_interpreter_enabled
                    })

                    active_agent_id = agent_id
                    routed_agent_name = None
                    gateway_name = agent_name

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
                                routing_response = router_llm_json.invoke(routing_prompt)
                                content = routing_response.content.strip()
                                
                                if content.startswith("```json"):
                                    content = content[7:]
                                if content.endswith("```"):
                                    content = content[:-3]
                                content = content.strip()
                                
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
                                        native_integrations_encrypted
                                    ) = await chat_repository.get_agent_routing_info(active_agent_id)
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
                        continue

                    # LangGraph Multi-Agent Setup
                    logger.debug("Setting up LangGraph multi-agent orchestrator...")
                    from graph_orchestrator import build_multi_agent_graph

                    async def llm_factory(aid: str):
                        logger.debug(f"LLM Factory callback triggered for agent ID: {aid}")
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
                            n_int_enc
                        ) = await chat_repository.get_agent_routing_info(aid)
                        
                        emb_model = emb_model or "text-embedding-3-small"
                        c_key = decrypt_key(c_key)
                        mem_patch = await chat_repository.fetch_temporary_memory_patch(aid)
                        
                        header_instruction = (
                            "SYSTEM MANDATE: You possess access to workspace database search tools (search_knowledge_base).\n"
                            "FOR ANY DOMAIN, TECHNICAL, DOCUMENT, OR KNOWLEDGE QUERY, YOU MUST CALL search_knowledge_base FIRST BEFORE ANSWERING.\n"
                            "DO NOT ANSWER FROM GENERAL MEMORY WITHOUT CALLING search_knowledge_base FIRST.\n\n"
                        )
                        formatted_prompt = header_instruction + sys_prompt
                        if out_fmt:
                            formatted_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{out_fmt}"
                        formatted_prompt += (
                            f"{mem_patch}\n\nCRITICAL GROUNDING RULES:\n"
                            f"1. ALWAYS EXECUTE search_knowledge_base FIRST for any factual/domain request.\n"
                            f"2. Base your response strictly on the search_knowledge_base output. If search_knowledge_base returns 'No related documents found', reply: 'I searched the workspace knowledge base database, but no relevant information was found.'\n"
                            f"3. Do NOT invent facts or answer ungrounded questions from parametric memory when database tools are present.\n"
                            f"4. Format response in clean Markdown without exposing tool call names or raw JSON."
                        )
                        
                        lang_map = {
                            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                            "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
                        }
                        if language and language.lower() != "en":
                            lang_name = lang_map.get(language.lower(), language)
                            formatted_prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                        llm_inst = await create_resilient_llm_instance(prov, mod, c_key, user_id=user_id)
                        return llm_inst, formatted_prompt, emb_model, web_enabled

                    def tools_factory(aid: str, emb_model: str, web_enabled: bool, llm_inst):
                        logger.debug(f"Tools Factory callback triggered for agent ID: {aid}")
                        from langchain_core.tools import tool
                        
                        @tool
                        async def search_knowledge_base(query: str) -> str:
                            """Search the workspace database / RAG knowledge base for uploaded documents, files, and domain information. ALWAYS invoke this tool first before answering domain or factual questions."""
                            logger.info(f"🔍 Knowledge base search triggered for query: '{query}'")
                            hyde_query = rag_engine.generate_hyde_query(query, llm_inst)
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
                            
                        agent_endpoints = endpoints_map.get(str(aid), [])
                        for ep in agent_endpoints:
                            if ep.get("method") and ep.get("path"):
                                webhook_tool = create_webhook_tool(ep, project_tools_dict)
                                t_list.append(webhook_tool)
                                
                        agent_dbs = databases_map.get(str(aid), [])
                        for db in agent_dbs:
                            if db.get("connection_string") and db.get("name"):
                                from tools.sql_tools import create_sql_tools
                                sql_tools = create_sql_tools(db.get("connection_string"), db.get("name"))
                                t_list.extend(sql_tools)
                                
                        if code_interpreter_enabled and str(aid) == str(agent_id):
                            from tools.code_tools import create_code_tools
                            t_list.extend(create_code_tools())
                            
                        if str(aid) != str(agent_id) and code_interpreter_map.get(str(aid), False):
                            from tools.code_tools import create_code_tools
                            t_list.extend(create_code_tools())

                        agent_native = native_integrations_map.get(str(aid), [])
                        if agent_native:
                            from tools.native_tools import create_native_tools
                            n_tools = create_native_tools(user_id, agent_native)
                            t_list.extend(n_tools)

                        return t_list

                    project_tools_dict = {}
                    endpoints_map = {}
                    databases_map = {}
                    code_interpreter_map = {}
                    native_integrations_map = {}
                    
                    endpoints_map[str(agent_id)] = endpoints
                    databases_map[str(agent_id)] = databases
                    code_interpreter_map[str(agent_id)] = code_interpreter_enabled
                    native_integrations_map[str(agent_id)] = native_integrations
                    
                    if project_id:
                        from db.agent_repository import get_project_tools
                        p_tools = await get_project_tools(project_id)
                        project_tools_dict = {str(t[0]): t[2] for t in p_tools}
                        
                    if project_id and not parent_agent_id and sub_agents:
                        for sa in sub_agents:
                            try:
                                endpoints_map[str(sa[0])] = json.loads(sa[3]) if isinstance(sa[3], str) else (sa[3] or [])
                            except Exception:
                                endpoints_map[str(sa[0])] = []
                            try:
                                db_str = decrypt_key(sa[5])
                                databases_map[str(sa[0])] = json.loads(db_str) if db_str else []
                            except Exception:
                                databases_map[str(sa[0])] = []
                            try:
                                code_interpreter_map[str(sa[0])] = bool(sa[4])
                            except Exception:
                                code_interpreter_map[str(sa[0])] = False
                            try:
                                n_str = decrypt_key(sa[6]) if len(sa) > 6 else None
                                native_integrations_map[str(sa[0])] = json.loads(n_str) if n_str else []
                            except Exception:
                                native_integrations_map[str(sa[0])] = []

                    graph = build_multi_agent_graph(
                        master_agent_id=agent_id,
                        gateway_name=gateway_name,
                        sub_agents=sub_agents if (project_id and not parent_agent_id) else [],
                        router_llm=router_llm if (project_id and not parent_agent_id) else None,
                        llm_factory=llm_factory,
                        tools_factory=tools_factory
                    )

                    history_items = history or []
                    msgs = []
                    for msg in history_items[-6:]:
                        if msg.get("role") == "user":
                            msgs.append(HumanMessage(content=msg.get("content", "")))
                        else:
                            msgs.append(AIMessage(content=msg.get("content", "")))
                    msgs.append(HumanMessage(content=message))
                    
                    inputs = {"messages": msgs}
                    logger.info("Executing LangGraph multi-agent stream events...")
                    
                    async for event in graph.astream_events(inputs, version="v2"):
                        kind = event["event"]
                        
                        if kind == "on_chat_model_stream":
                            chunk = event["data"]["chunk"]
                            if chunk.content:
                                await agent_connection_manager.send_json(
                                    {"type": "text_chunk", "content": chunk.content}, client_id
                                )
                                
                        elif kind == "on_tool_start":
                            t_name = event["name"]
                            status_msg = "Searching Knowledge Base..." if t_name == "search_knowledge_base" else "Searching the Web..."
                            await agent_connection_manager.send_json({"type": "status", "content": status_msg}, client_id)
                            
                        elif kind == "on_tool_end":
                            await agent_connection_manager.send_json({"type": "status", "content": ""}, client_id)
                            
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
                                if routed_name and routed_name != gateway_name:
                                    await agent_connection_manager.send_json(
                                        {"type": "text_chunk", "content": f"🤖 *[Routed to: {routed_name}]*\n\n"}, client_id
                                    )

                    await agent_connection_manager.send_json({"type": "status", "content": ""}, client_id)
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                    logger.info("LangGraph streaming generation complete.")

                except Exception as exc:
                    logger.error("Chat generation failed", exc_info=True)
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(exc)}, client_id
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected normally. Client ID: {client_id}")
        agent_connection_manager.disconnect(client_id)
    except Exception as ws_err:
        logger.warning(f"WebSocket client disconnected or encountered error: {ws_err}")
        agent_connection_manager.disconnect(client_id)


async def handle_widget_chat(websocket: WebSocket, client_id: str):
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
                        continue

                    agent_id, settings_chatbot, message_count, user_id, allowed_domains = chatbot_data

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
                        continue

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

                    logger.info("Generating HyDE vector search query...")
                    hyde_query = rag_engine.generate_hyde_query(message, llm)
                    query_vector = rag_engine.vectorize([hyde_query], model_name=embed_model)[0]

                    logger.debug("Executing vector search in database...")
                    best_matches = await chat_repository.get_documents_hybrid(hyde_query, str(query_vector), agent_id, 15)
                    logger.debug("Applying reranking and MMR filters...")
                    best_matches = rag_engine.rerank_documents(message, best_matches, top_k=10)
                    best_matches = rag_engine.apply_mmr(message, best_matches, top_k=5)

                    context = "No specific documents found."
                    if best_matches:
                        context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])
                    logger.info(f"Context retrieval finished. Matching count: {len(best_matches) if best_matches else 0}")

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

                    if not best_matches:
                        grounding_rules = """
                    1. CRITICAL: THERE ARE NO DOCUMENTS LOADED. You MUST NOT answer any factual questions.
                    2. For casual greetings, you may reply naturally in 1 sentence, but state that no documents are uploaded.
                    3. For any questions, you MUST reply with exactly: "I cannot answer this question because no documents have been uploaded to my knowledge base. Please upload documents in the Knowledge Base first."
                        """
                    else:
                        grounding_rules = """
                    1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
                    2. If the answer is NOT in the context, DO NOT use general knowledge. Politely inform the user that you can only answer questions based on the uploaded documents.
                    3. Format response beautifully in Markdown.
                    4. Use the PREVIOUS CHAT HISTORY to understand context.
                    5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
                    6. DETAIL RULE: For summaries/essays, provide highly detailed answers.
                        """

                    prompt = f"""{formatted_system_prompt}{memory_patch}
                    You are a strict, professional AI assistant grounded ONLY in the provided documents.

                    CRITICAL RULES:
                    {grounding_rules}

                    CONTEXT DOCUMENTS:
                    {context}

                    PREVIOUS CHAT HISTORY:
                    {history_text}

                    CURRENT USER INPUT: {message}
                    """

                    lang_map = {
                        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                        "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
                    }
                    if language and language.lower() != "en":
                        lang_name = lang_map.get(language.lower(), language)
                        prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                    logger.info("Initiating model response stream...")
                    for chunk in llm.stream(prompt):
                        if chunk.content:
                            await agent_connection_manager.send_json(
                                {"type": "text_chunk", "content": chunk.content},
                                client_id,
                            )

                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                    logger.info("Widget stream generation complete.")

                except Exception as e:
                    logger.error("Widget Chat endpoint failed", exc_info=True)
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(e)}, client_id
                    )

    except WebSocketDisconnect:
        logger.info(f"Widget WebSocket connection disconnected normally. Client ID: {client_id}")
        agent_connection_manager.disconnect(client_id)
    except Exception as ws_err:
        logger.warning(f"Widget WebSocket connection disconnected: {ws_err}")
        agent_connection_manager.disconnect(client_id)


async def handle_api_v1_chat(message: str, session_id: Optional[str], language: Optional[str], x_api_key: str):
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
                    routing_response = router_llm_json.invoke(routing_prompt)
                    content = routing_response.content.strip()

                    # Strip any stray markdown fences the model might add
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

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

        logger.debug("Generating HyDE vector search query...")
        hyde_query = rag_engine.generate_hyde_query(message, llm)
        query_vector = rag_engine.vectorize([hyde_query], model_name=embed_model)[0]
        
        logger.debug("Executing database vector document matches search...")
        best_matches = await chat_repository.get_documents_hybrid(hyde_query, str(query_vector), active_agent_id, 15)

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
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Politely inform the user that you can only answer questions based on the uploaded documents.
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.
            """

        prompt = f"""{formatted_system_prompt}{memory_patch}
        You are a strict, professional AI assistant grounded ONLY in the provided documents.

        CRITICAL RULES:
        {grounding_rules}

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {message}
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
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        full_response += chunk.content
                        yield chunk.content

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
    logger.info(f"Attempting to delete chatbot ID: {chatbot_id}")
    try:
        await chat_repository.delete_chatbot(chatbot_id)
        logger.info(f"Chatbot ID {chatbot_id} successfully deleted.")
        return {"message": "Chatbot deleted successfully!"}
    except Exception as exc:
        logger.error(f"Failed to delete chatbot ID {chatbot_id}: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
