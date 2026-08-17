"""
================================================================================
CHATBOT WIDGET DATABASE REPOSITORY LAYER (chatbot_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) / repository layer for configuring
deployable chatbot widgets. Chatbots are client-facing UI panels that wrap around
an underlying agent. This file handles retrieving, creating, and updating chatbot settings.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: The custom database context manager.
   - `run_in_threadpool`: FastAPI utility that runs blocking database calls in a
     background thread pool to keep the event loop free.
   - `json`: Python standard library for JSON encoding.

2. Repository Functions:
   - `get_chatbots(workspace_id)`: Retrieves all chatbot widgets configured for agents
     belonging to a specific workspace.
   - `get_chatbot_by_id(chatbot_id)`: Fetches a single chatbot configuration profile.
   - `create_chatbot(...)`: Inserts a new chatbot widget configuration, serializing its
     settings dictionary into a JSONB database field.
   - `update_chatbot(...)`: Performs a dynamic SQL UPDATE query based on custom-constructed
     sets of whitelisted SQL clauses.

DATABASE SCHEMAS AND JSONB:
- The `settings` column on the `chatbots` table uses PostgreSQL's JSONB format. We convert
  Python dictionaries to JSON strings using `json.dumps(settings)` and cast them using
  `%s::jsonb` to optimize query indexes and retrieval.
"""

from core.database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import json

async def get_chatbots(workspace_id: str):
    """
    Retrieves all chatbot widget configurations belonging to a specific workspace.

    Purpose:
        Fetches chatbot widgets to list them on the user's dashboard. Performs an INNER JOIN
        with the agents table to restrict the results to agents under the target workspace.

    Parameters:
        workspace_id (str): The unique workspace UUID.

    Returns:
        list of tuples: A list of chatbot record tuples, sorted newest first.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database connection errors.
    """
    # Open database connection in a read-only transaction (commit=False).
    async with get_db_cursor_async(commit=False) as cursor:
        # Execute query in a thread pool.
        # We query chatbot fields (id, name, settings, message_count, allowed_domains, etc.)
        # and join with agents on c.agent_id = a.id to filter by a.workspace_id.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE a.workspace_id = %s
            ORDER BY c.created_at DESC
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_chatbot_by_id(chatbot_id: str):
    """
    Retrieves a single chatbot widget configuration profile by its ID.

    Purpose:
        Fetches widget configuration and associated agent metadata for a specific chatbot.

    Parameters:
        chatbot_id (str): The unique database UUID of the chatbot.

    Returns:
        tuple | None: The matching chatbot row tuple, or None if not found.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.id, c.agent_id, c.name, c.settings, c.message_count, c.api_key, c.allowed_domains, c.created_at,
                   a.workspace_id, a.name as agent_name
            FROM chatbots c
            INNER JOIN agents a ON c.agent_id = a.id
            WHERE c.id = %s
            """,
            (chatbot_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def create_chatbot(agent_id: str, name: str, settings: dict):
    """
    Registers a new chatbot widget configuration in the database.

    Purpose:
        Creates a deployable widget profile, serializing its settings into a JSONB column.

    Parameters:
        agent_id (str): The UUID of the agent this widget wraps.
        name (str): The display name of the chatbot widget.
        settings (dict): A dictionary of visual and functional configuration properties.

    Returns:
        tuple: The newly created chatbot configuration row.

    Side Effects / State Changes:
        - Inserts a new row into the `chatbots` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Serialize the settings dictionary into a standard JSON string.
    settings_json = json.dumps(settings)
    # Open database connection with commit=True since we are modifying DB state.
    async with get_db_cursor_async(commit=True) as cursor:
        # Execute query.
        # We cast settings parameter using `%s::jsonb` to ensure PostgreSQL correctly stores it as a JSONB data type.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chatbots (agent_id, name, settings)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at
            """,
            (agent_id, name, settings_json)
        )
        return await run_in_threadpool(cursor.fetchone)


async def update_chatbot(chatbot_id: str, set_clauses: list, values: list):
    """
    Performs a dynamic SQL update on a chatbot widget's records.

    Purpose:
        Executes updates based on whitelisted clauses and parameters compiled by routers.

    Parameters:
        chatbot_id (str): The UUID of the chatbot to update.
        set_clauses (list of str): A list of update syntax statements (e.g. `["name = %s", "settings = %s::jsonb"]`).
        values (list): A list of values associated with the update clauses.

    Returns:
        tuple | None: The updated chatbot row tuple, or None.

    Side Effects / State Changes:
        - Updates fields in the `chatbots` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Format the query string, joining set clauses with commas.
        # The chatbot ID is bound to the WHERE clause at the end of the query values array.
        query = f"UPDATE chatbots SET {', '.join(set_clauses)} WHERE id = %s RETURNING id, agent_id, name, settings, message_count, api_key, allowed_domains, created_at;"
        # Execute the update query inside the thread pool, passing the values list as a tuple.
        await run_in_threadpool(cursor.execute, query, tuple(values))
        return await run_in_threadpool(cursor.fetchone)

