"""
================================================================================
ANALYTICS DATABASE REPOSITORY LAYER (analytics_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the Data Access Object (DAO) or repository layer specifically
dedicated to retrieving and compiling telemetry, metrics, and analytics for the
user dashboard. It interacts with the backend database (PostgreSQL) and exposes
methods that return structured aggregates, trends, and logs.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: A custom asynchronous context manager (from `database.py`)
     that facilitates automatic connection acquisition, cursor management, and
     transaction control (commit/rollback).
   - `run_in_threadpool`: A FastAPI utility that runs blocking synchronous functions
     (like psycopg2's SQL execution) in a background thread pool to prevent blocking
     the main asynchronous event loop.

2. Repository Functions:
   - `get_analytics_metrics(user_id)`: Fetches key summary counters for a user: total
     custom agents (excluding system-created placeholders), total uploaded documents,
     total document storage space used (in MB), and the total count of messages
     processed through user-facing chat widgets.
   - `get_analytics_series(user_id)`: Fetches time-series data for the last 30 days
     representing daily chat traffic. It separates internal agent chat sessions from
     external widget message log counts.
   - `get_analytics_top_chatbots(user_id)`: Selects the top 5 chatbots owned by the user,
     ranked by their aggregate message volumes.
   - `get_analytics_recent_questions(user_id)`: Returns the 10 most recent user questions
     submitted across any of the user's agents, along with timestamps and agent names.
   - `get_feedback_stats(user_id)`: Pulls qualitative user feedback metrics (upvotes,
     downvotes, and feedback category distribution) over the last 30 days.

CONCURRENCY PRINCIPLE:
Since standard Python PostgreSQL drivers (like `psycopg2`) run synchronously and perform
network I/O, calling their methods directly inside an `async def` function would block
the entire application server. By executing `cursor.execute`, `cursor.fetchone`, and
`cursor.fetchall` inside `run_in_threadpool`, we dispatch these blocking database
operations to background threads. This keeps the async event loop free to handle other
concurrent HTTP and WebSockets connections.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def get_analytics_metrics(user_id: str):
    """
    Compiles key high-level dashboard metrics for a specific user.

    Purpose:
        Retrieves the counts of active agents (excluding standard default assistants),
        total uploaded documents, combined storage usage in Megabytes (MB), and the
        aggregate message count across all user-facing chatbots.

    Parameters:
        user_id (str): The unique database identifier of the user requesting analytics.

    Returns:
        tuple: A 4-element tuple containing:
            - total_agents (int): The number of custom agents created by the user.
            - total_docs (int): The number of documents indexed across the user's agents.
            - total_storage_mb (float): The total database file size in MB.
            - total_widget_msgs (int): The aggregate message count from deployed chatbots.

    Side Effects / State Changes:
        - None. This function performs read-only database reads.

    Errors / Exceptions:
        - May raise database connection errors or query syntax errors if database schema changes.
    """
    # Open a database connection using our async context manager.
    # We specify commit=False since this function only reads data and does not modify the DB state.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # --- Total Custom Agents ---
        # Query the agents table, counting entries for this user.
        # We exclude default system-created agents ('Network Manager', 'General Assistant')
        # to ensure that we only show the number of custom agents created by the user.
        await run_in_threadpool(
            cursor.execute, 
            "SELECT COUNT(*) FROM agents WHERE user_id = %s AND name NOT IN ('Network Manager', 'General Assistant')", 
            (user_id,)
        )
        # Fetch the query result. fetchone returns a tuple containing the query columns,
        # so we access the first element (index 0). If the result is None or empty, we fall back to 0.
        total_agents = (await run_in_threadpool(cursor.fetchone))[0] or 0

        # --- Total Documents and Storage ---
        # Query both count of documents and sum of their file sizes in bytes.
        # We perform an INNER JOIN between documents (d) and agents (a) to filter documents
        # that belong to the user's agents.
        # COALESCE ensures that if SUM() yields null (no files found), it returns 0 instead.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) 
            FROM documents d JOIN agents a ON d.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        # Fetch the results containing both values in a tuple (count, size_bytes).
        doc_stats = await run_in_threadpool(cursor.fetchone)
        # Extract the document count (index 0).
        total_docs = doc_stats[0] or 0
        # Extract the sum of bytes (index 1) and convert to Megabytes.
        # Division by (1024 * 1024) transforms: bytes -> kilobytes -> megabytes.
        total_storage_mb = (doc_stats[1] or 0) / (1024 * 1024)

        # --- Total Chatbot Widget Messages ---
        # Calculate the sum of messages processed by the chatbots owned by the user.
        # We join chatbots (c) with agents (a) to link back to the user's ID.
        # COALESCE is used here to safely return 0 if no chatbots have been deployed.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(SUM(message_count), 0) FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE a.user_id = %s
            """,
            (user_id,),
        )
        # Fetch and unpack the sum.
        total_widget_msgs = (await run_in_threadpool(cursor.fetchone))[0] or 0
        
        # Return all computed values as a tuple.
        return total_agents, total_docs, total_storage_mb, total_widget_msgs


