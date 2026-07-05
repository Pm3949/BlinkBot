import os
import uuid
import logging
from typing import Optional, List, Dict
import asyncio
from fastapi import WebSocket, HTTPException
from fastapi.responses import StreamingResponse

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

from database_layer import chat_repository
from core.dependencies import rag_engine
from core.security import decrypt_key
from core.scrubber import scrub_pii
from handlers.websocket_handlers import agent_connection_manager

logger = logging.getLogger(__name__)


async def handle_chat_with_agent(websocket: WebSocket, client_id: str):
    await agent_connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_request":
                req_data = data.get("payload", {})
                agent_id = req_data.get("agent_id")
                message = req_data.get("message")
                history = req_data.get("history", [])
                language = req_data.get("language")

                if not agent_id or not message:
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
                    agent_data = await chat_repository.get_agent_for_chat(agent_id)
                    if not agent_data:
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
                    ) = agent_data
                    embed_model = embed_model or "text-embedding-3-small"
                    custom_api_key = decrypt_key(custom_api_key)

                    if not is_active:
                        await agent_connection_manager.send_json(
                            {
                                "type": "text_chunk",
                                "content": "Sorry, our custom services department is currently offline. Please try again later.",
                            },
                            client_id,
                        )
                        await agent_connection_manager.send_json(
                            {"type": "stream_end"}, client_id
                        )
                        continue

                    active_agent_id = agent_id
                    routed_agent_name = None
                    gateway_name = agent_name

                    if project_id and not parent_agent_id:
                        sub_agents = await chat_repository.get_sub_agents_for_project(
                            project_id
                        )

                        if len(sub_agents) > 1:
                            agent_descriptions_list = []
                            for sa in sub_agents:
                                is_master = str(sa[0]) == str(agent_id)
                                role_tag = (
                                    " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]"
                                    if is_master
                                    else ""
                                )
                                agent_descriptions_list.append(
                                    f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}"
                                )
                            agent_descriptions = "\n".join(agent_descriptions_list)

                            if provider == "openai":
                                key_to_use = custom_api_key or os.getenv(
                                    "OPENAI_API_KEY"
                                )
                                router_llm = ChatOpenAI(
                                    model_name=model,
                                    api_key=key_to_use,
                                    temperature=0.0,
                                )
                            elif provider == "ollama":
                                router_llm = ChatOllama(model=model, temperature=0.0)
                            else:
                                key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                                router_llm = ChatGroq(
                                    model_name=model,
                                    api_key=key_to_use,
                                    temperature=0.0,
                                )

                            routing_prompt = f"""You are the Master Coordinator Router.
Analyze the user's latest message and choose the best specialized sub-agent to handle it.

Available Agents:
{agent_descriptions}

User's Latest Message: {message}

Respond ONLY with the exact UUID of the chosen agent. Do not add any extra text, markdown, or formatting."""
                            try:
                                routing_response = router_llm.invoke(routing_prompt)
                                chosen_uuid = routing_response.content.strip()
                                chosen_agent = next(
                                    (
                                        sa
                                        for sa in sub_agents
                                        if str(sa[0]) == chosen_uuid
                                    ),
                                    None,
                                )
                                if chosen_agent and str(chosen_agent[0]) != str(
                                    agent_id
                                ):
                                    active_agent_id = chosen_agent[0]
                                    routed_agent_name = chosen_agent[1]
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
                                    ) = await chat_repository.get_agent_routing_info(
                                        active_agent_id
                                    )
                                    embed_model = (
                                        embed_model or "text-embedding-3-small"
                                    )
                                    custom_api_key = decrypt_key(custom_api_key)
                                    if not is_active:
                                        await agent_connection_manager.send_json(
                                            {
                                                "type": "text_chunk",
                                                "content": f"🤖 *[Routed to: {routed_agent_name}]*\n\nSorry, our custom services department is currently offline. Please try again later.",
                                            },
                                            client_id,
                                        )
                                        await agent_connection_manager.send_json(
                                            {"type": "stream_end"}, client_id
                                        )
                                        continue
                            except Exception as e:
                                logger.error(f"Dynamic routing failed: {e}")

                    current_msg_count, limits = (
                        await chat_repository.get_user_chat_limits(user_id)
                    )
                    if current_msg_count >= limits["agent_messages"]:
                        await agent_connection_manager.send_json(
                            {
                                "type": "error",
                                "content": "Monthly message limit exceeded. Please upgrade your plan.",
                            },
                            client_id,
                        )
                        continue

                    # LangGraph Multi-Agent Setup
                    from graph_orchestrator import build_multi_agent_graph

                    async def llm_factory(aid: str):
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
                        ) = await chat_repository.get_agent_routing_info(aid)
                        
                        emb_model = emb_model or "text-embedding-3-small"
                        c_key = decrypt_key(c_key)
                        mem_patch = await chat_repository.fetch_temporary_memory_patch(aid)
                        
                        formatted_prompt = sys_prompt
                        if out_fmt:
                            formatted_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{out_fmt}"
                        formatted_prompt += f"{mem_patch}\n\nYou are a highly intelligent ReAct agent. You have access to tools to search the knowledge base"
                        if web_enabled:
                            formatted_prompt += " and the web"
                        formatted_prompt += ".\nUse the tools iteratively if needed. Format your final response beautifully in Markdown.\n\nCRITICAL RULE: If you decide to call a tool, YOUR ENTIRE RESPONSE MUST BE ONLY THE TOOL CALL. Do NOT output any conversational text, greetings, or thoughts before or after the tool call. IF YOU OUTPUT TEXT AND A TOOL CALL TOGETHER, THE SYSTEM WILL CRASH."
                        
                        lang_map = {
                            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                            "hi": "Hindi", "zh-cn": "Chinese", "ja": "Japanese", "ko": "Korean",
                        }
                        if language and language.lower() != "en":
                            lang_name = lang_map.get(language.lower(), language)
                            formatted_prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                        if prov == "openai":
                            llm_inst = ChatOpenAI(model_name=mod, api_key=c_key or os.getenv("OPENAI_API_KEY"))
                        elif prov == "ollama":
                            llm_inst = ChatOllama(model=mod)
                        else:
                            llm_inst = ChatGroq(model_name=mod, api_key=c_key or os.getenv("GROQ_API_KEY"))

                        return llm_inst, formatted_prompt, emb_model, web_enabled

                    def tools_factory(aid: str, emb_model: str, web_enabled: bool, llm_inst):
                        from langchain_core.tools import tool
                        
                        @tool
                        async def search_knowledge_base(query: str) -> str:
                            """Search the internal knowledge base for documents. Use this first for ANY company-specific or factual questions."""
                            hyde_query = rag_engine.generate_hyde_query(query, llm_inst)
                            q_vec = rag_engine.vectorize([hyde_query], model_name=emb_model)[0]
                            best = await chat_repository.get_documents_hybrid(hyde_query, str(q_vec), aid, 15)
                            
                            if aid != agent_id:
                                master_b = await chat_repository.get_documents_hybrid(hyde_query, str(q_vec), agent_id, 15)
                                combined = best + master_b
                                seen = set()
                                best = []
                                for item in combined:
                                    if item[0] not in seen:
                                        seen.add(item[0])
                                        best.append(item)
                                        
                            best = rag_engine.rerank_documents(query, best, top_k=5)
                            docs = "\n---\n".join([decrypt_key(m[0]) or m[0] for m in best]) if best else "No related documents found."
                            return docs

                        @tool
                        async def search_web(query: str) -> str:
                            """Search the internet for current events, news, or general world knowledge."""
                            try:
                                from langchain_community.tools import DuckDuckGoSearchRun
                                search = DuckDuckGoSearchRun()
                                return search.run(query)
                            except Exception:
                                return "Web search failed or blocked."

                        t_list = [search_knowledge_base]
                        if web_enabled:
                            t_list.append(search_web)
                        return t_list

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
                    
                    async for event in graph.astream_events(inputs, version="v2"):
                        kind = event["event"]
                        
                        if kind == "on_chat_model_stream":
                            metadata = event.get("metadata", {})
                            # Only stream chunks from the actual agent node, not the supervisor router!
                            if metadata.get("langgraph_node") == "agent":
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
                                if routed_name and routed_name != gateway_name:
                                    await agent_connection_manager.send_json(
                                        {"type": "text_chunk", "content": f"🤖 *[Routed to: {routed_name}]*\n\n"}, client_id
                                    )

                    await agent_connection_manager.send_json({"type": "status", "content": ""}, client_id)
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

                except Exception as exc:
                    logger.exception("Chat generation failed")
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(exc)}, client_id
                    )

    except Exception:
        agent_connection_manager.disconnect(client_id)


