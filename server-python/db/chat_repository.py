"""
================================================================================
CHAT OPERATIONS AND VECTOR SEARCH DATABASE REPOSITORY LAYER (chat_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module handles runtime chat interactions, vector-based document retrieval
(RAG), rate limit controls, and chatbot widget metrics. It connects the core LLM/agent
orchestration layer with PostgreSQL (utilizing pgvector for hybrid semantic searches).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: Database context manager.
   - `run_in_threadpool`: Asynchronous thread executor for blocking database methods.
   - `uuid` and python typing indicators (`Optional`, `List`, `Dict`).

2. Repository Functions:
   - `fetch_temporary_memory_patch(agent_id)`: Summarizes negative user feedback from previous
     chat sessions to inject as prompt corrections (guardrails).
   - `get_agent_for_chat(agent_id)`: Loads complete configuration settings for an active agent.
   - `get_sub_agents_for_project(project_id)`: Fetches sub-agents linked to a multi-agent project network.
   - `get_agent_routing_info(agent_id)`: Gets name and orchestration parameters for routing.
   - `get_user_chat_limits(user_id)`: Aggregates monthly user message counts to compare with plan limits.
   - `get_documents_hybrid(...)`: Performs a hybrid vector search or direct pgvector cosine similarity match
     to feed relevant context into the agent's prompt context (RAG).
   - `get_chatbot_for_widget(chatbot_id)`: Retrieves widget information, allowed domains, and message counts.
   - `check_widget_limits(user_id)`: Aggregates total message counts across all widget configurations.
   - `log_widget_message(chatbot_id)`: Increments widget hit counters and inserts timestamps.
   - `get_chatbot_by_api_key(...)`: Identifies a chatbot profile by public API key.
   - `create_chat_session(...)` / `insert_chat_message(...)`: Appends session and message logs.
   - `get_session_history(session_id, limit)`: Recovers the past N turns of chat history.
   - `delete_agent(agent_id)`: Recursively determines the agent hierarchy using a CTE, clears vectors,
     documents, chat rooms, and profiles in order.
   - `delete_chatbot(chatbot_id)`: Deletes chatbot profiles and message logging streams.

VECTOR CONCEPTS IN RAG:
- Pgvector Distance Operators: `<=>` represents cosine distance. Cosine similarity is calculated as
  `(1 - (embedding <=> query_vector))`. A lower cosine distance means higher semantic similarity.
- Hybrid Search fallback: If `match_documents_hybrid` fails, it falls back to a query matching
  embeddings of the agent, its parent agent, or peer agents in the same project.
"""

from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
from typing import Optional, List, Dict
from utils.logger import get_db_logger
import uuid

logger = get_db_logger("chat_repository")

async def fetch_temporary_memory_patch(agent_id: str) -> str:
    """
    Finds and compiles recent unresolved user negative feedback for an agent.
    Retired: Always returns an empty string since the feedback system has been removed.
    """
    return ""


async def get_agent_for_chat(agent_id: str):
    """
    Retrieves the full configuration profile of an agent.
    If the agent_id corresponds to a project_id, resolves to its Network Manager agent first.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id FROM agents WHERE project_id = %s AND name LIKE 'Network Manager%%'",
            (agent_id,),
        )
        resolved = await run_in_threadpool(cursor.fetchone)
        target_id = resolved[0] if resolved else agent_id

        await run_in_threadpool(
            cursor.execute,
            "SELECT user_id, name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, project_id, parent_agent_id, is_active, endpoints, code_interpreter_enabled, databases, native_integrations, memory_enabled, use_byok FROM agents WHERE id = %s",
            (target_id,),
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_sub_agents_for_project(project_id: str):
    """
    Retrieves all sub-agents linked to a project network.

    Purpose:
        Used by coordinator/manager agents to discover peers or sub-agents they can delegate tasks to.

    Parameters:
        project_id (str): Unique project identifier.

    Returns:
        list of tuples: A list of sub-agent records.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT id, name, description, endpoints, code_interpreter_enabled, databases, native_integrations FROM agents WHERE project_id = %s", (project_id,))
        return await run_in_threadpool(cursor.fetchall)
        

