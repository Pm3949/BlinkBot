import os
import uuid
import logging
from typing import Optional, List, Dict
from fastapi import WebSocket, HTTPException
from fastapi.responses import StreamingResponse

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

from database import get_db_connection
from core.dependencies import rag_engine
from utils import get_user_limits
from core.security import decrypt_key
from core.scrubber import scrub_pii
from handlers.websocket_handlers import agent_connection_manager

logger = logging.getLogger(__name__)

def fetch_temporary_memory_patch(cursor, agent_id: str) -> str:
    """
    What it does: Finds any bad feedback the user gave in the past and tells the AI not to make those mistakes again.
    Args:
        cursor: The database cursor to run queries.
        agent_id (str): The ID of the agent we are talking to.
    Returns: A string containing instructions for the AI on what to avoid.
    """
    try:
        cursor.execute(
            """
            SELECT f.category, f.comment_text, m.content
            FROM message_feedback f
            JOIN chat_messages m ON f.message_id = m.id
            WHERE f.agent_id = %s AND f.status = 'open'
            """,
            (agent_id,)
        )
        open_tickets = cursor.fetchall()
        if not open_tickets:
            return ""
            
        patch = "\n\nCRITICAL TEMPORARY CORRECTIONS (USER FEEDBACK):\n"
        patch += "The following errors were flagged in your previous answers. You MUST NOT repeat these mistakes and MUST incorporate these corrections in your responses:\n"
        for cat, comment, msg_content in open_tickets:
            short_msg = msg_content[:50] + "..." if msg_content else "Unknown message"
            patch += f"- [Flagged {cat} in past answer: '{short_msg}']: {comment}\n"
        
        return patch
    except Exception as e:
        logger.error(f"Error fetching memory patch: {e}")
        return ""


