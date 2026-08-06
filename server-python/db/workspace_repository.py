"""
================================================================================
WORKSPACE AND MEMBERS DATABASE REPOSITORY LAYER (workspace_repository.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module manages workspace multi-tenant configurations, user memberships, role assignments,
and feature permissions flags. It supports:
1. Workspace Provisioning: Creating workspaces and automatically registering the owner
   as an Admin with full permissions.
2. Workspace Invitations: Adding new members by email. If the invited email matches an existing
   registered user, it links them immediately. If not, the `user_id` remains NULL as a pending invite
   until claimed.
3. Invite Claim System: When a user registers a new account, the system sweeps `workspace_members`
   and updates matching email columns to reference the newly generated user ID.
4. Role and Permissions Audits: Managing user roles (e.g. Admin, Member) and granular studio/model access
   permissions stored as PostgreSQL JSONB objects.
5. Subscription Limits Integration: Fetches subscription levels and limits of workspace owners
   to validate quota restrictions (such as maximum workspaces).

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `get_db_cursor_async` and `run_in_threadpool`: Core DB access interfaces.
   - `json`: Standard JSON encoder.

2. Repository Functions:
   - `check_workspace_member_exists(workspace_id, email)`: Checks membership states.
   - `create_workspace_member(...)`: Adds a member, mapping to registered users via a nested subquery
     on `public.users` and initializing permissions defaults.
   - `claim_pending_workspace_invites(...)`: Resolves invitations for newly registered users.
   - `get_user_subscription_limits(user_id)`: Fetches user plan levels and quotas.
   - `count_owned_workspaces(owner_id)`: Counts workspaces owned by a user.
   - `create_workspace(...)`: Spawns a workspace and configures the owner's Admin membership.
   - `get_primary_workspace(user_id)`: Returns the user's primary owned workspace.
   - `update_workspace_name(workspace_id, name)`: Modifies workspace titles.
   - `get_user_workspaces(user_id)`: Fetches all workspaces a user belongs to.
   - `get_workspace_members(workspace_id)`: Fetches workspace members.
   - `update_member_role(...)` / `update_member_permissions(...)`: Edits memberships.
   - `remove_member(member_id)`: Deletes members.
   - `get_member_by_id(member_id)`: Retrieves membership details.
"""

from database import get_db_cursor_async
from fastapi.concurrency import run_in_threadpool
import json