async def get_agent_routing_info(agent_id: str):
    """
    Retrieves routing and orchestration details for an agent.

    Purpose:
        Similar to get_agent_for_chat, but specifically structured to query parameters required
        to make sub-agent delegation decisions.

    Parameters:
        agent_id (str): Unique database identifier of the agent.

    Returns:
        tuple | None: Routing parameters tuple.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT name, system_prompt, output_format, llm_provider, llm_model, api_key, embedding_model, web_search_enabled, is_active, endpoints, code_interpreter_enabled, databases, native_integrations, memory_enabled, use_byok FROM agents WHERE id = %s",
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_user_chat_limits(user_id: str):
    """
    Computes a user's monthly message volume and queries their plan allowances.

    Purpose:
        Controls rate limits by checking the number of messages sent by the user in the current month
        against the maximum limit defined for their subscription tier.

    Parameters:
        user_id (str): Unique user identifier.

    Returns:
        tuple: (current_msg_count (int), limits (dict))
               - current_msg_count: Count of 'user' messages sent in the current calendar month.
               - limits: User subscription plan constraints retrieved from the billing/subscription setup.

    Side Effects / State Changes:
        - None. Read-only queries.

    Errors / Exceptions:
        - May raise database connection errors.
    """
    from utils import get_user_limits_by_id
    # Fetch the subscription parameters using helper.
    limits = await get_user_limits_by_id(user_id)
    async with get_db_cursor_async(commit=False) as cursor:
        # Count user messages created within the current calendar month.
        # `date_trunc('month', m.created_at)` truncates the timestamp to the first day of the month.
        # We join chat_messages -> chat_sessions -> agents to link back to the user owner.
        await run_in_threadpool(
            cursor.execute,
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
        # Fetch the count from index 0 of the tuple, fallback to 0.
        current_msg_count = (await run_in_threadpool(cursor.fetchone))[0] or 0
        return current_msg_count, limits


async def get_documents_hybrid(message: str, query_vector: str, agent_id: str, limit: int = 5):
    """
    Queries vector-indexed knowledge resources using hybrid search or cosine distance matching.

    Purpose:
        RAG (Retrieval-Augmented Generation) context lookup. Attempts to search documents
        using custom hybrid functions. If the database lacks hybrid search functions, it executes
        a direct cosine distance search on pgvector, matching documents from the target agent
        as well as siblings in the same project or parent agents.

    Parameters:
        message (str): Text prompt (for lexical keywords match in hybrid searches).
        query_vector (str): String representation of the text embedding float vector.
        agent_id (str): Target agent identifier.
        limit (int, optional): Maximum document segments to retrieve. Defaults to 5.

    Returns:
        list of tuples: A list of (content, similarity) tuples containing top matched segments.

    Side Effects / State Changes:
        - None. Read-only operations.

    Errors / Exceptions:
        - Catches general exceptions during hybrid matches to gracefully fall back on pgvector.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        try:
            # Attempt dynamic hybrid search (lexical + vector).
            # match_documents_hybrid is a custom SQL function expected in the PostgreSQL schema.
            # We explicitly cast parameters to matching database types (like `%s::vector` for pgvector).
            await run_in_threadpool(
                cursor.execute,
                "SELECT content, similarity FROM match_documents_hybrid(%s, %s::vector, %s, %s, 0.05)",
                (message, query_vector, agent_id, limit),
            )
            results = await run_in_threadpool(cursor.fetchall)
            if results and len(results) > 0:
                return results
        except Exception:
            # Fall back to standard vector cosine similarity query if hybrid query fails.
            logger.debug("Hybrid search function unavailable, falling back to pgvector cosine distance query")
            pass

        # Robust pgvector direct query fallback.
        # `<=>` is the pgvector Cosine Distance operator. Cosine Similarity is: `1 - cosine_distance`.
        # Cosine similarity evaluates how close two vector directions are, returning values closer to 1.
        # This fallback query checks for documents linked to:
        # 1. The target agent (`a.id = agent_id`).
        # 2. Sibling sub-agents within the same project.
        # 3. The parent agent if this is a sub-agent.
        # Ordered ASC by cosine distance (smallest distance first), up to the limit.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT e.content, (1 - (e.embedding <=> %s::vector)) AS similarity
            FROM document_embeddings e
            JOIN documents d ON e.document_id = d.id
            JOIN agents a ON d.agent_id = a.id
            WHERE (
                a.id = %s 
                OR a.project_id = (SELECT project_id FROM agents WHERE id = %s AND project_id IS NOT NULL)
                OR a.id = (SELECT parent_agent_id FROM agents WHERE id = %s AND parent_agent_id IS NOT NULL)
            )
            ORDER BY e.embedding <=> %s::vector ASC
            LIMIT %s
            """,
            (query_vector, agent_id, agent_id, agent_id, query_vector, limit),
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_chatbot_for_widget(chatbot_id: str):
    """
    Retrieves chatbot settings and access controls for widget rendering.

    Purpose:
        Fetches chatbot configuration metadata, message statistics, owner details,
        and domain CORS restrictions (allowed_domains) when loaded on a web site.

    Parameters:
        chatbot_id (str): Unique UUID of the chatbot widget.

    Returns:
        tuple | None: Chatbot profile tuple, or None if not found.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database connection errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT c.agent_id, c.settings, c.message_count, a.user_id, c.allowed_domains FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s",
            (chatbot_id,),
        )
        return await run_in_threadpool(cursor.fetchone)