async def handle_widget_chat(websocket: WebSocket, client_id: str):
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

                if not chatbot_id or not message:
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
                    chatbot_data = await chat_repository.get_chatbot_for_widget(
                        chatbot_id
                    )
                    if not chatbot_data:
                        await agent_connection_manager.send_json(
                            {"type": "error", "content": "Chatbot not found"}, client_id
                        )
                        continue

                    agent_id, settings, message_count, user_id, allowed_domains = (
                        chatbot_data
                    )

                    total_widget_msgs, limits = (
                        await chat_repository.check_widget_limits(user_id)
                    )
                    if total_widget_msgs >= limits["chatbot_messages"]:
                        await agent_connection_manager.send_json(
                            {
                                "type": "error",
                                "content": "Monthly widget message limit exceeded. Please upgrade your plan.",
                            },
                            client_id,
                        )
                        continue

                    await chat_repository.log_widget_message(chatbot_id)

                    agent_data = await chat_repository.get_agent_routing_info(agent_id)
                    if not agent_data:
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
                    ) = agent_data
                    embed_model = embed_model or "text-embedding-3-small"
                    custom_api_key = decrypt_key(custom_api_key)

                    if not is_active:
                        await agent_connection_manager.send_json(
                            {
                                "type": "text_chunk",
                                "content": "Sorry, our custom services department is currently offline. Please try again later.",
                            },
                            client_id,
                        )
                        await agent_connection_manager.send_json(
                            {"type": "stream_end"}, client_id
                        )
                        continue

                    if provider == "openai":
                        key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                        llm = ChatOpenAI(model_name=model, api_key=key_to_use)
                    elif provider == "ollama":
                        llm = ChatOllama(model=model)
                    else:
                        key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                        llm = ChatGroq(model_name=model, api_key=key_to_use)

                    hyde_query = rag_engine.generate_hyde_query(message, llm)
                    query_vector = rag_engine.vectorize(
                        [hyde_query], model_name=embed_model
                    )[0]

                    best_matches = await chat_repository.get_documents_hybrid(
                        hyde_query, str(query_vector), agent_id, 15
                    )
                    best_matches = rag_engine.rerank_documents(
                        message, best_matches, top_k=5
                    )

                    context = "No specific documents found."
                    if best_matches:
                        context = "\n\n---\n\n".join(
                            [
                                decrypt_key(match[0]) or match[0]
                                for match in best_matches
                            ]
                        )

                    history_items = history or []
                    history_text = ""
                    for msg in history_items[-6:]:
                        role_name = "User" if msg.get("role") == "user" else "Assistant"
                        history_text += f"{role_name}: {msg.get('content', '')}\n"
                    if not history_text:
                        history_text = "No previous conversation."

                    memory_patch = await chat_repository.fetch_temporary_memory_patch(
                        agent_id
                    )

                    formatted_system_prompt = system_prompt
                    if output_format:
                        formatted_system_prompt += (
                            f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{output_format}"
                        )

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
                        "en": "English",
                        "es": "Spanish",
                        "fr": "French",
                        "de": "German",
                        "hi": "Hindi",
                        "zh-cn": "Chinese",
                        "ja": "Japanese",
                        "ko": "Korean",
                    }
                    if language and language.lower() != "en":
                        lang_name = lang_map.get(language.lower(), language)
                        prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                    for chunk in llm.stream(prompt):
                        if chunk.content:
                            await agent_connection_manager.send_json(
                                {"type": "text_chunk", "content": chunk.content},
                                client_id,
                            )

                    await agent_connection_manager.send_json(
                        {"type": "stream_end"}, client_id
                    )

                except Exception as e:
                    logger.error(f"Widget Chat endpoint failed", exc_info=True)
                    await agent_connection_manager.send_json(
                        {"type": "error", "content": str(e)}, client_id
                    )

    except Exception:
        agent_connection_manager.disconnect(client_id)


