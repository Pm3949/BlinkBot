"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all External Single Sign-On
(SSO) and OAuth 2.0 connection configurations in the RAGMate backend. It maps
incoming HTTP REST requests directly to the underlying OAuth libraries (fastapi-sso)
and handles token database storage.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard OS libraries, logging modules, FastAPI routing structures,
   database transactional context managers, threadpool runners, and SSO provider SDKs.
2. SSO Instances Initialization: Initializes SSO clients (GitHubSSO and SlackSSO placeholders)
   with client credentials, redirect callbacks, and debugging configurations.
3. Database Utility (`save_oauth_token`): Inserts or updates (Upsert) OAuth access tokens
   and refresh tokens in the `oauth_connections` table.
4. HTTP Routes:
   - GET `/github/login`: Initiates authorization redirect handshakes to GitHub.
   - GET `/github/callback`: Receives callbacks, trades codes for tokens, registers connection
     records in the DB, and dispatches JS messages to close popups.
"""

from fastapi import APIRouter, Depends, HTTPException, Request  # FastAPI core routing components
from fastapi.responses import RedirectResponse  # HTTP Redirection responses
import os  # Read system environment parameters (Client IDs, secrets, callback domains)
import logging  # Import python logging library
from database import get_db_cursor_async  # Async database cursor connection context managers
from starlette.concurrency import run_in_threadpool  # Run blocking DB commands inside background threads

# Import fastapi-sso integrations
from fastapi_sso.sso.github import GithubSSO
SlackSSO = None  # Placeholder definition for Slack integrations (not implemented)

# Initialize FastAPI router for OAuth endpoints
router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize GitHub SSO client instance. Allow insecure HTTP for local dev.
github_sso = GithubSSO(
    client_id=os.getenv("GITHUB_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/github/callback",
    allow_insecure_http=True
) if GithubSSO else None

# Initialize Slack SSO client instance (if SlackSSO is implemented)
slack_sso = SlackSSO(
    client_id=os.getenv("SLACK_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("SLACK_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/slack/callback",
    allow_insecure_http=True
) if SlackSSO else None


async def save_oauth_token(user_id: str, provider: str, access_token: str, refresh_token: str = None):
    """
    Saves or updates OAuth credentials in the `oauth_connections` database table.
    Uses an UPSERT (insert or update on conflict) statement to prevent duplicate rows.

    Parameters:
        user_id (str): The unique database user UUID.
        provider (str): Name of the OAuth provider (e.g., 'github', 'slack').
        access_token (str): The retrieved access token.
        refresh_token (str, optional): The retrieved refresh token.

    Returns:
        None: Executes database writes.

    Exceptions Raised:
        Exception: Propagated if SQL execution crashes.
    """
    # Open transactional database cursor connection
    async with get_db_cursor_async(commit=True) as cursor:
        # Run blocking SQL code in threadpool to prevent blocking the event loop
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


@router.get("/github/login")
async def github_login():
    """
    HTTP GET endpoint initiating the GitHub OAuth 2.0 authorization redirect.

    Parameters:
        None

    Returns:
        RedirectResponse: Directs browser to GitHub's authorization consent screen.

    Exceptions Raised:
        HTTPException(501): Raised if GithubSSO is missing or disabled.
    """
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed or GithubSSO missing")
    with github_sso:
        # Retrieve the formatted redirect URL
        return await github_sso.get_login_redirect()


@router.get("/github/callback")
async def github_callback(request: Request):
    """
    HTTP GET callback endpoint that GitHub redirects back to after user consent.
    Exchanges codes for tokens, registers connection records in the DB, and returns
    HTML scripts to notify the dashboard frontend and close login popups.

    Parameters:
        request (Request): The incoming HTTP request payload context.

    Returns:
        HTMLResponse: JavaScript-based popup closure page.

    Exceptions Raised:
        HTTPException(400): Raised if OAuth validation fails.
        HTTPException(501): Raised if GitHub SSO is missing.
    """
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed")
    try:
        with github_sso:
            # Process parameters and verify token exchange
            user = await github_sso.verify_and_process(request)
            
            # Extract user ID from header context (fallback to default)
            ragmate_user_id = request.headers.get("X-User-Id", "default_user") 
            
            # Extract token parameters
            access_token = getattr(user, "access_token", "mock_gh_token")
            
            # Save token to database
            await save_oauth_token(ragmate_user_id, "github", access_token)
            
            # Import HTMLResponse dynamically to return popup closure script page
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content='''
                <html>
                    <head><title>OAuth Success</title></head>
                    <body>
                        <script>
                            // Notify parent window that authentication succeeded
                            if (window.opener) {
                                window.opener.postMessage("oauth_success", "*");
                            }
                            // Close popup
                            window.close();
                        </script>
                        <p>Authentication successful! You can close this window.</p>
                    </body>
                </html>
            ''')
    except Exception as e:
        logger.error(f"GitHub callback error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")
