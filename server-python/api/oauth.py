"""
================================================================================
NATIVE INTEGRATIONS OAUTH ROUTER LAYER (oauth.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for third-party native integrations
via OAuth 2.0 (specifically GitHub and Slack). It handles:
1. Redirection: Redirects users to external authorization screens (e.g. GitHub OAuth).
2. Callback Verification: Receives the authorization response, verifies it against the SSO provider,
   extracts access tokens, and updates integration links in the database.
3. Interactive Popup closure: Serves a lightweight HTML script response to close authorization popup windows
   and notify the parent window of success.

DATABASE INTEGRATION:
- Stored tokens are upserted into the `oauth_connections` table.
- If a connection already exists for a user-provider pair, the database updates the existing token values
  and updates the modification timestamp.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import os
import logging
from utils.logger import get_department_logger
from core.database import get_db_cursor_async
from starlette.concurrency import run_in_threadpool
from fastapi_sso.sso.github import GithubSSO

# Define SlackSSO placeholder for extension.
SlackSSO = None

# Initialize router instance for OAuth paths.
router = APIRouter()
# Initialize standard module-level logger.
logger = get_department_logger("auth")

# Initialize GitHub SSO client parameters.
github_sso = GithubSSO(
    client_id=os.getenv("GITHUB_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/github/callback",
    allow_insecure_http=True # True simplifies local dev testing (no HTTPS required)
) if GithubSSO else None

# Initialize Slack SSO client (currently disabled).
slack_sso = SlackSSO(
    client_id=os.getenv("SLACK_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("SLACK_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/slack/callback",
    allow_insecure_http=True
) if SlackSSO else None


# ==========================================
# HELPER DATA WRITERS
# ==========================================

async def save_oauth_token(user_id: str, provider: str, access_token: str, refresh_token: str = None):
    """
    Saves or updates OAuth credentials in the database.

    Purpose:
        Upserts the access and refresh tokens into the `oauth_connections` table.
        Uses `ON CONFLICT (user_id, provider)` to update existing connections instead of throwing errors.

    Parameters:
        user_id (str): UUID of the user.
        provider (str): Name of the integration provider (e.g. 'github', 'slack').
        access_token (str): Google/GitHub API access token string.
        refresh_token (str, optional): Google/GitHub refresh token string.

    Returns:
        None.

    Side Effects / State Changes:
        - Writes or updates a row in the `oauth_connections` table.

    Errors / Exceptions:
        - May raise database execution or connection exceptions.
    """
    # Open an async transaction connection context.
    async with get_db_cursor_async(commit=True) as cursor:
        # Run database operations concurrently using threadpools.
        await run_in_threadpool(
            cursor.execute,
            """
            INSERT INTO oauth_connections (user_id, provider, access_token, refresh_token)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, provider) DO UPDATE 
            SET access_token = EXCLUDED.access_token, 
                refresh_token = EXCLUDED.refresh_token,
                updated_at = timezone('utc'::text, now());
            """,
            (user_id, provider, access_token, refresh_token)
        )


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/github/login")
async def github_login():
    """
    Initiates the GitHub OAuth authorization flow.

    Purpose:
        Redirects the user to the GitHub authorization screen to request permissions.

    Parameters:
        None.

    Returns:
        RedirectResponse: Redirection to the GitHub login portal.

    Errors / Exceptions:
        - Raises 501 Not Implemented if the SSO client is unconfigured or missing dependencies.
    """
    # Guard check: verify the SSO client is initialized.
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed or GithubSSO missing")
    # Redirect the user to the GitHub login page.
    with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/github/callback")
async def github_callback(request: Request):
    """
    Handles callbacks from GitHub OAuth.

    Purpose:
        Exchanges the authorization code for tokens, saves them,
        and returns an HTML page that closes the popup window and notifies the parent.

    Parameters:
        request (Request): The callback HTTP request containing authorization codes.

    Returns:
        HTMLResponse: A script that closes the popup window.

    Side Effects / State Changes:
        - Stores the access token in `oauth_connections`.

    Errors / Exceptions:
        - Raises 400 Bad Request if token verification fails.
    """
    # Guard check.
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed")
    try:
        # Verify the authorization code and retrieve user profile info.
        with github_sso:
            user = await github_sso.verify_and_process(request)
            
            # Extract user ID from request headers.
            # Fall back to 'default_user' if missing.
            ragmate_user_id = request.headers.get("X-User-Id", "default_user") 
            
            # Extract the raw access token from the user object.
            access_token = getattr(user, "access_token", "mock_gh_token")
            
            # Save the tokens to the database.
            await save_oauth_token(ragmate_user_id, "github", access_token)
            
            # Return an HTML page containing JavaScript to close the popup
            # and notify the parent window of success.
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content='''
                <html>
                    <head><title>OAuth Success</title></head>
                    <body>
                        <script>
                            if (window.opener) {
                                window.opener.postMessage("oauth_success", "*");
                            }
                            window.close();
                        </script>
                        <p>Authentication successful! You can close this window.</p>
                    </body>
                </html>
            ''')
    except Exception as e:
        logger.error(f"GitHub callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@router.get("/slack/login")
async def slack_login():
    """
    Initiates the Slack OAuth authorization flow.
    """
    client_id = os.getenv("SLACK_CLIENT_ID", "mock_slack_id")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/slack/callback"
    slack_scopes = "chat:write,commands,channels:read,groups:read,im:read,mpim:read"
    url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&user_scope={slack_scopes}"
    )
    return RedirectResponse(url)


@router.get("/slack/callback")
async def slack_callback(code: str, request: Request):
    """
    Handles callbacks from Slack OAuth.
    """
    client_id = os.getenv("SLACK_CLIENT_ID", "mock_slack_id")
    client_secret = os.getenv("SLACK_CLIENT_SECRET", "mock_slack_secret")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/slack/callback"
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Slack OAuth token exchange failed: {data}")
                raise HTTPException(status_code=400, detail=f"Slack authentication failed: {data.get('error')}")
            access_token = data.get("access_token") or data.get("authed_user", {}).get("access_token")
            ragmate_user_id = request.headers.get("X-User-Id", "default_user")
            await save_oauth_token(ragmate_user_id, "slack", access_token)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content='''
                <html>
                    <head><title>OAuth Success</title></head>
                    <body>
                        <script>
                            if (window.opener) {
                                window.opener.postMessage("oauth_success", "*");
                            }
                            window.close();
                        </script>
                        <p>Slack authentication successful! You can close this window.</p>
                    </body>
                </html>
            ''')
    except Exception as e:
        logger.error(f"Slack callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")


@router.get("/jira/login")
async def jira_login():
    """
    Initiates the Jira OAuth authorization flow.
    """
    client_id = os.getenv("JIRA_CLIENT_ID", "mock_jira_id")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/jira/callback"
    scopes = "read:jira-work write:jira-work"
    url = (
        f"https://auth.atlassian.com/authorize"
        f"?audience=api.atlassian.com"
        f"&client_id={client_id}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state=atlassian_auth"
        f"&response_type=code"
        f"&prompt=consent"
    )
    return RedirectResponse(url)


@router.get("/jira/callback")
async def jira_callback(code: str, request: Request):
    """
    Handles callbacks from Jira OAuth.
    """
    client_id = os.getenv("JIRA_CLIENT_ID", "mock_jira_id")
    client_secret = os.getenv("JIRA_CLIENT_SECRET", "mock_jira_secret")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/jira/callback"
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            data = resp.json()
            if "access_token" not in data:
                logger.error(f"Jira OAuth token exchange failed: {data}")
                raise HTTPException(status_code=400, detail="Jira authentication failed")
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            ragmate_user_id = request.headers.get("X-User-Id", "default_user")
            await save_oauth_token(ragmate_user_id, "jira", access_token, refresh_token)
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content='''
                <html>
                    <head><title>OAuth Success</title></head>
                    <body>
                        <script>
                            if (window.opener) {
                                window.opener.postMessage("oauth_success", "*");
                            }
                            window.close();
                        </script>
                        <p>Jira authentication successful! You can close this window.</p>
                    </body>
                </html>
            ''')
    except Exception as e:
        logger.error(f"Jira callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

