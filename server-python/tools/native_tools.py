from typing import List
import logging
from langchain_core.tools import tool, BaseTool
from database import get_db_cursor_async
from starlette.concurrency import run_in_threadpool
import httpx

logger = logging.getLogger(__name__)

async def get_oauth_token(user_id: str, provider: str) -> str:
    """Helper to fetch the OAuth token for a specific user and provider."""
    async with get_db_cursor_async(commit=False) as cursor:
        await run_in_threadpool(
            cursor.execute,
            "SELECT access_token FROM oauth_connections WHERE user_id = %s AND provider = %s",
            (user_id, provider)
        )
        row = await run_in_threadpool(cursor.fetchone)
        if row:
            return row[0]
        return None

def create_native_tools(user_id: str, allowed_integrations: List[str]) -> List[BaseTool]:
    """
    Creates LangChain tools for native integrations (GitHub, Slack, etc.) 
    that are explicitly enabled for the agent.
    """
    tools = []

    if "github" in allowed_integrations:
        @tool(name="github_create_issue")
        async def github_create_issue(repo: str, title: str, body: str) -> str:
            """
            Create a GitHub issue in a specified repository (format: owner/repo).
            Only use this if you have explicit information about the bug/task.
            """
            token = await get_oauth_token(user_id, "github")
            if not token:
                return "Error: User has not connected their GitHub account via OAuth."
            
            url = f"https://api.github.com/repos/{repo}/issues"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {"title": title, "body": body}
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 201:
                        data = resp.json()
                        return f"Successfully created GitHub issue: {data.get('html_url')}"
                    else:
                        return f"Failed to create issue. Status: {resp.status_code}. Response: {resp.text}"
            except Exception as e:
                return f"Error connecting to GitHub API: {e}"

        tools.append(github_create_issue)

    if "slack" in allowed_integrations:
        @tool(name="slack_send_message")
        async def slack_send_message(channel: str, text: str) -> str:
            """
            Send a message to a specific Slack channel.
            The channel parameter can be a channel ID (e.g. C12345) or name (e.g. #general).
            """
            token = await get_oauth_token(user_id, "slack")
            if not token:
                return "Error: User has not connected their Slack account via OAuth."
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {"channel": channel, "text": text}
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()
                    if data.get("ok"):
                        return f"Successfully sent message to Slack channel {channel}."
                    else:
                        return f"Failed to send Slack message: {data.get('error')}"
            except Exception as e:
                return f"Error connecting to Slack API: {e}"
                
        tools.append(slack_send_message)

    return tools
