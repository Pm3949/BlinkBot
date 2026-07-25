"""
================================================================================
USER FEEDBACK AND AUDIT LOGS DATABASE REPOSITORY LAYER (feedback_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages database interactions for message-level quality audits and user
feedback tickets (`message_feedback`). It supports workflows for ticketing:
1. Users flag a response (submit upvote/downvote and categories like 'inaccurate').
2. System administrators view open issues and mark them resolved (status changes to 'pending_verification').
3. Requester is prompted to verify if they are satisfied (closing the ticket or re-opening it with comments).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async`: Asynchronous context manager for PostgreSQL connections.
   - `run_in_threadpool`: Asynchronous thread dispatcher for blocking psycopg2 operations.

2. Repository Functions:
   - `fix_feedback_db_constraint()`: Dynamically alters constraints to support new statuses.
   - `submit_feedback(...)`: Inserts a feedback ticket when a user votes on a message.
   - `check_workspace_role(...)`: Checks user privileges within a workspace (e.g. Owner vs Member).
   - `get_open_feedback(...)`: Retrieves all open tickets for a workspace.
   - `get_feedback_workspace_id(...)`: Scopes tickets to parent workspaces for authentication checking.
   - `mark_feedback_resolved(...)`: Marks tickets as fixed, sending them to 'pending_verification'.
   - `get_pending_verification(...)`: Lists tickets waiting for verification by the creator. Includes
     a subquery to fetch the user's preceding message to provide context.
   - `get_feedback_for_verification(...)`: Gets the author and feedback notes.
   - `verify_feedback(...)`: Closes the ticket or re-opens it as 'open' with user comments appended.

TICKETING STATE MACHINE:
   [open] -> Administrator marks resolved -> [pending_verification] -> User satisfies -> [closed]
     ^                                             |
     |--------------- User rejects ----------------|
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool

async def fix_feedback_db_constraint():
    """
    Updates the database check constraint for feedback status values.

    Purpose:
        Ensures the `status` column in the `message_feedback` table supports all state machine
        values: ('open', 'resolved', 'pending_verification', 'closed'). Useful for migrations.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Drops the old check constraint `message_feedback_status_check` if present.
        - Adds a new check constraint requiring status to be one of the four valid states.
        - Commits changes to the database (commit=True).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open connection with commit=True since we are executing schema changes (DDL).
    async with get_db_cursor_async(commit=True) as cursor:
        # Drop constraint to avoid duplicates.
        await run_in_threadpool(cursor.execute, "ALTER TABLE message_feedback DROP CONSTRAINT IF EXISTS message_feedback_status_check;")
        # Apply updated check constraint.
        await run_in_threadpool(cursor.execute, "ALTER TABLE message_feedback ADD CONSTRAINT message_feedback_status_check CHECK (status IN ('open', 'resolved', 'pending_verification', 'closed'));")


async def submit_feedback(message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by):
    """
    Submits a user feedback record for a specific chat response.

    Purpose:
        Saves upvotes/downvotes, category classifications (e.g. 'hallucination'), and optional comments.

    Parameters:
        message_id (str): The ID of the chat message being evaluated.
        agent_id (str): The ID of the agent that generated the response.
        workspace_id (str): The ID of the workspace containing the chat.
        vote_type (str): Either 'up' (positive) or 'down' (negative).
        category (str | None): Classification label for bad responses.
        comment_text (str | None): User notes detail.
        created_by (str): The user ID of the evaluator.

    Returns:
        str/int: The generated database primary key ID of the feedback ticket.

    Side Effects / State Changes:
        - Writes a new row to the `message_feedback` table.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO message_feedback 
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (message_id, agent_id, workspace_id, vote_type, category, comment_text, created_by)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]


async def check_workspace_role(workspace_id: str, user_id: str):
    """
    Fetches the user's role inside a workspace.

    Purpose:
        Used to authorize feedback resolution actions, ensuring only workspace Owners
        or designated admins can resolve tickets.

    Parameters:
        workspace_id (str): The workspace UUID.
        user_id (str): The user UUID.

    Returns:
        tuple | None: Returns a single element tuple containing the role name (e.g., `('Owner',)`), or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (workspace_id, user_id)
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_open_feedback(workspace_id: str):
    """
    Retrieves all open feedback tickets for a workspace.

    Purpose:
        Loads open tickets for the workspace dashboard. Returns message content and agent names
        using JOIN operations.

    Parameters:
        workspace_id (str): The target workspace UUID.

    Returns:
        list of tuples: A list of open feedback records, ordered from newest to oldest.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # LEFT JOIN message_feedback (f) -> chat_messages (m) -> agents (a) to resolve names and content.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT f.id, f.message_id, f.agent_id, f.vote_type, f.category, 
                   f.comment_text, f.created_at, f.created_by,
                   m.content as message_content, m.role,
                   a.name as agent_name
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.status = 'open'
            ORDER BY f.created_at DESC;
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_feedback_workspace_id(feedback_id: str):
    """
    Locates the workspace ID linked to a feedback ticket.

    Purpose:
        Used during authentication checks to confirm a feedback ticket belongs to the user's workspace.

    Parameters:
        feedback_id (str): The target feedback UUID.

    Returns:
        tuple | None: A tuple containing the workspace_id, or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT workspace_id FROM message_feedback WHERE id = %s", (feedback_id,))
        return await run_in_threadpool(cursor.fetchone)


