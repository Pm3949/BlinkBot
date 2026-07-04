"""
Chat Router (The Core Conversational Engine).
Responsibility: Receives user messages, performs Hybrid Search (RAG) to find context, 
handles dynamic routing to sub-agents (Multi-Agent framework), builds the final prompt, 
and streams the LLM response back.
"""
import json
import logging
import os
import psycopg2
from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Header, Response
from fastapi.responses import StreamingResponse

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun

from database import get_db_connection
from schemas import ChatRequest, WidgetChatRequest
from core.dependencies import rag_engine
from utils import get_user_limits
from core.security import decrypt_key
from routers.auth import limiter
from core.scrubber import scrub_pii

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

def fetch_temporary_memory_patch(cursor, agent_id: str) -> str:
    """
    Self-Correction Mechanism: Fetches any "open" feedback tickets where users 
    complained about previous bad answers. These are injected into the system prompt 
    so the AI knows not to repeat its mistakes.
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

# ==========================================
# INTERNAL CHAT ENDPOINT (Web Dashboard)
# ==========================================

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """
    Stream an LLM response grounded in the uploaded documents.
    Used by the main web dashboard interface.
    """
    if not req.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    # Security: Scrub Personally Identifiable Information (SSN, Cards) before sending to LLMs
    req.message = scrub_pii(req.message)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Load Agent Configuration
        cursor.execute(
            "SELECT user_id, name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, project_id, parent_agent_id, is_active FROM agents WHERE id = %s",
            (req.agent_id,),
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

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
            is_active
        ) = agent_data
        embed_model = embed_model or "text-embedding-3-small"
        custom_api_key = decrypt_key(custom_api_key)
        
        # Graceful degradation if the agent is disabled by the owner
        if not is_active:
            async def offline_stream():
                yield "Sorry, our custom services department is currently offline. Please try again later."
            return StreamingResponse(offline_stream(), media_type="text/plain")
        
        active_agent_id = req.agent_id
        routed_agent_name = None
        gateway_name = agent_name

        # ==========================================
        # DYNAMIC ROUTING (Multi-Agent Switcher)
        # ==========================================
        # If this agent belongs to a Project and is a "Master Agent" (has no parent),
        # we check if there are specialized sub-agents we should route this query to.
        if project_id and not parent_agent_id:
            cursor.execute("SELECT id, name, description FROM agents WHERE project_id = %s", (project_id,))
            sub_agents = cursor.fetchall()
            
            if len(sub_agents) > 1:
                agent_descriptions_list = []
                for sa in sub_agents:
                    is_master = str(sa[0]) == str(req.agent_id)
                    role_tag = " [MASTER/GLOBAL - Default fallback for general knowledge & uploaded files]" if is_master else ""
                    agent_descriptions_list.append(f"ID: {sa[0]} | Name: {sa[1]}{role_tag} | Description: {sa[2]}")
                agent_descriptions = "\n".join(agent_descriptions_list)
                
                # Setup a cheap, fast routing LLM to decide which agent should answer
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

User's Latest Message: {req.message}

Respond ONLY with the exact UUID of the chosen agent. Do not add any extra text, markdown, or formatting."""
                
                try:
                    routing_response = router_llm.invoke(routing_prompt)
                    chosen_uuid = routing_response.content.strip()
                    
                    chosen_agent = next((sa for sa in sub_agents if str(sa[0]) == chosen_uuid), None)
                    if chosen_agent and str(chosen_agent[0]) != str(req.agent_id):
                        active_agent_id = chosen_agent[0]
                        routed_agent_name = chosen_agent[1]
                        
                        # OVERRIDE CONTEXT: The chosen sub-agent's settings overwrite the master agent's settings
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
                            return StreamingResponse(offline_stream(), media_type="text/plain")
                except Exception as e:
                    logger.error(f"Dynamic routing failed: {e}")

        # ==========================================
        # BILLING CHECK
        # ==========================================
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
            raise HTTPException(
                status_code=403,
                detail="Monthly message limit exceeded. Please upgrade your plan.",
            )

        # ==========================================
        # LLM INITIALIZATION
        # ==========================================
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

        # ==========================================
        # RAG HYBRID SEARCH (Retrieval)
        # ==========================================
        # 1. Convert user message to a mathematical vector
        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]

        # 2. Run Hybrid Search (BM25 Keyword + Vector Similarity)
        cursor.execute(
            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
            (req.message, str(query_vector), active_agent_id),
        )
        best_matches = cursor.fetchall()

        # If routed to sub-agent, fallback to query master agent (req.agent_id) documents as well
        if active_agent_id != req.agent_id:
            cursor.execute(
                "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                (req.message, str(query_vector), req.agent_id),
            )
            master_matches = cursor.fetchall()
            # Combine, deduplicate, and sort by similarity
            combined = best_matches + master_matches
            seen = set()
            unique_combined = []
            for item in combined:
                if item[0] not in seen:
                    seen.add(item[0])
                    unique_combined.append(item)
            unique_combined.sort(key=lambda x: x[1], reverse=True)
            best_matches = unique_combined[:5]

        # 3. Concatenate the retrieved chunks
        doc_context = "No specific documents found."
        if best_matches:
            doc_context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])

        # ==========================================
        # WEB SEARCH INTEGRATION
        # ==========================================
        web_context = "Web search disabled."
        if web_search_enabled:
            try:
                search = DuckDuckGoSearchRun()
                web_context = search.run(req.message)
            except Exception as e:
                logger.error(f"Web search failed: {e}")
                web_context = "Web search failed or was blocked by the search engine."

        # ==========================================
        # PROMPT CONSTRUCTION
        # ==========================================
        history_items = req.history or []
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

        CURRENT USER INPUT: {req.message}
        """

        # Optional Localization Override
        lang_map = {
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
            "ja": "Japanese", "ko": "Korean"
        }
        if getattr(req, 'language', None) and req.language.lower() != "en":
            lang_name = lang_map.get(req.language.lower(), req.language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        # ==========================================
        # STREAMING GENERATOR
        # ==========================================
        async def stream_generator():
            try:
                # If routing occurred, visibly tell the user who is talking
                if routed_agent_name and routed_agent_name != gateway_name:
                    yield f"🤖 *[Routed to: {routed_agent_name}]*\n\n"
                    
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Chat endpoint failed")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ==========================================
# PUBLIC CHAT WIDGET ENDPOINT
# ==========================================

@router.post("/api/widget/chat")
@limiter.limit("25/minute")
async def widget_chat(req: WidgetChatRequest, request: Request):
    """
    Stateless chat endpoint for external websites embedding the chatbot.
    Identical logic to `/chat` but validates allowed domains and logs metrics.
    """
    if not req.chatbot_id:
        raise HTTPException(status_code=400, detail="chatbot_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    req.message = scrub_pii(req.message)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Chatbot Config
        cursor.execute(
            "SELECT c.agent_id, c.settings, c.message_count, a.user_id, c.allowed_domains FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s",
            (req.chatbot_id,),
        )
        chatbot_data = cursor.fetchone()
        if not chatbot_data:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        agent_id, settings, message_count, user_id, allowed_domains = chatbot_data
        settings = settings or {}

        # 2. CORS / Domain Validation
        # Crucial for preventing bad actors from taking the embed script and putting it on their own site,
        # which would drain the original user's quota.
        if allowed_domains and request.headers.get("origin"):
            origin = (
                request.headers.get("origin")
                .replace("http://", "")
                .replace("https://", "")
                .split(":")[0]
            )
            domains = [
                d.strip().replace("http://", "").replace("https://", "").split(":")[0] 
                for d in allowed_domains.split(",") if d.strip()
            ]
            
            allowed = False
            if not domains:
                allowed = True
            else:
                for d in domains:
                    if d == origin:
                        allowed = True
                        break
                    elif d.startswith("*.") and origin.endswith(d[1:]):
                        allowed = True
                        break
                        
            if not allowed:
                raise HTTPException(status_code=403, detail="Domain not allowed")

        # 3. Check Chatbot Message Limit
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
            raise HTTPException(
                status_code=403,
                detail="Monthly widget message limit exceeded. Please upgrade your plan.",
            )

        # 4. Increment Analytics Counters
        cursor.execute(
            "UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s",
            (req.chatbot_id,),
        )
        cursor.execute(
            "INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)",
            (req.chatbot_id,),
        )
        conn.commit()

        # 5. Get the agent config
        cursor.execute(
            "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, is_active FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Underlying Agent not found")

        agent_name, system_prompt, output_format, provider, model, custom_api_key, embed_model, is_active = agent_data
        embed_model = embed_model or "text-embedding-3-small"
        custom_api_key = decrypt_key(custom_api_key)
        
        if not is_active:
            async def offline_stream():
                yield "Sorry, our custom services department is currently offline. Please try again later."
            return StreamingResponse(offline_stream(), media_type="text/plain")

        # 6. Setup LLM
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

        # 7. Fetch RAG Context
        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]

        cursor.execute(
            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
            (req.message, str(query_vector), agent_id),
        )
        best_matches = cursor.fetchall()

        context = "No specific documents found."
        if best_matches:
            context = "\n\n---\n\n".join([decrypt_key(match[0]) or match[0] for match in best_matches])

        # 8. Format Chat History (Stateless)
        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        memory_patch = fetch_temporary_memory_patch(cursor, agent_id)

        # 9. Build Prompt
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

        CURRENT USER INPUT: {req.message}
        """

        lang_map = {
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
            "ja": "Japanese", "ko": "Korean"
        }
        if getattr(req, 'language', None) and req.language.lower() != "en":
            lang_name = lang_map.get(req.language.lower(), req.language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        async def stream_generator():
            try:
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Widget Chat endpoint failed", exc_info=True)
        # CRITICAL FIX: Only roll back if the connection is actually still open.
        # Sometimes streaming responses crash because the user abruptly closes the browser.
        if conn and not conn.closed:
            try:
                conn.rollback()
            except psycopg2.InterfaceError:
                pass 

        return StreamingResponse(
            iter([f"Error: {str(e)}"]),
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ==========================================
# API ACCESS (Programmatic)
# ==========================================

class APIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None

@router.post("/api/v1/chat")
@limiter.limit("25/minute")
async def api_v1_chat(req: APIChatRequest, request: Request, response: Response, x_api_key: str = Header(...)):
    """
    Programmatic access endpoint using custom API Keys.
    Allows developers to integrate RAG agents into their own backend systems 
    (e.g., Slack bots, Discord integrations, custom mobile apps).
    
    Data Flow: Authenticate via Header -> Initialize Session -> Run RAG -> Log History -> Stream Response.
    """
    import uuid
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get chatbot by API key
        cursor.execute(
            "SELECT c.id, c.agent_id, a.user_id FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.api_key = %s",
            (x_api_key,),
        )
        chatbot_data = cursor.fetchone()
        if not chatbot_data:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        chatbot_id, master_agent_id, user_id = chatbot_data

        req.message = scrub_pii(req.message)

        # Session Management: If none provided, create a new one automatically
        session_id = req.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chat_sessions (id, title, agent_id) VALUES (%s, %s, %s)",
                (session_id, req.message[:50], master_agent_id)
            )
        
        # Return the session ID in the header so the developer can track state
        response.headers["X-Session-ID"] = session_id
        
        # Save User Message
        user_msg_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO chat_messages (id, session_id, role, content) VALUES (%s, %s, 'user', %s)",
            (user_msg_id, session_id, req.message)
        )
        conn.commit()

        # Fetch History from Database (Unlike the widget which relies on the frontend)
        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT 10",
            (session_id,)
        )
        history_rows = cursor.fetchall()
        # Exclude the message we just inserted so the LLM doesn't see it twice
        history_items = [{"role": row[0], "content": row[1]} for row in history_rows[:-1]]
        
        # Fetch Master Agent Data
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
            return StreamingResponse(offline_stream(), media_type="text/plain")

        active_agent_id = master_agent_id
        routed_agent_name = None
        gateway_name = agent_name

        # DYNAMIC ROUTING MIDDLEWARE
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

