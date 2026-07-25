"""
================================================================================
CHAT HISTORY DATABASE REPOSITORY LAYER (chat_history_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database operations for chat sessions and individual chat
messages. It provides CRUD functionality for the `chat_sessions` and `chat_messages`
tables, keeping track of conversation history between users and AI agents.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: The custom database context manager (from `database.py`).
   - `run_in_threadpool`: FastAPI utility used to run synchronous database operations in
     separate thread pool threads to prevent blocking the async loop.
   - `uuid`: Python's built-in UUID generator, used to assign globally unique IDs to
     newly created chat sessions.

2. Repository Functions:
   - `get_chat_sessions(...)`: Returns all chat sessions in a workspace, ordered by
     pinned status and updated timestamps.
   - `create_chat_session(...)`: Generates a new session ID and saves a session record.
   - `update_chat_session(...)`: Updates a session's title or pinned status, building the
     SQL statement dynamically to update only provided fields.
   - `delete_chat_session(...)`: Deletes a session and its cascading items.
   - `clear_agent_chat_history(...)`: Deletes all sessions associated with a specific agent.
   - `get_chat_messages(...)`: Fetches all messages within a specific session, sorted by time.
   - `create_chat_message(...)`: Inserts a new message and updates the parent session's
     `updated_at` timestamp in the same transaction block.

CONCURRENCY & DB MOTIVATION:
- Asynchronous database operations: Blocking database commands are delegated to thread pools via
  `run_in_threadpool`.
- Clean updates: `timezone('utc'::text, now())` is used to store standardized UTC timestamps
  directly at the database level.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import uuid

async def get_chat_sessions(workspace_id: str, user_id: str):
    """
    Retrieves all chat sessions for a specific user and workspace.

    Purpose:
        Fetches the user's chat history for display in the sidebar. Includes the linked
        agent's name for clarity and orders them by pinned status (highest priority)
        and then by update date.

    Parameters:
        workspace_id (str): The ID of the workspace containing the chat sessions.
        user_id (str): The unique database identifier of the user who owns the sessions.

    Returns:
        list of tuples: A list of session records. Each record contains:
            - id (str): Session UUID.
            - agent_id (str): Associated agent's UUID.
            - title (str): The title/header of the conversation.
            - pinned (bool): True if the session is pinned to the top.
            - created_at (datetime): Creation timestamp.
            - updated_at (datetime): Last active timestamp.
            - agent_name (str | None): Name of the agent (retrieved via LEFT JOIN).

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection in a read-only transaction (commit=False).
    async with get_db_cursor_async(commit=False) as cursor:
        # Perform query in a thread pool. We perform a LEFT JOIN from `chat_sessions`
        # to `agents` to query the agent name. Even if the agent was deleted, the
        # session details will still return with a Null agent name.
        # Order is DESC for pinned (True comes before False) and updated_at DESC (newest first).
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT s.id, s.agent_id, s.title, s.pinned, s.created_at, s.updated_at, a.name as agent_name
            FROM chat_sessions s
            LEFT JOIN agents a ON s.agent_id = a.id
            WHERE s.workspace_id = %s AND s.user_id = %s
            ORDER BY s.pinned DESC, s.updated_at DESC
            """,
            (workspace_id, user_id)
        )
        # Fetch and return all matching rows.
        return await run_in_threadpool(cursor.fetchall)


async def create_chat_session(user_id: str, workspace_id: str, agent_id: str, title: str):
    """
    Creates a new chat session in the database.

    Purpose:
        Generates a new chat history thread when a user starts talking to an agent.
        Generates a random UUID version 4 to serve as the session ID.

    Parameters:
        user_id (str): The ID of the user starting the session.
        workspace_id (str): The ID of the workspace.
        agent_id (str): The ID of the agent associated with the session.
        title (str): Initial title description for the conversation.

    Returns:
        tuple: The newly created chat session row containing id, agent_id, title, pinned,
               created_at, and updated_at.

    Side Effects / State Changes:
        - Writes a new row to the `chat_sessions` table.
        - Commits change to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    # Generate a unique session ID. UUID version 4 guarantees globality and unpredictability.
    session_id = str(uuid.uuid4())
    # Open database connection in a write-only transaction (commit=True).
    async with get_db_cursor_async(commit=True) as cursor:
        # Execute INSERT statement.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chat_sessions (id, user_id, workspace_id, agent_id, title)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, agent_id, title, pinned, created_at, updated_at;
            """,
            (session_id, user_id, workspace_id, agent_id, title)
        )
        # Fetch and return the single inserted row.
        return await run_in_threadpool(cursor.fetchone)


async def update_chat_session(session_id: str, title: str, pinned: bool):
    """
    Updates mutable properties of a chat session.

    Purpose:
        Modifies a session's title or pin status. Updates the `updated_at` column to the current UTC time.

    Parameters:
        session_id (str): The unique ID of the session to update.
        title (str | None): The new title value, or None if the title should not change.
        pinned (bool | None): The new pin status, or None if pinned should not change.

    Returns:
        bool: True if an update query was executed, False if no changes were specified.

    Side Effects / State Changes:
        - Updates fields in the `chat_sessions` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        updates = []
        values = []
        
        # Build update clauses dynamically depending on which parameters were supplied.
        if title is not None:
            updates.append("title = %s")
            values.append(title)
        if pinned is not None:
            updates.append("pinned = %s")
            values.append(pinned)
            
        # If both title and pinned parameters are None, exit early.
        if not updates:
            return False
            
        # Add timezone-aware UTC updated_at column to database record.
        # timezone('utc'::text, now()) fetches the server time, normalizes to UTC time zone, and casts.
        updates.append("updated_at = timezone('utc'::text, now())")
        # Add session_id to the query binding parameters tuple.
        values.append(session_id)
        
        # Format SQL query statement, joining updates list with commas.
        query = f"UPDATE chat_sessions SET {', '.join(updates)} WHERE id = %s"
        # Execute query.
        await run_in_threadpool(cursor.execute, query, tuple(values))
        return True