async def get_analytics_series(user_id: str):
    """
    Retrieves time-series message counts for the last 30 days to build analytics graphs.

    Purpose:
        Fetches two distinct activity streams to chart user engagement over time:
        1. Internal chat sessions (user interactions with the dashboard agents).
        2. External widget message logs (interactions by end-users on embedded chatbots).

    Parameters:
        user_id (str): The unique database identifier of the user.

    Returns:
        tuple: A 2-element tuple containing:
            - internal_series (list of tuples): A list of (date, message_count) representing internal chats.
            - widget_series (list of tuples): A list of (date, message_count) representing widget chats.

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a database connection inside a read-only transaction.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # --- Internal Agent Message Series ---
        # Fetch daily message counts for the user's agents.
        # date_trunc('day', m.created_at)::date strips time info (HH:MM:SS) and casts to a plain DATE type.
        # We JOIN chat_messages -> chat_sessions -> agents to associate messages with the owner.
        # We restrict results to user messages (m.role = 'user') and those created in the last 30 days.
        # Results are grouped by date and sorted chronologically.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT date_trunc('day', m.created_at)::date AS day, count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND m.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        # Fetch the entire resulting rows list of time-series data.
        internal_series = await run_in_threadpool(cursor.fetchall)

        # --- External Chatbot Widget Message Series ---
        # Fetch daily message counts for external widgets owned by this user.
        # We JOIN widget_message_logs -> chatbots -> agents to verify owner user_id.
        # Only messages logged in the last 30 days are included.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT date_trunc('day', l.created_at)::date AS day, count(*) 
            FROM widget_message_logs l
            JOIN chatbots c ON l.chatbot_id = c.id
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s 
            AND l.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
            """,
            (user_id,),
        )
        # Fetch all time-series logs for the external widgets.
        widget_series = await run_in_threadpool(cursor.fetchall)
        
        # Return both series for graph rendering.
        return internal_series, widget_series


async def get_analytics_top_chatbots(user_id: str):
    """
    Retrieves the user's top 5 chatbots sorted by their total message count.

    Purpose:
        Identifies which chatbot widgets are receiving the most user interactions,
        allowing the dashboard to highlight high-performing channels.

    Parameters:
        user_id (str): The unique database identifier of the user.

    Returns:
        list of tuples: A list of tuples containing:
            - name (str): The name of the chatbot retrieved from its JSON settings.
            - message_count (int): The number of messages processed by the chatbot.

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a read-only transaction.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # Execute query selecting name and message counts.
        # `settings->>'name'` extraction retrieves the name key value from the JSON settings field.
        # We JOIN chatbots with agents to filter by the user_id owner.
        # Ordered by message count in descending order, limited to 5 results.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT c.settings->>'name' as name, c.message_count 
            FROM chatbots c JOIN agents a ON c.agent_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY c.message_count DESC LIMIT 5
            """,
            (user_id,),
        )
        # Fetch and return the list of top 5 chatbots.
        return await run_in_threadpool(cursor.fetchall)


async def get_analytics_recent_questions(user_id: str):
    """
    Retrieves the 10 most recent user questions asked across all of the user's agents.

    Purpose:
        Displays a feed of live or recent prompts submitted by users to help administrators
        understand what their users are asking about in real-time.

    Parameters:
        user_id (str): The unique database identifier of the user.

    Returns:
        list of tuples: A list of tuples containing:
            - content (str): The text content of the message.
            - created_at (datetime): The timestamp when the message was sent.
            - agent_name (str): The name of the agent that processed the message.

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a read-only transaction.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # Run query to retrieve recent questions.
        # We filter messages where the role is 'user' (excluding assistant responses).
        # Sorted by creation timestamp in descending order (newest first), and limited to 10.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT m.content, m.created_at, a.name as agent_name 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            ORDER BY m.created_at DESC LIMIT 10
            """,
            (user_id,),
        )
        # Fetch and return the recent question rows.
        return await run_in_threadpool(cursor.fetchall)