async def check_widget_limits(user_id: str):
    """
    Retrieves chatbot message stats across all widgets owned by a user.

    Purpose:
        Ensures message quotas are not exceeded for embedded widgets.

    Parameters:
        user_id (str): Unique database user identifier.

    Returns:
        tuple: (total_widget_msgs (int), limits (dict))
               - total_widget_msgs: Cumulative messages served across all chatbot widgets.
               - limits: Allowed plan tier thresholds.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    from utils import get_user_limits_by_id
    limits = await get_user_limits_by_id(user_id)
    async with get_db_cursor_async(commit=False) as cursor:
        # Sum the message_count column across all chatbots owned by the user.
        # COALESCE returns 0 if the user has no chatbots (sum returns Null).
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(message_count), 0)
            FROM chatbots c
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s
            """,
            (user_id,),
        )
        total_widget_msgs = (await run_in_threadpool(cursor.fetchone))[0] or 0
        return total_widget_msgs, limits


async def log_widget_message(chatbot_id: str):
    """
    Logs widget interaction statistics.

    Purpose:
        Increments the message counter on the chatbot widget row and records a timestamped entry
        in the message logs for time-series aggregation.

    Parameters:
        chatbot_id (str): The unique identifier of the chatbot.

    Returns:
        None.

    Side Effects / State Changes:
        - Increments message_count in `chatbots`.
        - Inserts an entry in `widget_message_logs`.
        - Commits both changes in a transaction.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Increment hit counter by 1.
        await run_in_threadpool(cursor.execute, "UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (chatbot_id,))
        # Write analytics log entry (created_at automatically set by DB default constraint).
        await run_in_threadpool(cursor.execute, "INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (chatbot_id,))


async def get_chatbot_by_api_key(x_api_key: str):
    """
    Looks up chatbot metadata using a public API key.

    Purpose:
        Authorizes widget backend interactions using the provided header API key.

    Parameters:
        x_api_key (str): The API key string.

    Returns:
        tuple | None: Returns (id, agent_id, user_id) if found, or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT c.id, c.agent_id, a.user_id FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.api_key = %s",
            (x_api_key,),
        )
        return await run_in_threadpool(cursor.fetchone)


async def create_chat_session(session_id: str, title: str, agent_id: str):
    """
    Creates a new chat session entry.

    Purpose:
        Saves a session placeholder. Typically triggered by external integrations or widgets.

    Parameters:
        session_id (str): The unique identifier to assign to the session.
        title (str): Title description of the conversation.
        agent_id (str): Target agent UUID.

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts a row in the `chat_sessions` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions (e.g. duplicate key).
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO chat_sessions (id, title, agent_id) VALUES (%s, %s, %s)",
            (session_id, title, agent_id)
        )
    logger.debug(f"Chat session created: session_id={session_id}, agent_id={agent_id}")


async def insert_chat_message(msg_id: str, session_id: str, role: str, content: str):
    """
    Inserts a message record with a predefined message ID.

    Purpose:
        Saves a chat log entry. Allows specify an explicit ID (e.g., matching a client-side generated UUID).

    Parameters:
        msg_id (str): Explicit message UUID.
        session_id (str): Associated session UUID.
        role (str): Sender role (e.g., 'user', 'assistant').
        content (str): Text content.

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts a row in `chat_messages`.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    from utils.data_vault import secure_pack
    packed_content = secure_pack(content)
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO chat_messages (id, session_id, role, content) VALUES (%s, %s, %s, %s)",
            (msg_id, session_id, role, packed_content)
        )