async def handle_api_v1_chat(
    message: str, session_id: Optional[str], language: Optional[str], x_api_key: str
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")

    try:
        chatbot_data = await chat_repository.get_chatbot_by_api_key(x_api_key)
        if not chatbot_data:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        chatbot_id, master_agent_id, user_id = chatbot_data

        message = scrub_pii(message)

        if not session_id:
            session_id = str(uuid.uuid4())
            await chat_repository.create_chat_session(
                session_id, message[:50], master_agent_id
            )

        user_msg_id = str(uuid.uuid4())
        await chat_repository.insert_chat_message(
            user_msg_id, session_id, "user", message
        )

        history_rows = await chat_repository.get_session_history(session_id)
        history_items = [
            {"role": row[0], "content": row[1]} for row in history_rows[:-1]
        ]

        agent_data = await chat_repository.get_agent_for_chat(master_agent_id)
        if not agent_data:
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
        ) = agent_data
        embed_model = embed_model or "text-embedding-3-small"
        custom_api_key = decrypt_key(custom_api_key)

        if not is_active:

            async def offline_stream():
                yield "Sorry, our custom services department is currently offline. Please try again later."

            return (
                StreamingResponse(offline_stream(), media_type="text/plain"),
                session_id,
            )

        active_agent_id = master_agent_id
        routed_agent_name = None
        gateway_name = agent_name

        if project_id and not parent_agent_id:
            sub_agents = await chat_repository.get_sub_agents_for_project(project_id)

            if len(sub_agents) > 1:
                agent_descriptions_list = []
                for sa in sub_agents:
                    is_master = str(sa[0]) == str(master_agent_id)
                    role_tag = (
                        " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]"
                        if is_master
                        else ""
                    )
                    agent_descriptions_list.append(
                        f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}"
                    )
                agent_descriptions = "\n".join(agent_descriptions_list)

                if provider == "openai":
                    key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                    router_llm = ChatOpenAI(
                        model_name=model, api_key=key_to_use, temperature=0.0
                    )
                elif provider == "ollama":
                    router_llm = ChatOllama(model=model, temperature=0.0)
                else:
                    key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                    router_llm = ChatGroq(
                        model_name=model, api_key=key_to_use, temperature=0.0
                    )

                routing_prompt = f"""You are the Master Coordinator Router.
Analyze the user's latest message and choose the best specialized sub-agent to handle it.

Available Agents:
{agent_descriptions}

User's Latest Message: {message}

Respond ONLY with the exact UUID of the chosen agent. Do not add any extra text, markdown, or formatting."""

                try:
                    routing_response = router_llm.invoke(routing_prompt)
                    chosen_uuid = routing_response.content.strip()

                    chosen_agent = next(
                        (sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None
                    )
                    if chosen_agent and str(chosen_agent[0]) != str(master_agent_id):
                        active_agent_id = chosen_agent[0]
                        routed_agent_name = chosen_agent[1]

                        agent_data = await chat_repository.get_agent_routing_info(
                            active_agent_id
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
                        ) = agent_data
                        embed_model = embed_model or "text-embedding-3-small"
                        custom_api_key = decrypt_key(custom_api_key)

                        if not is_active:

                            async def offline_stream():
                                yield f"🤖 *[Routed to: {routed_agent_name}]*\n\nSorry, our custom services department is currently offline. Please try again later."

                            return (
                                StreamingResponse(
                                    offline_stream(), media_type="text/plain"
                                ),
                                session_id,
                            )
                except Exception as e:
                    logger.error(f"Dynamic routing failed: {e}")

        hyde_query = rag_engine.generate_hyde_query(message, llm)
        query_vector = rag_engine.vectorize([hyde_query], model_name=embed_model)[0]
        best_matches = await chat_repository.get_documents_hybrid(
            hyde_query, str(query_vector), active_agent_id, 15
        )

        if active_agent_id != master_agent_id:
            master_matches = await chat_repository.get_documents_hybrid(
                hyde_query, str(query_vector), master_agent_id, 15
            )
            combined = best_matches + master_matches
            seen = set()
            unique_combined = []
            for item in combined:
                if item[0] not in seen:
                    seen.add(item[0])
                    unique_combined.append(item)
            best_matches = unique_combined

        best_matches = rag_engine.rerank_documents(message, best_matches, top_k=5)

        context = "No specific documents found."
        if best_matches:
            context = "\n\n---\n\n".join(
                [decrypt_key(match[0]) or match[0] for match in best_matches]
            )

        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        memory_patch = await chat_repository.fetch_temporary_memory_patch(
            active_agent_id
        )

        formatted_system_prompt = system_prompt
        if output_format:
            formatted_system_prompt += (
                f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{output_format}"
            )

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
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "hi": "Hindi",
            "zh-cn": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
        }
        if language and language.lower() != "en":
            lang_name = lang_map.get(language.lower(), language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        await chat_repository.log_widget_message(chatbot_id)

        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        elif provider == "ollama":
            llm = ChatOllama(model=model)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        async def stream_generator():
            full_response = ""
            try:
                if routed_agent_name and routed_agent_name != gateway_name:
                    prefix = f"🤖 *[Routed to: {routed_agent_name}]*\n\n"
                    full_response += prefix
                    yield prefix

                for chunk in llm.stream(prompt):
                    if chunk.content:
                        full_response += chunk.content
                        yield chunk.content

                try:
                    assist_msg_id = str(uuid.uuid4())
                    await chat_repository.insert_chat_message(
                        assist_msg_id, session_id, "assistant", full_response
                    )
                except Exception as db_e:
                    logger.error(f"Failed to save assistant message: {db_e}")

            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return (
            StreamingResponse(stream_generator(), media_type="text/plain"),
            session_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("API Chat endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_agent(agent_id: str):
    try:
        deleted_count = await chat_repository.delete_agent(agent_id)
        if deleted_count == 0:
            return {"message": "Agent not found or already deleted"}

        return {
            "message": f"Agent and {deleted_count - 1} sub-agents completely wiped!"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


async def handle_delete_chatbot(chatbot_id: str):
    try:
        await chat_repository.delete_chatbot(chatbot_id)
        return {"message": "Chatbot deleted successfully!"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
