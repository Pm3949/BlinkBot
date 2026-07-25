"""
================================================================================
THIRD-PARTY CONNECTOR AND OAUTH REPOSITORY LAYER (connector_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database integration records for external systems, focusing primarily on
OAuth connections (e.g. Google Drive) and document processing initialization. It provides
functions to store and recover refresh/access tokens and set up processing stubs for
document processing workflows.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: The custom database context manager.
   - `run_in_threadpool`: FastAPI utility that runs blocking database calls in a background thread pool.
   - `psycopg2.extras`: Imports cursor factory profiles.

2. Repository Functions:
   - `upsert_google_token(...)`: Stores or updates Google OAuth credentials, using SQL COALESCE
     to ensure we do not overwrite the persistent `refresh_token` if a new token isn't provided.
   - `get_google_token(user_id)`: Fetches a user's active Google OAuth tokens.
   - `update_access_token_only(user_id, access_token)`: Refreshes only the ephemeral access token
     when it expires.
   - `get_agent_embed_info(agent_id)`: Looks up embedding configuration details for vector processing.
   - `create_document_stub(agent_id, filename)`: Creates a document row marked as 'processing' to return
     an ID immediately for async background indexing pipelines.

TOKEN COALESCE PATTERN:
- Google OAuth refresh tokens are typically issued only on the first authorization prompt.
  Subsequent flows return only a new `access_token`. To prevent overwriting the existing refresh
  token with a NULL value, we query existing tokens first, and then execute an update using
  `COALESCE(%s, refresh_token)` in SQL.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import psycopg2.extras

async def upsert_google_token(user_id: str, access_token: str, refresh_token: str):
    """
    Inserts a new Google OAuth connection or updates tokens on an existing connection.

    Purpose:
        Saves OAuth authorization tokens. Handles token refreshes. Uses a COALESCE logic
        during updates to make sure we don't clear the persistent refresh_token if the auth
        flow only returned a new ephemeral access_token.

    Parameters:
        user_id (str): The unique database user identifier.
        access_token (str): The temporary access token from Google OAuth.
        refresh_token (str | None): The persistent refresh token from Google OAuth (can be None).

    Returns:
        None.

    Side Effects / State Changes:
        - Inserts or modifies a row in the `oauth_connections` table.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection in a write transaction.
    async with get_db_cursor_async(commit=True) as cursor:
        # Check if the user already has a Google OAuth connection record.
        await run_in_threadpool(cursor.execute, "SELECT id FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        existing = await run_in_threadpool(cursor.fetchone)
        
        # If a connection record exists, update the tokens.
        if existing:
            # We use COALESCE(%s, refresh_token) so that if the passed refresh_token parameter is Null (None),
            # PostgreSQL retains the existing refresh_token value in the database.
            await run_in_threadpool(
                cursor.execute,
                "UPDATE oauth_connections SET access_token = %s, refresh_token = COALESCE(%s, refresh_token), updated_at = NOW() WHERE id = %s",
                (access_token, refresh_token, existing[0])
            )
        # If no connection record exists, insert a new record.
        else:
            await run_in_threadpool(
                cursor.execute,
                "INSERT INTO oauth_connections (user_id, provider, access_token, refresh_token) VALUES (%s, 'google', %s, %s)",
                (user_id, access_token, refresh_token)
            )


async def get_google_token(user_id: str):
    """
    Retrieves Google OAuth credentials for a specific user.

    Purpose:
        Fetches stored access and refresh tokens to execute integration actions (like accessing Google Drive APIs).

    Parameters:
        user_id (str): The unique user database identifier.

    Returns:
        tuple | None: Returns (access_token, refresh_token) if the user has connected Google OAuth, or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT access_token, refresh_token FROM oauth_connections WHERE user_id = %s AND provider = 'google'", (user_id,))
        return await run_in_threadpool(cursor.fetchone)


async def update_access_token_only(user_id: str, access_token: str):
    """
    Updates the access token for a Google OAuth connection.

    Purpose:
        Saves a newly generated access token obtained from a refresh token request when the old one expires.

    Parameters:
        user_id (str): The unique user database identifier.
        access_token (str): The new Google access token.

    Returns:
        None.

    Side Effects / State Changes:
        - Modifies `access_token` and `updated_at` in the `oauth_connections` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE oauth_connections SET access_token = %s, updated_at = NOW() WHERE user_id = %s AND provider = 'google'", 
            (access_token, user_id)
        )


async def get_agent_embed_info(agent_id: str):
    """
    Retrieves the embedding configurations for an agent.

    Purpose:
        Provides the vectorizer background worker with instructions on which model to use
        and how to split the text during file parsing.

    Parameters:
        agent_id (str): Unique agent identifier.

    Returns:
        tuple | None: Returns (embedding_model, chunk_strategy) or None if the agent doesn't exist.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT embedding_model, chunk_strategy FROM agents WHERE id = %s",
            (agent_id,),
        )
        return await run_in_threadpool(cursor.fetchone)


async def create_document_stub(agent_id: str, filename: str):
    """
    Creates an initial placeholder document record in the database.

    Purpose:
        Registers a document marked with the 'processing' state. Returns the generated
        document ID immediately, allowing background workers to parse and index the file
        asynchronously without blocking client request response times.

    Parameters:
        agent_id (str): The ID of the agent this document is linked to.
        filename (str): The name of the uploaded document file.

    Returns:
        str/int: The generated database identifier of the new document.

    Side Effects / State Changes:
        - Writes a new row to the `documents` table with status 'processing' and size 0.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Create a document placeholder.
        await run_in_threadpool(
            cursor.execute,
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', 0) RETURNING id;",
            (agent_id, filename)
        )
        # Fetch the RETURNING id column from the executed query insert and return it.
        return (await run_in_threadpool(cursor.fetchone))[0]

