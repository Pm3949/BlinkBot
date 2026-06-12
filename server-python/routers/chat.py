import json
import logging
import os
import psycopg2
from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import StreamingResponse

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from database import get_db_connection
from schemas import ChatRequest, WidgetChatRequest
from core.dependencies import rag_engine
from utils import get_user_limits

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """Stream an LLM response grounded in the uploaded documents."""
    if not req.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s",
            (req.agent_id,),
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        (
            user_id,
            agent_name,
            system_prompt,
            provider,
            model,
            custom_api_key,
            embed_model,
        ) = agent_data
        embed_model = embed_model or "text-embedding-3-small"

        # Check Message Limits
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

        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]

        cursor.execute(
            """
            SELECT de.content, de.embedding::text
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = %s
            ORDER BY de.embedding <=> %s::vector
            LIMIT 100
        """,
            (req.agent_id, str(query_vector)),
        )
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [
                json.loads(row[1]) if isinstance(row[1], str) else row[1]
                for row in rows
            ]

            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=3,
            )

            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        prompt = f"""{system_prompt}
        You are a strict, professional AI assistant grounded ONLY in the provided documents.

        CRITICAL RULES:
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {req.message}
        """

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


@router.post("/api/widget/chat")
async def widget_chat(req: WidgetChatRequest, request: Request):
    """Stateless chat endpoint for external widgets."""
    if not req.chatbot_id:
        raise HTTPException(status_code=400, detail="chatbot_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Get the agent_id linked to this chatbot
        cursor.execute(
            "SELECT c.agent_id, c.settings, c.message_count, a.user_id, c.allowed_domains FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s",
            (req.chatbot_id,),
        )
        chatbot_data = cursor.fetchone()
        if not chatbot_data:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        agent_id, settings, message_count, user_id, allowed_domains = chatbot_data
        settings = settings or {}

        # Optional Origin Validation
        if allowed_domains and request.headers.get("origin"):
            origin = (
                request.headers.get("origin")
                .replace("http://", "")
                .replace("https://", "")
                .split(":")[0]
            )
            domains = [d.strip() for d in allowed_domains.split(",") if d.strip()]
            if domains and origin not in domains:
                raise HTTPException(status_code=403, detail="Domain not allowed")

        # Check Chatbot Message Limit
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

        # Increment widget message count and log it
        cursor.execute(
            "UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s",
            (req.chatbot_id,),
        )
        cursor.execute(
            "INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)",
            (req.chatbot_id,),
        )
        conn.commit()

        # 2. Get the agent config
        cursor.execute(
            "SELECT name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Underlying Agent not found")

        agent_name, system_prompt, provider, model, custom_api_key, embed_model = (
            agent_data
        )
        embed_model = embed_model or "text-embedding-3-small"

        # 3. Setup LLM
        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        # 4. Fetch RAG Context
        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]

        cursor.execute(
            """
            SELECT de.content, de.embedding::text
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = %s
            ORDER BY de.embedding <=> %s::vector
            LIMIT 100
        """,
            (agent_id, str(query_vector)),
        )
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [
                json.loads(row[1]) if isinstance(row[1], str) else row[1]
                for row in rows
            ]

            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=3,
            )

            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        # 5. Format Chat History (Stateless)
        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        # 6. Build Prompt
        prompt = f"""{system_prompt}
        You are a strict, professional AI assistant grounded ONLY in the provided documents.

        CRITICAL RULES:
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {req.message}
        """

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
        # CRITICAL FIX: Only roll back if the connection is actually still open
        if conn and not conn.closed:
            try:
                conn.rollback()
            except psycopg2.InterfaceError:
                pass  # Connection was already closed by the host anyway

        return StreamingResponse(
            iter([f"Error: {str(e)}"]),
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


class APIChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


@router.post("/api/v1/chat")
async def api_v1_chat(req: APIChatRequest, x_api_key: str = Header(...)):
    """Programmatic access endpoint using API Key."""
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

        chatbot_id, agent_id, user_id = chatbot_data

        # We can reuse the logic by forwarding to the same internal function or copy-pasting for simplicity.
        # Since it's streaming, let's reuse the internal generator from `widget_chat`.
        # To avoid duplicating 100 lines, we'll construct a WidgetChatRequest and call widget_chat logic directly.
        # But wait, widget_chat returns StreamingResponse. We can just call it.
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # We don't have request object for widget_chat, let's just duplicate the streaming logic for clarity
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check Limits
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
                status_code=403, detail="Monthly message limit exceeded"
            )

        cursor.execute(
            "UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s",
            (chatbot_id,),
        )
        cursor.execute(
            "INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,)
        )
        conn.commit()

        cursor.execute(
            "SELECT name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s",
            (agent_id,),
        )
        agent_data = cursor.fetchone()
        agent_name, system_prompt, provider, model, custom_api_key, embed_model = (
            agent_data
        )
        embed_model = embed_model or "text-embedding-3-small"

        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
        cursor.execute(
            "SELECT de.content, de.embedding::text FROM document_embeddings de JOIN documents d ON de.document_id = d.id WHERE d.agent_id = %s ORDER BY de.embedding <=> %s::vector LIMIT 100",
            (agent_id, str(query_vector)),
        )
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [
                json.loads(row[1]) if isinstance(row[1], str) else row[1]
                for row in rows
            ]
            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=3,
            )
            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        prompt = f"{system_prompt}\n\nCONTEXT DOCUMENTS:\n{context}\n\nPREVIOUS CHAT HISTORY:\n{history_text}\n\nCURRENT USER INPUT: {req.message}"

        async def stream_generator():
            try:
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                yield f"\n\n⚠️ Error: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")
    except Exception as e:
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


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM document_embeddings
            WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
        """,
            (agent_id,),
        )
        cursor.execute("DELETE FROM documents WHERE agent_id = %s", (agent_id,))
        cursor.execute(
            """
            DELETE FROM chat_messages 
            WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = %s)
        """,
            (agent_id,),
        )
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id = %s", (agent_id,))
        cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        conn.commit()
        return {"message": "Agent and all its memory completely wiped!"}
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