async def check_workspace_member_exists(workspace_id: str, email: str):
    """
    Checks if a user is already registered in a workspace.

    Purpose:
        Prevents adding duplicate members to a workspace.

    Parameters:
        workspace_id (str): Workspace UUID.
        email (str): Email to search for.

    Returns:
        tuple | None: Returns (id,) if found, or None.

    Side Effects / State Changes:
        - None. Read-only query.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    # Open database connection in a read-only transaction (commit=False).
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (workspace_id, email),
        )
        return await run_in_threadpool(cursor.fetchone)


async def create_workspace_member(workspace_id: str, email: str, role: str):
    """
    Adds a new user membership to a workspace.

    Purpose:
        Invites a user. If the email is registered in `public.users`, links it immediately.
        Otherwise, leaves the `user_id` field as NULL to mark it as a pending invitation.
        Initializes default workspace permissions with studio and models set to false.

    Parameters:
        workspace_id (str): The workspace UUID.
        email (str): The invited user's email.
        role (str): Role designation (e.g. 'Admin', 'Member', 'Viewer').

    Returns:
        str/int: The generated database ID of the workspace membership.

    Side Effects / State Changes:
        - Writes a row to `workspace_members`.
        - Commits updates (commit=True).

    Errors / Exceptions:
        - May raise database execution exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Split email by "@" to generate a default user name from the prefix (e.g., "alice@example.com" -> "alice").
        default_name = email.split("@")[0]
        # Insert statement. A nested subquery SELECTs the user ID from `public.users` matching the email.
        # LOWER() is used to execute a case-insensitive email check.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (
                %s, 
                (SELECT id FROM public.users WHERE LOWER(email) = LOWER(%s) LIMIT 1),
                %s, 
                %s, 
                %s, 
                '{"studio": false, "models": false}'::jsonb
            )
            RETURNING id;
            """,
            (workspace_id, email, email, default_name, role),
        )
        return (await run_in_threadpool(cursor.fetchone))[0]


async def claim_pending_workspace_invites(user_id: str, email: str):
    """
    Claims pending workspace invitations for a newly registered user account.

    Purpose:
        Sweeps the membership table and updates matching email rows with the new user's UUID.

    Parameters:
        user_id (str): The newly registered user UUID.
        email (str): The registered user email.

    Returns:
        None.

    Side Effects / State Changes:
        - Updates matching rows in `workspace_members`.
        - Commits changes to the database.

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Look up records matching the user's email case-insensitively where user_id is currently NULL (pending invite).
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE workspace_members
            SET user_id = %s
            WHERE LOWER(email) = LOWER(%s) AND user_id IS NULL;
            """,
            (user_id, email),
        )


async def get_user_subscription_limits(user_id: str):
    """
    Fetches subscription details and usage limits for a user.

    Purpose:
        Used during workspace provisioning to evaluate user tier quotas.

    Parameters:
        user_id (str): Unique user identifier.

    Returns:
        tuple | None: (plan_tier (str), limits (dict/json)) or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT plan_tier, limits
            FROM user_subscriptions
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def count_owned_workspaces(owner_id: str):
    """
    Counts the number of workspaces owned by a user.

    Purpose:
        Validates user creation quotas.

    Parameters:
        owner_id (str): The unique user UUID of the owner.

    Returns:
        int: Number of workspaces owned by the user.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT COUNT(*) FROM workspaces WHERE owner_id = %s", 
            (owner_id,)
        )
        return (await run_in_threadpool(cursor.fetchone))[0]


async def create_workspace(name: str, owner_id: str, email: str, user_name: str):
    """
    Provisions a new workspace and registers the creator as an Admin.

    Purpose:
        Creates a workspace. In the same transaction, adds the owner as a member with Admin role
        and full permissions (studio: true, models: true).

    Parameters:
        name (str): The workspace name.
        owner_id (str): User UUID of the workspace creator.
        email (str): Email address of the creator.
        user_name (str): Display name of the creator.

    Returns:
        str: The generated database ID of the new workspace.

    Side Effects / State Changes:
        - Writes a new row to `workspaces`.
        - Writes a new row to `workspace_members`.
        - Commits changes (commit=True).

    Errors / Exceptions:
        - May raise database-related errors.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Step 1: Create the workspace entry.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspaces (name, owner_id)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (name, owner_id)
        )
        # Fetch the created workspace UUID.
        workspace_id = (await run_in_threadpool(cursor.fetchone))[0]
        
        # Step 2: Add the owner as a member with Admin role and full permissions.
        # Permissions are stored as a JSONB database column.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, 'Admin', '{"studio": true, "models": true}'::jsonb)
            """,
            (workspace_id, owner_id, email, user_name)
        )

        # Step 3: Provision core system tools (Web Search, CSV Sandbox, OCR Analyzer)
        # Ensure is_system = true and is_global = true.
        CORE_SYSTEM_TOOLS = [
            {
                "name": "Web Search Fallback",
                "tool_type": "api_webhook",
                "configuration": {
                    "system_identifier": "web_search",
                    "description": "Allow the agent to search the internet if the answer isn't in documents."
                }
            },
            {
                "name": "Python Code Sandbox (CSV Analyzer)",
                "tool_type": "database",
                "configuration": {
                    "system_identifier": "code_interpreter",
                    "description": "Allow the agent to natively parse, query, and perform statistical analysis on uploaded CSV and Excel spreadsheet files."
                }
            },
            {
                "name": "Image Reader (OCR)",
                "tool_type": "api_webhook",
                "configuration": {
                    "system_identifier": "ocr_reader",
                    "description": "Perform optical character recognition (OCR) fallback routines for scanned PDFs or images."
                }
            }
        ]
        
        for tool in CORE_SYSTEM_TOOLS:
            await run_in_threadpool(
                cursor.execute,
                """
                INSERT INTO workspace_tools (workspace_id, name, tool_type, configuration, is_system, is_global)
                VALUES (%s, %s, %s, %s, true, true)
                """,
                (workspace_id, tool["name"], tool["tool_type"], json.dumps(tool["configuration"]))
            )

        return workspace_id


async def get_primary_workspace(user_id: str):
    """
    Retrieves the first workspace owned by a user.

    Purpose:
        Fetches the primary workspace details when a user logs in.

    Parameters:
        user_id (str): User UUID.

    Returns:
        tuple | None: (id, name, owner_id) or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, name, owner_id
            FROM workspaces
            WHERE owner_id = %s
            LIMIT 1
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def update_workspace_name(workspace_id: str, name: str):
    """
    Modifies a workspace's display name.

    Purpose:
        Renames a workspace.

    Parameters:
        workspace_id (str): Workspace UUID.
        name (str): The new name.

    Returns:
        tuple | None: (id, name, owner_id) or None.

    Side Effects / State Changes:
        - Modifies `name` and updates the timestamp (`updated_at = now()`) in the workspaces table.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            UPDATE workspaces
            SET name = %s, updated_at = now()
            WHERE id = %s
            RETURNING id, name, owner_id;
            """,
            (name, workspace_id)
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_user_workspaces(user_id: str):
    """
    Fetches all workspaces a user belongs to.

    Purpose:
        Lists workspaces (both owned and shared) for the user's dashboard selection.

    Parameters:
        user_id (str): User UUID.

    Returns:
        list of tuples: Workspace and membership records:
                        (id, name, owner_id, role, permissions)

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        # Join workspaces and members to retrieve attributes.
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT w.id, w.name, w.owner_id, wm.role, wm.permissions
            FROM workspace_members wm
            JOIN workspaces w ON wm.workspace_id = w.id
            WHERE wm.user_id = %s
            """,
            (user_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def get_workspace_members(workspace_id: str):
    """
    Retrieves all members of a workspace.

    Purpose:
        Lists workspace members on the workspace settings page.

    Parameters:
        workspace_id (str): Workspace UUID.

    Returns:
        list of tuples: Members records sorted by date:
                        (id, user_id, email, name, role, permissions, created_at)

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT id, user_id, email, name, role, permissions, created_at
            FROM workspace_members
            WHERE workspace_id = %s
            ORDER BY created_at ASC
            """,
            (workspace_id,)
        )
        return await run_in_threadpool(cursor.fetchall)