async def handle_chat_with_agent(websocket: WebSocket, client_id: str):
    """
    What it does: Runs the continuous chat loop for the internal dashboard. It receives messages, finds relevant documents, decides if a sub-agent should handle it, asks the AI, and streams the answer back.
    Args:
        websocket (WebSocket): The active connection to the user's browser.
        client_id (str): The unique ID of the user's chat session.
    Returns: None. Keeps running until the user disconnects.
    """
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
                    await agent_connection_manager.send_json({"type": "error", "content": "agent_id and message are required"}, client_id)
                    continue

                message = scrub_pii(message)
                conn = None
                cursor = None
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        "SELECT user_id, name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, project_id, parent_agent_id, is_active FROM agents WHERE id = %s",
                        (agent_id,),
                    )
                    agent_data = cursor.fetchone()
                    if not agent_data:
                        await agent_connection_manager.send_json({"type": "error", "content": "Agent not found"}, client_id)
                        continue

                    (user_id, agent_name, system_prompt, output_format, provider, model, custom_api_key, embed_model, web_search_enabled, project_id, parent_agent_id, is_active) = agent_data
                    embed_model = embed_model or "text-embedding-3-small"
                    custom_api_key = decrypt_key(custom_api_key)
                    
                    if not is_active:
                        await agent_connection_manager.send_json({"type": "text_chunk", "content": "Sorry, our custom services department is currently offline. Please try again later."}, client_id)
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    active_agent_id = agent_id
                    routed_agent_name = None
                    gateway_name = agent_name

                    if project_id and not parent_agent_id:
                        cursor.execute("SELECT id, name, description FROM agents WHERE project_id = %s", (project_id,))
                        sub_agents = cursor.fetchall()
                        
                        if len(sub_agents) > 1:
                            agent_descriptions_list = []
                            for sa in sub_agents:
                                is_master = str(sa[0]) == str(agent_id)
                                role_tag = " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]" if is_master else ""
                                agent_descriptions_list.append(f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}")
                            agent_descriptions = "\n".join(agent_descriptions_list)
                            
                            if provider == "openai":
                                key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                                router_llm = ChatOpenAI(model_name=model, api_key=key_to_use, temperature=0.0)
                            elif provider == "ollama":
                                router_llm = ChatOllama(model=model, temperature=0.0)
                            else:
                                key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                                router_llm = ChatGroq(model_name=model, api_key=key_to_use, temperature=0.0)
                            
                            routing_prompt = f"""You are the Master Coordinator Router.
Analyze the user's latest message and choose the best specialized sub-agent to handle it.

Available Agents:
{agent_descriptions}

User's Latest Message: {message}

Respond ONLY with the exact UUID of the chosen agent. Do not add any extra text, markdown, or formatting."""
                            try:
                                routing_response = router_llm.invoke(routing_prompt)
                                chosen_uuid = routing_response.content.strip()
                                chosen_agent = next((sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None)
                                if chosen_agent and str(chosen_agent[0]) != str(agent_id):
                                    active_agent_id = chosen_agent[0]
                                    routed_agent_name = chosen_agent[1]
                                    cursor.execute(
                                        "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, is_active FROM agents WHERE id = %s",
                                        (active_agent_id,),
                                    )
                                    (agent_name, system_prompt, output_format, provider, model, custom_api_key, embed_model, web_search_enabled, is_active) = cursor.fetchone()
                                    embed_model = embed_model or "text-embedding-3-small"
                                    custom_api_key = decrypt_key(custom_api_key)
                                    if not is_active:
                                        await agent_connection_manager.send_json({"type": "text_chunk", "content": f"🤖 *[Routed to: {routed_agent_name}]*\n\nSorry, our custom services department is currently offline. Please try again later."}, client_id)
                                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                                        continue
                            except Exception as e:
                                logger.error(f"Dynamic routing failed: {e}")

                    limits = get_user_limits(user_id, cursor)
                    cursor.execute(
                        """
                        SELECT count(*) 
                        FROM chat_messages m
                        JOIN chat_sessions s ON m.session_id = s.id
                        JOIN agents a ON s.agent_id = a.id
                        WHERE a.user_id = %s AND m.role = 'user' 
                        AND date_trunc('month', m.created_at) = date_trunc('month', current_date)
                        """,
                        (user_id,),
                    )
                    current_msg_count = cursor.fetchone()[0] or 0
                    if current_msg_count >= limits["agent_messages"]:
                        await agent_connection_manager.send_json({"type": "error", "content": "Monthly message limit exceeded. Please upgrade your plan."}, client_id)
                        continue

                    if provider == "openai":
                        key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                        llm = ChatOpenAI(model_name=model, api_key=key_to_use)
                    elif provider == "ollama":
                        llm = ChatOllama(model=model)
                    else:
                        key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                        llm = ChatGroq(model_name=model, api_key=key_to_use)

                    query_vector = rag_engine.vectorize([message], model_name=embed_model)[0]
                    cursor.execute(
                        "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                        (message, str(query_vector), active_agent_id),
                    )
                    best_matches = cursor.fetchall()
                    if active_agent_id != agent_id:
                        cursor.execute(
                            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                            (message, str(query_vector), agent_id),
                        )
                        master_matches = cursor.fetchall()
                        combined = best_matches + master_matches
                        seen = set()
                        unique_combined = []
                        for item in combined:
                            if item[0] not in seen:
                                seen.add(item[0])
                                unique_combined.append(item)
                        unique_combined.sort(key=lambda x: x[1], reverse=True)
                        best_matches = unique_combined[:5]

                    doc_context = "No specific documents found."
                    if best_matches:
                        doc_context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])

                    web_context = "Web search disabled."
                    if web_search_enabled:
                        try:
                            search = DuckDuckGoSearchRun()
                            web_context = search.run(message)
                        except Exception as e:
                            logger.error(f"Web search failed: {e}")
                            web_context = "Web search failed or was blocked by the search engine."

                    history_items = history or []
                    history_text = ""
                    for msg in history_items[-6:]:
                        role_name = "User" if msg.get("role") == "user" else "Assistant"
                        history_text += f"{role_name}: {msg.get('content', '')}\n"
                    if not history_text:
                        history_text = "No previous conversation."
                        
                    memory_patch = fetch_temporary_memory_patch(cursor, active_agent_id)

                    if not best_matches and not web_search_enabled:
                        grounding_rules = """
                    5. CRITICAL: THERE ARE NO DOCUMENTS LOADED. You MUST NOT answer any factual questions using general knowledge.
                    6. For casual greetings (e.g., 'hello', 'hi'), you may reply naturally in 1 sentence, but mention that no documents are uploaded.
                    7. For any factual questions, you MUST reply with exactly: "I cannot answer this question because no documents have been uploaded to my knowledge base. Please upload documents in the Knowledge Base first."
                        """
                    elif web_search_enabled:
                        grounding_rules = """
                    5. You have access to both PRIVATE DOCUMENTS CONTEXT and WEB SEARCH CONTEXT.
                    6. Answer accurately. If the contexts conflict, prioritize the Private Documents.
                    7. If you used the WEB SEARCH CONTEXT to answer any part of the question, you MUST start your entire response with the exact tag: [WEB_SOURCE]
                    8. Do not use general knowledge outside of the provided contexts.
                        """
                    else:
                        grounding_rules = """
                    5. You are a strict, professional AI assistant grounded ONLY in the provided PRIVATE DOCUMENTS CONTEXT.
                    6. For factual questions, ONLY answer using the provided CONTEXT.
                    7. If the answer is NOT in the context, DO NOT use general knowledge. Politely inform the user that you can only answer questions based on the uploaded documents.
                        """

                    formatted_system_prompt = system_prompt
                    if output_format:
                        formatted_system_prompt += f"\n\nCRITICAL FORMATTING INSTRUCTIONS:\n{output_format}"
                        
                    prompt = f"""{formatted_system_prompt}{memory_patch}
                    You are a helpful assistant. Use the following context to answer the user.

                    CRITICAL RULES:
                    1. Format response beautifully in Markdown.
                    2. Use the PREVIOUS CHAT HISTORY to understand context.
                    3. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
                    4. DETAIL RULE: For summaries/essays, provide highly detailed answers.{grounding_rules}

                    ---
                    PRIVATE DOCUMENTS CONTEXT:
                    {doc_context}
                    ---
                    WEB SEARCH CONTEXT:
                    {web_context}
                    ---

                    PREVIOUS CHAT HISTORY:
                    {history_text}

                    CURRENT USER INPUT: {message}
                    """

                    lang_map = {
                        "en": "English", "es": "Spanish", "fr": "French",
                        "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
                        "ja": "Japanese", "ko": "Korean"
                    }
                    if language and language.lower() != "en":
                        lang_name = lang_map.get(language.lower(), language)
                        prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                    if routed_agent_name and routed_agent_name != gateway_name:
                        await agent_connection_manager.send_json({"type": "text_chunk", "content": f"🤖 *[Routed to: {routed_agent_name}]*\n\n"}, client_id)
                        
                    for chunk in llm.stream(prompt):
                        if chunk.content:
                            await agent_connection_manager.send_json({"type": "text_chunk", "content": chunk.content}, client_id)
                            
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

                except Exception as exc:
                    logger.exception("Chat generation failed")
                    await agent_connection_manager.send_json({"type": "error", "content": str(exc)}, client_id)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

    except Exception:
        agent_connection_manager.disconnect(client_id)


