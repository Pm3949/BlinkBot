"""
================================================================================
THIRD-PARTY NATIVE API INTEGRATION TOOLS (native_tools.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module compiles external utility integrations (tools) enabling agent networks to 
directly interact with third-party web services like GitHub and Slack. 

KEY ARCHITECTURAL FEATURES:
1. Dynamic OAuth Token Fetching (`get_oauth_token`):
   Agents execute actions on behalf of the authenticated user. When a tool runs, it queries 
   the PostgreSQL `oauth_connections` table to fetch the user's provider-specific access token.
2. Conditional Tool Inclusion:
   Tools are instantiated dynamically based on the agent's `allowed_integrations` array list. 
   If an agent is not configured with 'github' permissions, the GitHub tool is not registered 
   in the agent's toolbox.
3. Asynchronous HTTP Pipelines (`httpx.AsyncClient`):
   Performs non-blocking external API requests to protect server thread execution pools.

BEGINNER API CONCEPTS:
- OAuth Connection: A security protocol allowing this application to perform actions on 
  external platforms (like writing GitHub issues or Slack messages) on behalf of a user without 
  exposing the user's password.
- HTTP Request Headers: Metadata sent with requests containing credentials (such as OAuth Bearer tokens) 
  and content format instructions (such as `Accept` or `Content-Type`).
- prebuilt tools: Functions marked with LangChain's `@tool` decorator that agents can invoke 
  autonomously when planning execution paths.
"""

from typing import List
import logging
from langchain_core.tools import tool, BaseTool
from database import get_db_cursor_async
from starlette.concurrency import run_in_threadpool
import httpx

# Initialize standard module logger.
logger = logging.getLogger(__name__)


# ==========================================
# HELPER DATA ACCESS FUNCTIONS
# ==========================================

async def get_oauth_token(user_id: str, provider: str) -> str:
    """
    Fetches the OAuth access token for a specific user and provider.

    Purpose:
        Queries the database to retrieve active tokens required to authenticate 
        third-party API calls.

    Parameters:
        user_id (str): UUID of the user requesting tool execution.
        provider (str): The integration platform name (e.g. 'github', 'slack').

    Returns:
        str: The retrieved access token string if found, otherwise None.

    Side Effects / State Changes:
        - Performs a read query on the database connection pool.

    Errors / Exceptions:
        - Returns None if the query fails or no matching token is found.
    """
    # Borrow a cursor using the database async context manager.
    async with get_db_cursor_async(commit=False) as cursor:
        # Run the select query inside a worker thread to keep the event loop non-blocking.
        await run_in_threadpool(
            cursor.execute,
            "SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = %s",
            (user_id, provider)
        )
        # Fetch query results in the worker thread.
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            # Return the access token string.
            return row[0]
        # Return None if no connection token exists.
        return None


# ==========================================
# PUBLIC TOOL GENERATION FACTORY
# ==========================================

def create_native_tools(user_id: str, allowed_integrations: List[str]) -> List[BaseTool]:
    """
    Generates LangChain integration tools based on enabled provider settings.

    Purpose:
        Dynamically instantiates and returns a list of LangChain tools 
        that matches the agent's authorized integrations.

    Parameters:
        user_id (str): UUID of the user initiating agent configurations.
        allowed_integrations (list of str): List of enabled integrations (e.g. ['github', 'slack']).

    Returns:
        list of BaseTool: List containing the instantiated LangChain tool classes.
    """
    # Initialize the tools list.
    tools = []

    # Check if GitHub tools are enabled for this agent.
    if "github" in allowed_integrations:
        @tool(name="github_create_issue")
        async def github_create_issue(repo: str, title: str, body: str) -> str:
            """
            Create a GitHub issue in a specified repository (format: owner/repo).
            Only use this if you have explicit information about the bug/task.

            Purpose:
                Sends an authenticated request to the GitHub API to create an issue.

            Parameters:
                repo (str): Repository path formatted as 'owner/repo_name'.
                title (str): Title of the issue.
                body (str): Description body text.

            Returns:
                str: Success status message containing the issue URL or an error description.
            """
            # Fetch the user's GitHub access token.
            token = await get_oauth_token(user_id, "github")
            if not token:
                # Return early if token is missing.
                return "Error: User has not connected their GitHub account via OAuth."
            
            # Construct the endpoint URL.
            url = f"https://api.github.com/repos/{repo}/issues"
            # Set authorization headers.
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            # Set request body payload.
            payload = {"title": title, "body": body}
            
            try:
                # Perform the async post request.
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    # Verify response status.
                    if resp.status_code == 201:
                        data = resp.json()
                        return f"Successfully created GitHub issue: {data.get('html_url')}"
                    else:
                        return f"Failed to create issue. Status: {resp.status_code}. Response: {resp.text}"
            except Exception as e:
                # Return exception details.
                return f"Error connecting to GitHub API: {e}"

        # Append the tool.
        tools.append(github_create_issue)

    # Check if Slack tools are enabled for this agent.
    if "slack" in allowed_integrations:
        @tool(name="slack_send_message")
        async def slack_send_message(channel: str, text: str) -> str:
            """
            Send a message to a specific Slack channel.
            The channel parameter can be a channel ID (e.g. C12345) or name (e.g. #general).

            Purpose:
                Sends an authenticated chat message payload to a Slack workspace.

            Parameters:
                channel (str): Target channel name or channel ID.
                text (str): Message text to send.

            Returns:
                str: Success confirmation message or an error description.
            """
            # Fetch the user's Slack access token.
            token = await get_oauth_token(user_id, "slack")
            if not token:
                # Return early if token is missing.
                return "Error: User has not connected their Slack account via OAuth."
            
            # Construct the endpoint URL.
            url = "https://slack.com/api/chat.postMessage"
            # Set authorization headers.
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            # Set request body payload.
            payload = {"channel": channel, "text": text}
            
            try:
                # Perform the async post request.
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()
                    # Verify response status.
                    if data.get("ok"):
                        return f"Successfully sent message to Slack channel {channel}."
                    else:
                        return f"Failed to send Slack message: {data.get('error')}"
            except Exception as e:
                # Return exception details.
                return f"Error connecting to Slack API: {e}"
                
        # Append the tool.
        tools.append(slack_send_message)

    # Return the assembled tools list.
    return tools