User's Latest Message: {req.message}

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
                            return StreamingResponse(offline_stream(), media_type="text/plain")
                except Exception as e:
                    logger.error(f"Dynamic routing failed: {e}")

        # RAG Logic
        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
        cursor.execute(
            "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
            (req.message, str(query_vector), active_agent_id),
        )
        best_matches = cursor.fetchall()

        # If routed to sub-agent, fallback to query master agent (master_agent_id) documents as well
        if active_agent_id != master_agent_id:
            cursor.execute(
                "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, 5, 0.3)",
                (req.message, str(query_vector), master_agent_id),
            )
            master_matches = cursor.fetchall()
            # Combine, deduplicate, and sort by similarity
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

        CURRENT USER INPUT: {req.message}
        """

        lang_map = {
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "hi": "Hindi", "zh-cn": "Chinese",
            "ja": "Japanese", "ko": "Korean"
        }
        if getattr(req, 'language', None) and req.language.lower() != "en":
            lang_name = lang_map.get(req.language.lower(), req.language)
            prompt += f"\n\nIMPORTANT INSTRUCTION: You MUST reply entirely in {lang_name}! Translate your output to {lang_name} completely."

        # Increment Analytics
        cursor.execute("UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (chatbot_id,))
        cursor.execute("INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,))
        conn.commit()

        # Setup LLM
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
                        
                # Async logging: Save final generated response to DB so the developer has logs
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

        return StreamingResponse(stream_generator(), media_type="text/plain")

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

# ==========================================
# CASCADING DELETION HELPERS
# ==========================================

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """
    Completely wipes an agent. Because of the Multi-Agent architecture, 
    we must recursively delete any sub-agents attached to this agent.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Recursive CTE query to fetch all sub-agents (and their sub-agents)
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
        
        # 2. Hard delete all related data to prevent orphaned rows
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

@router.delete("/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str):
    """Deletes a widget endpoint and all its related analytics logs."""
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