async def handle_widget_chat(websocket: WebSocket, client_id: str):
    """
    What it does: Runs the continuous chat loop for the external website widget. It receives messages from visitors, limits usage based on the user's plan, finds answers, and sends them back.
    Args:
        websocket (WebSocket): The active connection to the visitor's browser.
        client_id (str): The unique ID of the visitor's chat session.
    Returns: None. Keeps running until the visitor disconnects.
    """
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
                    await agent_connection_manager.send_json({"type": "error", "content": "chatbot_id and message are required"}, client_id)
                    continue

                message = scrub_pii(message)
                conn = None
                cursor = None
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        "SELECT c.agent_id, c.settings, c.message_count, a.user_id, c.allowed_domains FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s",
                        (chatbot_id,),
                    )
                    chatbot_data = cursor.fetchone()
                    if not chatbot_data:
                        await agent_connection_manager.send_json({"type": "error", "content": "Chatbot not found"}, client_id)
                        continue

                    agent_id, settings, message_count, user_id, allowed_domains = chatbot_data

                    limits = get_user_limits(user_id, cursor)
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(message_count), 0)
                        FROM chatbots c
                        JOIN agents a ON c.agent_id = a.id
                        WHERE a.user_id = %s
                    """,
                        (user_id,),
                    )
                    total_widget_msgs = cursor.fetchone()[0] or 0
                    if total_widget_msgs >= limits["chatbot_messages"]:
                        await agent_connection_manager.send_json({"type": "error", "content": "Monthly widget message limit exceeded. Please upgrade your plan."}, client_id)
                        continue

                    cursor.execute("UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (chatbot_id,))
                    cursor.execute("INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,))
                    conn.commit()

                    cursor.execute(
                        "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, is_active FROM agents WHERE id = %s",
                        (agent_id,),
                    )
                    agent_data = cursor.fetchone()
                    if not agent_data:
                        await agent_connection_manager.send_json({"type": "error", "content": "Underlying Agent not found"}, client_id)
                        continue

                    agent_name, system_prompt, output_format, provider, model, custom_api_key, embed_model, is_active = agent_data
                    embed_model = embed_model or "text-embedding-3-small"
                    custom_api_key = decrypt_key(custom_api_key)
                    
                    if not is_active:
                        await agent_connection_manager.send_json({"type": "text_chunk", "content": "Sorry, our custom services department is currently offline. Please try again later."}, client_id)
                        await agent_connection_manager.send_json({"type": "stream_end"}, client_id)
                        continue

                    if provider == "openai":
                        key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                        llm = ChatOpenAI(model_name=model, api_key=key_to_use)
                    elif provider == "ollama":
                        llm = ChatOllama(model=model)
                    else:
                        key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                        llm = ChatGroq(model_name=model, api_key=key_to_use)

                    query_vector = rag_engine.vectorize([message], model_name=embed_model)[0]

                    cursor.execute(
                        "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                        (message, str(query_vector), agent_id),
                    )
                    best_matches = cursor.fetchall()

                    context = "No specific documents found."
                    if best_matches:
                        context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])

                    history_items = history or []
                    history_text = ""
                    for msg in history_items[-6:]:
                        role_name = "User" if msg.get("role") == "user" else "Assistant"
                        history_text += f"{role_name}: {msg.get('content', '')}\n"
                    if not history_text:
                        history_text = "No previous conversation."

                    memory_patch = fetch_temporary_memory_patch(cursor, agent_id)

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
                        "en": "English", "es": "Spanish", "fr": "French",
                        "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
                        "ja": "Japanese", "ko": "Korean"
                    }
                    if language and language.lower() != "en":
                        lang_name = lang_map.get(language.lower(), language)
                        prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

                    for chunk in llm.stream(prompt):
                        if chunk.content:
                            await agent_connection_manager.send_json({"type": "text_chunk", "content": chunk.content}, client_id)
                            
                    await agent_connection_manager.send_json({"type": "stream_end"}, client_id)

                except Exception as e:
                    logger.error(f"Widget Chat endpoint failed", exc_info=True)
                    if conn and not conn.closed:
                        try:
                            conn.rollback()
                        except:
                            pass 
                    await agent_connection_manager.send_json({"type": "error", "content": str(e)}, client_id)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

    except Exception:
        agent_connection_manager.disconnect(client_id)


async def handle_api_v1_chat(message: str, session_id: Optional[str], language: Optional[str], x_api_key: str):
    """
    What it does: Processes a chat message sent programmatically via an API key. It authenticates the key, finds the answer, logs the conversation, and sends the answer back as a continuous stream of text.
    Args:
        message (str): The user's question.
        session_id (str, optional): An ID to remember past messages in this conversation.
        language (str, optional): The language to respond in.
        x_api_key (str): The developer's secret API key.
    Returns: A StreamingResponse that sends the text back piece by piece.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT c.id, c.agent_id, a.user_id FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.api_key = %s",
            (x_api_key,),
        )
        chatbot_data = cursor.fetchone()
        if not chatbot_data:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        chatbot_id, master_agent_id, user_id = chatbot_data

        message = scrub_pii(message)

        if not session_id:
            session_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chat_sessions (id, title, agent_id) VALUES (%s, %s, %s)",
                (session_id, message[:50], master_agent_id)
            )
        
        user_msg_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO chat_messages (id, session_id, role, content) VALUES (%s, %s, 'user', %s)",
            (user_msg_id, session_id, message)
        )
        conn.commit()

        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT 10",
            (session_id,)
        )
        history_rows = cursor.fetchall()
        history_items = [{"role": row[0], "content": row[1]} for row in history_rows[:-1]]
        
        cursor.execute(
            "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, project_id, parent_agent_id, is_active FROM agents WHERE id = %s",
            (master_agent_id,),
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        (
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
            is_active
        ) = agent_data
        embed_model = embed_model or "text-embedding-3-small"
        custom_api_key = decrypt_key(custom_api_key)
        
        if not is_active:
            async def offline_stream():
                yield "Sorry, our custom services department is currently offline. Please try again later."
            return StreamingResponse(offline_stream(), media_type="text/plain"), session_id

        active_agent_id = master_agent_id
        routed_agent_name = None
        gateway_name = agent_name

        if project_id and not parent_agent_id:
            cursor.execute("SELECT id, name, description FROM agents WHERE project_id = %s", (project_id,))
            sub_agents = cursor.fetchall()
            
            if len(sub_agents) > 1:
                agent_descriptions_list = []
                for sa in sub_agents:
                    is_master = str(sa[0]) == str(master_agent_id)
                    role_tag = " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]" if is_master else ""
                    agent_descriptions_list.append(f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}")
                agent_descriptions = "\n".join(agent_descriptions_list)
                
                if provider == "openai":
                    key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
                    router_llm = ChatOpenAI(model_name=model, api_key=key_to_use, temperature=0.0)
                elif provider == "ollama":
                    router_llm = ChatOllama(model=model, temperature=0.0)
                else:
                    key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
                    router_llm = ChatGroq(model_name=model, api_key=key_to_use, temperature=0.0)
                
                routing_prompt = f"""You are the Master Coordinator Router.
Analyze the user's latest message and choose the best specialized sub-agent to handle it.

Available Agents:
{agent_descriptions}

User's Latest Message: {message}

Respond ONLY with the exact UUID of the chosen agent. Do not add any extra text, markdown, or formatting."""
                
                try:
                    routing_response = router_llm.invoke(routing_prompt)
                    chosen_uuid = routing_response.content.strip()
                    
                    chosen_agent = next((sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None)
                    if chosen_agent and str(chosen_agent[0]) != str(master_agent_id):
                        active_agent_id = chosen_agent[0]
                        routed_agent_name = chosen_agent[1]
                        
                        cursor.execute(
                            "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, is_active FROM agents WHERE id = %s",
                            (active_agent_id,),
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
                            is_active
                        ) = cursor.fetchone()
                        embed_model = embed_model or "text-embedding-3-small"
                        custom_api_key = decrypt_key(custom_api_key)
                        
                        if not is_active:
                            async def offline_stream():
                                yield f"🤖 *[Routed to: {routed_agent_name}]*\n\nSorry, our custom services department is currently offline. Please try again later."
                            return StreamingResponse(offline_stream(), media_type="text/plain"), session_id
                except Exception as e:
                    logger.error(f"Dynamic routing failed: {e}")

        query_vector = rag_engine.vectorize([message], model_name=embed_model)[0]
        cursor.execute(
            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
            (message, str(query_vector), active_agent_id),
        )
        best_matches = cursor.fetchall()

        if active_agent_id != master_agent_id:
            cursor.execute(
                "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                (message, str(query_vector), master_agent_id),
            )
            master_matches = cursor.fetchall()
            combined = best_matches + master_matches
            seen = set()
            unique_combined = []
            for item in combined:
                if item[0] not in seen:
                    seen.add(item[0])
                    unique_combined.append(item)
            unique_combined.sort(key=lambda x: x[1], reverse=True)
            best_matches = unique_combined[:5]

        context = "No specific documents found."
        if best_matches:
            context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])

        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        memory_patch = fetch_temporary_memory_patch(cursor, active_agent_id)

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
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
            "ja": "Japanese", "ko": "Korean"
        }
        if language and language.lower() != "en":
            lang_name = lang_map.get(language.lower(), language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        cursor.execute("UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (chatbot_id,))
        cursor.execute("INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,))
        conn.commit()

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
                    save_conn = get_db_connection()
                    save_cursor = save_conn.cursor()
                    assist_msg_id = str(uuid.uuid4())
                    save_cursor.execute(
                        "INSERT INTO chat_messages (id, session_id, role, content) VALUES (%s, %s, 'assistant', %s)",
                        (assist_msg_id, session_id, full_response)
                    )
                    save_conn.commit()
                    save_cursor.close()
                    save_conn.close()
                except Exception as db_e:
                    logger.error(f"Failed to save assistant message: {db_e}")

            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain"), session_id

    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as exc:
        logger.exception("API Chat endpoint failed")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


async def handle_delete_agent(agent_id: str):
    """
    What it does: Completely erases an AI agent, its documents, and its past conversations from the system. It also deletes any smaller sub-agents attached to it.
    Args:
        agent_id (str): The ID of the agent to delete.
    Returns: A confirmation message showing how many agents were deleted.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            WITH RECURSIVE agent_tree AS (
                SELECT id FROM agents WHERE id = %s
                UNION
                SELECT a.id 
                FROM agents a
                INNER JOIN agent_tree at ON a.parent_agent_id = at.id
            )
            SELECT id FROM agent_tree;
            """,
            (agent_id,)
        )
        rows = cursor.fetchall()
        if not rows:
            return {"message": "Agent not found or already deleted"}
            
        descendant_ids = tuple(row[0] for row in rows)
        
        cursor.execute(
            """
            DELETE FROM document_embeddings
            WHERE document_id IN (SELECT id FROM documents WHERE agent_id IN %s)
            """,
            (descendant_ids,),
        )
        cursor.execute("DELETE FROM documents WHERE agent_id IN %s", (descendant_ids,))
        cursor.execute(
            """
            DELETE FROM chat_messages 
            WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id IN %s)
            """,
            (descendant_ids,),
        )
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id IN %s", (descendant_ids,))
        cursor.execute("DELETE FROM agents WHERE id IN %s", (descendant_ids,))
        conn.commit()
        return {"message": f"Agent and {len(descendant_ids) - 1} sub-agents completely wiped!"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def handle_delete_chatbot(chatbot_id: str):
    """
    What it does: Erases an external chat widget and all the message logs it collected.
    Args:
        chatbot_id (str): The ID of the chatbot widget to delete.
    Returns: A confirmation message.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM widget_message_logs WHERE chatbot_id = %s", (chatbot_id,)
        )
        cursor.execute("DELETE FROM chatbots WHERE id = %s", (chatbot_id,))
        conn.commit()
        return {"message": "Chatbot deleted successfully!"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