async def get_session_history(session_id: str, limit: int = 10):
    """
    Recovers the history of conversation messages for a session.

    Purpose:
        Fetches the previous N turns of conversation to load as history in the LLM prompt.

    Parameters:
        session_id (str): Unique session identifier.
        limit (int, optional): The number of recent messages to return. Defaults to 10.

    Returns:
        list of tuples: A list of (role, content) message records, ordered chronologically.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC LIMIT %s",
            (session_id, limit)
        )
        rows = await run_in_threadpool(cursor.fetchall)
        
        from utils.data_vault import secure_unpack
        unpacked_rows = []
        for role, content in rows:
            unpacked_rows.append((role, secure_unpack(content)))
            
        return unpacked_rows


async def delete_agent(agent_id: str):
    """
    Deletes an agent profile and recursively deletes any sub-agents.

    Purpose:
        Wipes out an agent profile. Since agents can have child agents (hierarchical setup),
        this function uses a PostgreSQL Recursive Common Table Expression (CTE) to discover all
        descendant sub-agents first. It then manually iterates over each ID to clear out documents,
        embeddings, sessions, chats, and widgets in a correct transaction sequence before deleting
        the core agent records to avoid foreign key violations.

    Parameters:
        agent_id (str): The unique database identifier of the agent.

    Returns:
        int: Total number of agents deleted (including descendants).

    Side Effects / State Changes:
        - Wipes rows across vector embeddings, documents, chats, widget logs, and agents tables.
        - Commits modifications to the database (commit=True).

    Errors / Exceptions:
        - May raise database constraint violations if some foreign keys are not handled properly.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Discover all sub-agents in the tree using a Recursive CTE query.
        # The base SELECT queries the parent agent_id.
        # The recursive UNION query joins agents to search for records where parent_agent_id matches
        # the current tree nodes.
        await run_in_threadpool(
            cursor.execute,
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
        # Fetch the complete list of IDs in the tree.
        agent_ids_to_delete = [row[0] for row in (await run_in_threadpool(cursor.fetchall))]

        # If the query result is empty, exit early.
        if not agent_ids_to_delete:
            logger.debug(f"No agents found for deletion cascade from agent_id={agent_id}")
            return 0
            
        # Step 2: Manually loop through each agent ID to clear out its downstream resources in order.
        for aid in agent_ids_to_delete:
            # Wipes document vector embeddings.
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM document_embeddings
                WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
                """, (aid,)
            )
            # Wipes document metadata.
            await run_in_threadpool(cursor.execute, "DELETE FROM documents WHERE agent_id = %s", (aid,))
            # Wipes langgraph checkpoints & writes.
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM langgraph_checkpoints
                WHERE thread_id IN (SELECT id::text FROM chat_sessions WHERE agent_id = %s)
                """, (aid,)
            )
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM langgraph_writes
                WHERE thread_id IN (SELECT id::text FROM chat_sessions WHERE agent_id = %s)
                """, (aid,)
            )
            # Wipes chat message logs.
            await run_in_threadpool(
                cursor.execute,
                """
                DELETE FROM chat_messages 
                WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = %s)
                """, (aid,)
            )
            # Wipes chat sessions.
            await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id = %s", (aid,))
            # Wipes chatbot widgets.
            await run_in_threadpool(cursor.execute, "DELETE FROM chatbots WHERE agent_id = %s", (aid,))
            
        # Step 3: Delete the agents themselves.
        # We construct a dynamic comma-separated list of placeholder values (%s) to match the count of IDs.
        ids_tuple = tuple(agent_ids_to_delete)
        placeholders = ','.join(['%s'] * len(ids_tuple))
        await run_in_threadpool(cursor.execute, f"DELETE FROM agents WHERE id IN ({placeholders})", ids_tuple)
        
        logger.info(f"Agent cascade deletion completed: {len(agent_ids_to_delete)} agents removed from agent_id={agent_id}")
        # Return the count of agents that were deleted.
        return len(agent_ids_to_delete)


async def delete_chatbot(chatbot_id: str):
    """
    Deletes a chatbot widget configuration and its interaction logs.

    Purpose:
        Removes a chatbot widget and deletes its associated telemetry logs.

    Parameters:
        chatbot_id (str): Unique UUID of the chatbot.

    Returns:
        None.

    Side Effects / State Changes:
        - Deletes rows in `widget_message_logs` and `chatbots`.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Delete dependencies first to satisfy database foreign keys constraints.
        await run_in_threadpool(cursor.execute, "DELETE FROM widget_message_logs WHERE chatbot_id = %s", (chatbot_id,))
        # Delete the core chatbot configuration row.
        await run_in_threadpool(cursor.execute, "DELETE FROM chatbots WHERE id = %s", (chatbot_id,))


async def clear_agent_conversation_history(agent_id: str):
    """
    Deletes all chat messages and sessions associated with the agent to clear conversation memory.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM langgraph_checkpoints WHERE thread_id IN (SELECT id::text FROM chat_sessions WHERE agent_id = %s);",
            (agent_id,)
        )
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM langgraph_writes WHERE thread_id IN (SELECT id::text FROM chat_sessions WHERE agent_id = %s);",
            (agent_id,)
        )
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = %s);",
            (agent_id,)
        )
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM chat_sessions WHERE agent_id = %s;",
            (agent_id,)
        )
        return True