async def mark_feedback_resolved(feedback_id: str, resolved_by: str):
    """
    Marks a feedback ticket as resolved.

    Purpose:
        Changes status to 'pending_verification', indicating an administrator has attempted to fix
        the problem. Saves the resolver's user ID and timestamp.

    Parameters:
        feedback_id (str): Unique feedback UUID.
        resolved_by (str): The user ID of the resolving administrator.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates `status`, `resolved_at`, and `resolved_by` columns.
        - Commits changes.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE message_feedback
            SET status = 'pending_verification', resolved_at = now(), resolved_by = %s
            WHERE id = %s
            RETURNING id;
            """,
            (resolved_by, feedback_id)
        )


async def get_pending_verification(workspace_id: str, user_id: str):
    """
    Retrieves tickets waiting for verification by the user who created them.

    Purpose:
        Lists tickets waiting for creator verification. Uses a subquery to fetch the user's
        preceding chat message to provide context (the question that triggered the bad answer).

    Parameters:
        workspace_id (str): Workspace UUID.
        user_id (str): The user UUID who created the feedback.

    Returns:
        list of tuples: A list of pending tickets, sorted by resolution date.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # The nested subquery selects the user's question preceding the flagged assistant message:
        # Finds a message in the same session (`session_id = m.session_id`) where role is 'user'
        # and it was sent before the assistant's message (`um.created_at < m.created_at`).
        # Sorted DESC by creation time, limited to 1, to retrieve the immediate preceding prompt.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT f.id, f.message_id, f.agent_id, f.category, 
                   f.comment_text, f.created_at,
                   m.content as message_content,
                   a.name as agent_name,
                   (
                       SELECT content 
                       FROM chat_messages um 
                       WHERE um.session_id = m.session_id 
                         AND um.role = 'user' 
                         AND um.created_at < m.created_at 
                       ORDER BY created_at DESC 
                       LIMIT 1
                   ) as user_message
            FROM message_feedback f
            LEFT JOIN chat_messages m ON f.message_id = m.id
            LEFT JOIN agents a ON f.agent_id = a.id
            WHERE f.workspace_id = %s AND f.created_by = %s AND f.status = 'pending_verification'
            ORDER BY f.resolved_at DESC;
            """,
            (workspace_id, user_id)
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_feedback_for_verification(feedback_id: str):
    """
    Retrieves basic metrics of a ticket to verify ownership.

    Purpose:
        Fetches the author ID to authorize verification actions.

    Parameters:
        feedback_id (str): Feedback UUID.

    Returns:
        tuple | None: Returns (created_by, comment_text) or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(cursor.execute, "SELECT created_by, comment_text FROM message_feedback WHERE id = %s", (feedback_id,))
        return await run_in_threadpool(cursor.fetchone)


async def verify_feedback(feedback_id: str, is_satisfied: bool, comment: str, current_comment: str):
    """
    Records the user's validation response.

    Purpose:
        Updates status based on validation.
        - If satisfied, closes the ticket.
        - If not satisfied, re-opens the ticket and appends comments detailing why.

    Parameters:
        feedback_id (str): The target feedback UUID.
        is_satisfied (bool): True if the fix is verified, False to reject and re-open.
        comment (str): The reject comment detailing what is still wrong.
        current_comment (str): The existing feedback comment log.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates the `status` and `comment_text` columns.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # If the user is satisfied, close the ticket.
        if is_satisfied:
            await run_in_threadpool(cursor.execute, "UPDATE message_feedback SET status = 'closed' WHERE id = %s", (feedback_id,))
        # If the user rejects the fix, re-open the ticket and append their comments.
        else:
            new_comment = current_comment or ""
            # Format and append comments, preserving history.
            if comment:
                new_comment = f"{new_comment}\\n\\n[User Unsatisfied]: {comment}"
                
            await run_in_threadpool(
                cursor.execute,
                """
                UPDATE message_feedback
                SET status = 'open', comment_text = %s
                WHERE id = %s
                """,
                (new_comment, feedback_id)
            )