async def update_member_role(member_id: str, role: str):
    """
    Updates a workspace member's role designation.

    Purpose:
        Modifies user privileges (e.g. demoting an Admin to a Member).

    Parameters:
        member_id (str): Membership record UUID.
        role (str): The new role.

    Returns:
        tuple | None: (id,) or None.

    Side Effects / State Changes:
        - Updates the `role` column in the workspace_members table.
        - Commits change.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "UPDATE workspace_members SET role = %s WHERE id = %s RETURNING id;",
            (role, member_id)
        )
        return await run_in_threadpool(cursor.fetchone)


async def update_member_permissions(member_id: str, permissions: dict):
    """
    Updates a workspace member's feature permissions.

    Purpose:
        Modifies granular access flags. Encodes permissions dict to a JSON string
        before updating the JSONB column.

    Parameters:
        member_id (str): Membership record UUID.
        permissions (dict): Permissions dictionary (e.g. `{"studio": true, "models": false}`).

    Returns:
        tuple | None: (id,) or None.

    Side Effects / State Changes:
        - Modifies the JSONB permissions column.
        - Commits changes.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        # Convert the permissions dictionary to a JSON string and cast to jsonb.
        await run_in_threadpool(
            cursor.execute,
            "UPDATE workspace_members SET permissions = %s::jsonb WHERE id = %s RETURNING id;",
            (json.dumps(permissions), member_id)
        )
        return await run_in_threadpool(cursor.fetchone)


async def remove_member(member_id: str):
    """
    Removes a member from a workspace.

    Purpose:
        Revokes a user's access to a workspace.

    Parameters:
        member_id (str): Membership record UUID.

    Returns:
        tuple | None: (id,) of the deleted member if found, or None.

    Side Effects / State Changes:
        - Deletes the row from `workspace_members`.
        - Commits transaction.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=True) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "DELETE FROM workspace_members WHERE id = %s RETURNING id;",
            (member_id,)
        )
        return await run_in_threadpool(cursor.fetchone)


async def get_member_by_id(member_id: str):
    """
    Retrieves membership metadata details by ID.

    Purpose:
        Resolves membership properties. Joins the workspace table to return the workspace name.

    Parameters:
        member_id (str): Membership record UUID.

    Returns:
        tuple | None: (id, workspace_id, email, name, user_id, workspace_name) or None.

    Side Effects / State Changes:
        - None. Read-only.

    Errors / Exceptions:
        - May raise database exceptions.
    """
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            """
            SELECT wm.id, wm.workspace_id, wm.email, wm.name, wm.user_id, w.name as workspace_name
            FROM workspace_members wm
            JOIN workspaces w ON wm.workspace_id = w.id
            WHERE wm.id = %s
            """,
            (member_id,)
        )
        return await run_in_threadpool(cursor.fetchone)