async def get_feedback_stats(user_id: str):
    """
    Aggregates qualitative upvotes, downvotes, and feedback categories for the user's agents.

    Purpose:
        Retrieves user feedback signals (thumbs up/down) and the categorized reasons
        for downvotes (e.g., inaccurate, slow, inappropriate) over the last 30 days
        to analyze quality and user satisfaction.

    Parameters:
        user_id (str): The unique database identifier of the user.

    Returns:
        tuple: A 3-element tuple containing:
            - up_votes (int): Number of upvotes ('up') received in the last 30 days.
            - down_votes (int): Number of downvotes ('down') received in the last 30 days.
            - category_distribution (list of dict): A breakdown of feedback category counts.
              Each dict is structured as {"name": category_name, "value": feedback_count}.

    Side Effects / State Changes:
        - None. Read-only operation.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open a read-only transaction.
    async with get_db_cursor_async(commit=False) as cursor:
        
        # --- Aggregate Upvotes & Downvotes ---
        # Execute query using conditional aggregates (FILTER clause) to count up and down votes in one pass.
        # Only counts feedback records from the last 30 days belonging to the user's agents.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT 
                COUNT(*) FILTER (WHERE vote_type = 'up'),
                COUNT(*) FILTER (WHERE vote_type = 'down')
            FROM message_feedback f
            JOIN agents a ON f.agent_id = a.id
            WHERE a.user_id = %s AND f.created_at >= current_date - interval '30 days'
            """,
            (user_id,)
        )
        # Fetch the vote aggregate counts tuple.
        vote_counts = await run_in_threadpool(cursor.fetchone)
        # Extract upvotes count, defaulting to 0 if None.
        up_votes = vote_counts[0] or 0
        # Extract downvotes count, defaulting to 0 if None.
        down_votes = vote_counts[1] or 0

        # --- Category Distribution breakdown ---
        # Group feedback items by category name and order by total count descending.
        # We ignore null categories (e.g. upvotes generally don't have categories, only downvotes do).
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT category, COUNT(*) as count
            FROM message_feedback f
            JOIN agents a ON f.agent_id = a.id
            WHERE a.user_id = %s AND f.category IS NOT NULL AND f.created_at >= current_date - interval '30 days'
            GROUP BY category
            ORDER BY count DESC
            """,
            (user_id,)
        )
        # Fetch all matching categories and counts.
        category_rows = await run_in_threadpool(cursor.fetchall)
        category_distribution = [{"name": r[0], "value": r[1]} for r in category_rows]
        # Return upvotes, downvotes, and the categories list.
        return up_votes, down_votes, category_distribution


async def get_credit_analytics(user_id: str):
    """
    Retrieves credit telemetry data including wallet balance, usage per model, and 30-day trends.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # 1. Fetch current credit balance
        await run_in_threadpool(
            cursor.execute,
            "SELECT COALESCE(credit_balance, 0.0) FROM user_wallets WHERE user_id = %s",
            (user_id,)
        )
        r_bal = await run_in_threadpool(cursor.fetchone)
        credit_balance = float(r_bal[0]) if r_bal else 0.0

        # 2. Fetch usage breakdown by model (negative credits represent consumption deduction)
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT COALESCE(model_used, 'System Overhead/Base'), ABS(SUM(amount_credits))
            FROM credit_transactions
            WHERE user_id = %s AND amount_credits < 0
            GROUP BY model_used
            ORDER BY ABS(SUM(amount_credits)) DESC
            """,
            (user_id,)
        )
        model_rows = await run_in_threadpool(cursor.fetchall)
        credit_by_model = [{"name": r[0], "value": float(r[1])} for r in model_rows]

        # 3. Fetch 30-day daily historical credit usage trends
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT date_trunc('day', created_at)::date AS day, ABS(SUM(amount_credits))
            FROM credit_transactions
            WHERE user_id = %s AND amount_credits < 0 AND created_at >= current_date - interval '30 days'
            GROUP BY day
            ORDER BY day ASC
            """,
            (user_id,)
        )
        series_rows = await run_in_threadpool(cursor.fetchall)
        credit_series = [{"date": str(r[0]), "credits": float(r[1])} for r in series_rows]

        return credit_balance, credit_by_model, credit_series
