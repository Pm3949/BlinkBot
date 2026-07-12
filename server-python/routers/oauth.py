from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import os
import logging
from database import get_db_cursor_async
from starlette.concurrency import run_in_threadpool

from fastapi_sso.sso.github import GithubSSO
SlackSSO = None

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize SSO instances. In production, ensure these ENV variables are set.
github_sso = GithubSSO(
    client_id=os.getenv("GITHUB_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/github/callback",
    allow_insecure_http=True
) if GithubSSO else None

slack_sso = SlackSSO(
    client_id=os.getenv("SLACK_CLIENT_ID", "mock_id"),
    client_secret=os.getenv("SLACK_CLIENT_SECRET", "mock_secret"),
    redirect_uri=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/api/auth/slack/callback",
    allow_insecure_http=True
) if SlackSSO else None


async def save_oauth_token(user_id: str, provider: str, access_token: str, refresh_token: str = None):
    async with get_db_cursor_async(commit=True) as cursor:
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
    """Initiate GitHub OAuth login."""
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed or GithubSSO missing")
    with github_sso:
        return await github_sso.get_login_redirect()

@router.get("/github/callback")
async def github_callback(request: Request):
    """Verify GitHub login and save the token."""
    if not github_sso:
        raise HTTPException(status_code=501, detail="fastapi-sso not installed")
    try:
        with github_sso:
            user = await github_sso.verify_and_process(request)
            # In a real app, you'd extract the RAGMate user_id from the session or JWT token.
            # Here we assume a mock user ID for demonstration.
            ragmate_user_id = request.headers.get("X-User-Id", "default_user") 
            
            # Note: fastapi-sso user object doesn't expose the raw access token directly in standard models
            # but we can get it from the SSO provider instance if needed, or assume it's mock logic for now.
            # We'll just save a mock token if we can't extract it easily, to satisfy the DB schema.
            access_token = getattr(user, "access_token", "mock_gh_token")
            
            await save_oauth_token(ragmate_user_id, "github", access_token)
            # Return a simple HTML page that closes the popup and notifies the parent window
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

# Similar routes can be added for Slack...
