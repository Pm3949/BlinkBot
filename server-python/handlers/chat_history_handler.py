"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the business logic coordinator for managing chat histories, 
messages, and conversation sessions in RAGMate.

From top to bottom, the file performs the following tasks:
1. Imports: Loads FastAPI exception modules and database wrappers from the 
   chat_history_repository.
2. Logging: Initializes a department logger specifically scoped to "agent" interactions
   to audit message queries and purging actions.
3. Session Management Handlers:
   - `handle_get_chat_sessions`: Fetches and formats the list of all chat sessions 
     for a user in a given workspace, converting database timestamp values to ISO strings.
   - `handle_create_chat_session`: Inserts a new chat session entry into database tables.
   - `handle_update_chat_session`: Alters properties of a session (like renaming titles or pinning them).
   - `handle_delete_chat_session`: Safely wipes out a single chat session.
4. Purge Handlers:
   - `handle_clear_agent_chat_history`: Purges all chat records and conversations linked to an agent.
5. Message Level Handlers:
   - `handle_get_chat_messages`: Fetches individual messages within a session, returning roles and metrics.
   - `handle_create_chat_message`: Inserts a single message (user or assistant role) along with latency metrics.
"""

from fastapi import HTTPException  # Import web exceptions to raise clean HTTP error codes
from db import chat_history_repository  # Database access layer for chat history tables

# Logging utilities
from utils.logger import get_department_logger

# Scope a department logger to "agent" context to record chat history events
logger = get_department_logger("agent")


async def handle_get_chat_sessions(workspace_id: str, user_id: str):
    """
    Retrieves the list of all chat sessions for a specific user within a workspace.
    Fleshes out raw database rows and formats them into serialized dictionaries.

    Parameters:
        workspace_id (str): The unique database UUID of the active workspace.
        user_id (str): The unique database UUID of the target user.

    Returns:
        list: A list of session dictionaries, containing:
            - 'id': Session UUID.
            - 'agent_id': Linked agent UUID.
            - 'title': Session label string.
            - 'pinned': Boolean flag if pinned to top.
            - 'created_at': ISO-formatted date string.
            - 'updated_at': ISO-formatted date string.
            - 'agent_name': Name of the agent (falls back to "General").

    Exceptions Raised:
        HTTPException(500): Raised if any SQL query fails.
    """
    # Log information indicating retrieval is initiated
    logger.info(f"Retrieving chat sessions list for workspace ID: {workspace_id} (User ID: {user_id})")
    try:
        # Query database row collections matching user and workspace
        logger.debug("Executing chat sessions fetch query in database...")
        rows = await chat_history_repository.get_chat_sessions(workspace_id, user_id)
        logger.debug(f"Retrieved {len(rows)} chat session records.")
        
        # Loop through rows and format timestamps to ISO 8601 strings
        sessions = []
        for row in rows:
            sessions.append({
                "id": row[0],                                                # Session UUID
                "agent_id": row[1],                                          # Linked Agent ID
                "title": row[2],                                             # Custom session title
                "pinned": row[3],                                            # Pinned state (boolean flag)
                "created_at": row[4].isoformat() if row[4] else None,        # Creation date ISO format string
                "updated_at": row[5].isoformat() if row[5] else None,        # Last updated date ISO format string
                "agent_name": row[6] or "General"                            # Name of agent, fallback to default "General"
            })
            
        # Log successful list formatting
        logger.info(f"Successfully processed and returned {len(sessions)} chat sessions.")
        return sessions
    except Exception as e:
        # Catch errors, log, and raise a 500 error
        logger.error(f"Error fetching chat sessions for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chat sessions")


async def handle_create_chat_session(payload: dict):
    """
    Registers a new chat conversation session in the database.

    Parameters:
        payload (dict): A dictionary payload containing:
            - 'user_id' (str): Creator's User UUID.
            - 'workspace_id' (str): Target Workspace UUID.
            - 'agent_id' (str): Target AI Agent UUID.
            - 'title' (str, optional): Custom title for the session (default is 'New chat').

    Returns:
        dict: A dictionary structure of the newly registered session details.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database writes fail.
    """
    # Log session creation arguments
    logger.info(f"Creating a new chat session. Workspace ID: {payload.get('workspace_id')}")
    try:
        # Call repository method to insert record into database table
        logger.debug("Executing database creation query in chat_history_repository...")
        row = await chat_history_repository.create_chat_session(
            payload.get("user_id"),
            payload.get("workspace_id"),
            payload.get("agent_id"),
            payload.get("title", "New chat")  # Fallback title if none provided
        )
        
        # Log successful database write
        logger.info(f"Chat session successfully created. ID: {row[0]}")
        return {
            "id": row[0],
            "agent_id": row[1],
            "title": row[2],
            "pinned": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None
        }
    except Exception as e:
        # Catch unexpected errors
        logger.error(f"Error creating chat session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chat session")


async def handle_update_chat_session(session_id: str, payload: dict):
    """
    Updates the title or pinned status of a chat session.

    Parameters:
        session_id (str): The unique database UUID identifying the target session.
        payload (dict): A dictionary payload containing:
            - 'title' (str, optional): New title for the session.
            - 'pinned' (bool, optional): Pinned status flag.

    Returns:
        dict: A status confirmation message dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if SQL update transaction crashes.
    """
    # Log update attributes
    logger.info(f"Updating chat session ID: {session_id} (Title: '{payload.get('title')}', Pinned: {payload.get('pinned')})")
    try:
        # Call database repository update scripts
        logger.debug("Executing database update query in chat_history_repository...")
        updated = await chat_history_repository.update_chat_session(
            session_id,
            payload.get("title"),
            payload.get("pinned")
        )
            
        # Check if the database did not affect any rows (implies key mismatch or no change)
        if not updated:
            logger.warning(f"No updates matched or no parameters changed for session ID: {session_id}")
            return {"message": "No updates provided"}
            
        # Log success and return
        logger.info(f"Chat session ID {session_id} successfully updated.")
        return {"message": "Chat session updated"}
    except Exception as e:
        logger.error(f"Error updating chat session ID {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chat session")


async def handle_delete_chat_session(session_id: str):
    """
    Permanently deletes a chat session and all messages contained within it.

    Parameters:
        session_id (str): The database UUID of the target session to remove.

    Returns:
        dict: A confirmation dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if SQL deletion script crashes.
    """
    logger.info(f"Deleting chat session ID: {session_id}")
    try:
        # Execute database delete script
        logger.debug("Executing database delete query in chat_history_repository...")
        await chat_history_repository.delete_chat_session(session_id)
        
        # Log deletion success
        logger.info(f"Chat session ID {session_id} successfully deleted.")
        return {"message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session ID {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete chat session")


async def handle_clear_agent_chat_history(agent_id: str):
    """
    Deletes all historical conversation messages and sessions linked to a specific agent ID.
    Used for troubleshooting or data scrubbing compliance.

    Parameters:
        agent_id (str): The database UUID of the agent.

    Returns:
        dict: A status confirmation message payload.

    Exceptions Raised:
        HTTPException(500): Raised if database purge operations crash.
    """
    logger.info(f"Scrubbing/clearing chat history for agent ID: {agent_id}")
    try:
        # Call purge methods in database repository
        logger.debug("Executing database purge query in chat_history_repository...")
        await chat_history_repository.clear_agent_chat_history(agent_id)
        
        # Log scrub success
        logger.info(f"All chat history for agent ID {agent_id} successfully scrubbed.")
        return {"message": "All chat history for this agent has been scrubbed"}
    except Exception as e:
        logger.error(f"Error clearing agent chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


async def handle_get_chat_messages(session_id: str):
    """
    Retrieves all messages associated with a chat session.

    Parameters:
        session_id (str): The unique database UUID identifying the session.

    Returns:
        list: A list of messages dictionaries sorted chronologically, containing:
            - 'id': Message UUID.
            - 'role': Sender role ('user' or 'assistant').
            - 'content': Plain text content of the message.
            - 'latency': Generation latency in milliseconds (if assistant).
            - 'created_at': ISO-formatted date string.

    Exceptions Raised:
        HTTPException(500): Raised if SQL database queries fail.
    """
    logger.info(f"Retrieving messages list for chat session: {session_id}")
    try:
        # Pull raw rows
        logger.debug("Executing chat messages fetch query...")
        rows = await chat_history_repository.get_chat_messages(session_id)
        logger.debug(f"Retrieved {len(rows)} message records.")
        
        # Map raw database tuples to structured dictionary elements
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],                                                # Message ID
                "role": row[1],                                              # Role ('user' or 'assistant')
                "content": row[2],                                           # Text body message content
                "latency": row[3],                                           # Model processing latency in MS
                "created_at": row[4].isoformat() if row[4] else None         # ISO-formatted registration date
            })
            
        # Log successful completion and count
        logger.info(f"Successfully processed {len(messages)} messages.")
        return messages
    except Exception as e:
        logger.error(f"Error fetching messages for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chat messages")


async def handle_create_chat_message(payload: dict):
    """
    Creates and records a single message entry in a chat session.

    Parameters:
        payload (dict): A dictionary payload containing:
            - 'session_id' (str): The target conversation session UUID.
            - 'role' (str): Sender identity ('user' or 'assistant').
            - 'content' (str): Text body of message.
            - 'latency' (float, optional): Processing latency metrics.

    Returns:
        dict: A dictionary structure of the newly registered message.

    Exceptions Raised:
        HTTPException(500): Raised if database write fails.
    """
    # Log creation parameters
    logger.info(f"Creating a new chat message entry. Session ID: {payload.get('session_id')} (Role: {payload.get('role')})")
    try:
        # Call repository method to insert record into the DB
        logger.debug("Executing message insertion query...")
        row = await chat_history_repository.create_chat_message(
            payload.get("session_id"),
            payload.get("role"),
            payload.get("content"),
            payload.get("latency")
        )
        
        # Log success and return
        logger.info(f"Chat message successfully created. ID: {row[0]}")
        return {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "latency": row[3],
            "created_at": row[4].isoformat() if row[4] else None
        }
    except Exception as e:
        logger.error(f"Error creating chat message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chat message")