async def delete_chat_session(session_id: str):
    """
    Deletes a specific chat session.

    Purpose:
        Permanently deletes a conversation session. Downstream messages are cascade-deleted
        automatically if foreign keys are configured with CASCADE deletion rules in PostgreSQL.

    Parameters:
        session_id (str): The UUID of the session to delete.

    Returns:
        None.

    Side Effects / State Changes:
        - Deletes rows in `chat_sessions` (and cascade dependencies).
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE id = %s", (session_id,))


async def clear_agent_chat_history(agent_id: str):
    """
    Deletes all chat sessions associated with a specific agent.

    Purpose:
        Wipes chat history for an agent. Used when an agent is reset or deleted.

    Parameters:
        agent_id (str): Unique identifier of the agent.

    Returns:
        None.

    Side Effects / State Changes:
        - Deletes multiple rows in `chat_sessions`.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(cursor.execute, "DELETE FROM chat_sessions WHERE agent_id = %s", (agent_id,))


async def get_chat_messages(session_id: str):
    """
    Retrieves all messages for a specific chat session.

    Purpose:
        Fetches the complete message thread history for a session to render inside the chat window.

    Parameters:
        session_id (str): Unique database session identifier.

    Returns:
        list of tuples: A list of messages in the session, sorted by creation date (oldest first).

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection in a read-only transaction (commit=False).
    async with get_db_cursor_async(commit=False) as cursor:
        # Execute SELECT query in a thread pool. Sorted by created_at ASC to show chat timeline.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, role, content, latency, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def create_chat_message(session_id: str, role: str, content: str, latency: float):
    """
    Creates a new chat message and updates the parent session's update time.

    Purpose:
        Inserts a message record into `chat_messages` and updates `updated_at` on the
        corresponding parent `chat_sessions` row to keep it ordered correctly in sidebar lists.

    Parameters:
        session_id (str): The ID of the session the message belongs to.
        role (str): The role of the sender (e.g. 'user', 'assistant', 'system').
        content (str): The body text of the message.
        latency (float): The time taken by the LLM (in seconds) to respond.

    Returns:
        tuple: The created message row tuple containing id, role, content, latency, and created_at.

    Side Effects / State Changes:
        - Inserts a row in the `chat_messages` table.
        - Modifies a row in the `chat_sessions` table.
        - Commits both modifications in a single transaction.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    # Open database connection with commit=True.
    async with get_db_cursor_async(commit=True) as cursor:
        # Insert the message record and return values.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO chat_messages (session_id, role, content, latency)
            VALUES (%s, %s, %s, %s)
            RETURNING id, role, content, latency, created_at;
            """,
            (session_id, role, content, latency)
        )
        # Fetch the returning message record values.
        row = await run_in_threadpool(cursor.fetchone)
        
        # Update the parent session's last activity timestamp to the current UTC time.
        # This brings the active chat session back to the top of the sidebar.
        await run_in_threadpool(
            cursor.execute,
            "UPDATE chat_sessions SET updated_at = timezone('utc'::text, now()) WHERE id = %s",
            (session_id,)
        )
        return row

