"""
================================================================================
AUTHENTICATION AND AUTHORIZATION ROUTER LAYER (auth.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the FastAPI endpoint router for all authentication processes.
It implements:
1. Native Email/Password flows: Handles registration, OTP validation, logins, and resets.
2. Google OAuth Integration: Redirects users to Google's consent screen and processes callbacks,
   supporting dynamic frontend redirection via the OAuth `state` parameter to handle both local development (localhost) and production environments securely.
3. Two-Factor Authentication (2FA): Handles provisioning QR code URIs, TOTP verification, and disabling.
4. Security Rate Limiting: Uses `slowapi` to restrict request frequency on authentication endpoints
   (e.g., limiting login attempts to prevent brute-force attacks).

DATA FLOW:
- Clients query authentication paths. Pydantic validator schemas check input formats.
- The router applies the slowapi `@limiter.limit` decorator to prevent request spam.
- Processing is delegated to `handlers/auth_handler.py`, which handles database operations,
  SMTP email delivery, and JWT signature generation.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import Pydantic validation schemas.
from schemas import UserRegister, VerifyOTP, UserLogin, ForgotPassword, ResetPassword, Login2FA
# Import authentication business logic handlers.
from handlers.auth_handler import (
    handle_google_login,
    handle_google_callback,
    handle_register,
    handle_verify_otp,
    handle_login,
    handle_forgot_password,
    handle_reset_password,
    handle_setup_2fa,
    handle_verify_2fa_setup,
    handle_login_2fa,
    handle_disable_2fa
)

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)

# Initialize router with tags for automated Swagger documentation.
router = APIRouter(prefix="/auth", tags=["auth"])
# Initialize rate limiter using client IP addresses.
limiter = Limiter(key_func=get_remote_address)


# ==========================================
# ENDPOINT IMPLEMENTATIONS
# ==========================================

@router.get("/google/login")
async def google_login(request: Request, state: str = None):
    """
    Initiates Google OAuth authorization flows.

    Purpose:
        Constructs the Google OAuth request URL and redirects the client's browser.

    Parameters:
        request (Request): The incoming HTTP request.
        state (str, optional): The state parameter to preserve frontend origin context.

    Returns:
        RedirectResponse: A redirect to the Google consent screen.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - None.
    """
    # Extract the protocol and hostname (e.g. 'https://api.blinkbot.com') to formulate redirection URLs.
    base_url = str(request.base_url).rstrip("/")
    # Retrieve the Google consent screen redirection URL from the handler.
    auth_url = await handle_google_login(base_url, state)
    # Redirect the client's browser to the Google OAuth page.
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str = None):
    """
    Processes OAuth callbacks from Google.

    Purpose:
        Exchanges the authorization code for user profile info, registers new users,
        and redirects to the frontend with an access token.

    Parameters:
        request (Request): The incoming callback HTTP request.
        code (str): The Google authorization code.
        state (str, optional): The state parameter containing the frontend redirect URL.

    Returns:
        RedirectResponse: A redirect to the frontend application dashboard.

    Side Effects / State Changes:
        - Creates a new user record if this is their first login.
        - Records OAuth credentials.

    Errors / Exceptions:
        - Raises 400 Bad Request if the authorization code is invalid or expired.
    """
    # Format the root application URL.
    base_url = str(request.base_url).rstrip("/")
    # Get the full URL requested by Google to verify callback parameters.
    request_url = str(request.url)
    # Exchange the code for an access token and get the frontend redirect URL.
    redirect_url = await handle_google_callback(base_url, request_url, code, state)
    # Redirect the user to the frontend application.
    return RedirectResponse(redirect_url)


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister):
    """
    Registers a new email/password account.

    Purpose:
        Creates a pending user profile and sends a 6-digit verification OTP email.
        This endpoint is rate-limited to 5 requests per minute per IP address.

    Parameters:
        request (Request): The incoming request. Required by the rate limiter.
        payload (UserRegister): The user's registration details.

    Returns:
        dict: Success status and message.

    Side Effects / State Changes:
        - Writes a pending user record to the database.
        - Sends a verification email.

    Errors / Exceptions:
        - Raises 400 Bad Request if the email is already registered.
    """
    # Delegate registration processing to the authentication handler.
    return await handle_register(payload.email, payload.password)


@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, payload: VerifyOTP):
    """
    Verifies the email registration OTP.

    Purpose:
        Checks the OTP code and activates the user account.
        This endpoint is rate-limited to 5 requests per minute per IP.

    Parameters:
        request (Request): The incoming request.
        payload (VerifyOTP): The OTP code and target email address.

    Returns:
        dict: The signed JWT access token and user metadata.

    Side Effects / State Changes:
        - Updates the user's status to active in the database.

    Errors / Exceptions:
        - Raises 400 Bad Request if the OTP is invalid or expired.
    """
    # Verify the code using the handler.
    return await handle_verify_otp(payload.email, payload.otp)


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin):
    """
    Authenticates email and password credentials.

    Purpose:
        Logs in the user. If 2FA is enabled, returns a flag prompting for the TOTP code
        instead of the JWT.
        This endpoint is rate-limited to 10 requests per minute per IP.

    Parameters:
        request (Request): The incoming request.
        payload (UserLogin): The login details.

    Returns:
        dict: JWT credentials or a 2FA prompt flag.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Raises 401 Unauthorized if credentials do not match.
    """
    # Authenticate credentials using the handler.
    return await handle_login(payload.email, payload.password)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, payload: ForgotPassword):
    """
    Initiates the password recovery flow.

    Purpose:
        Generates a password recovery OTP and sends it via email.
        This endpoint is rate-limited to 3 requests per minute per IP.

    Parameters:
        request (Request): The incoming request.
        payload (ForgotPassword): The target email address.

    Returns:
        dict: Generic success confirmation message.

    Side Effects / State Changes:
        - Generates a temporary reset code.
        - Sends a recovery email.

    Errors / Exceptions:
        - None. Returns a success message even if the email does not exist to prevent account enumeration.
    """
    # Process password recovery through the handler.
    return await handle_forgot_password(payload.email)


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPassword):
    """
    Resets a user's password.

    Purpose:
        Updates the password in the database after validating the recovery code.
        This endpoint is rate-limited to 5 requests per minute per IP.

    Parameters:
        request (Request): The incoming request.
        payload (ResetPassword): Contains the email, recovery token, and new password.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Updates the user's password hash in the database.

    Errors / Exceptions:
        - Raises 400 Bad Request if the token is invalid or expired.
    """
    # Reset the password using the handler.
    return await handle_reset_password(payload.email, payload.token, payload.new_password)


@router.post("/2fa/setup")
async def setup_2fa(request: Request, payload: dict):
    """
    Initiates 2FA setup.

    Purpose:
        Generates a new TOTP secret key and returns a QR code provisioning URI.

    Parameters:
        request (Request): The incoming request.
        payload (dict): A dictionary containing `user_id`.

    Returns:
        dict: The secret key and provisioning URI.

    Side Effects / State Changes:
        - Generates a temporary TOTP key.

    Errors / Exceptions:
        - Raises 400 Bad Request if the user ID is missing.
    """
    # Generate setup configurations.
    return await handle_setup_2fa(payload.get("user_id"))


@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: Request, payload: dict):
    """
    Finalizes 2FA setup.

    Purpose:
        Verifies the first TOTP code to confirm correct scanner configuration
        before enabling 2FA.

    Parameters:
        request (Request): The incoming request.
        payload (dict): A dictionary containing `user_id` and `totp_code`.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Toggles the `two_factor_enabled` flag to True in the database.

    Errors / Exceptions:
        - Raises 400 Bad Request if the verification code is invalid.
    """
    # Verify and enable 2FA.
    return await handle_verify_2fa_setup(payload.get("user_id"), payload.get("totp_code"))


@router.post("/login/2fa")
@limiter.limit("5/minute")
async def login_2fa(request: Request, payload: Login2FA):
    """
    Authenticates a 2FA TOTP code during login.

    Purpose:
        Verifies the 2FA code and issues the JWT access token.
        This endpoint is rate-limited to 5 requests per minute per IP.

    Parameters:
        request (Request): The incoming request.
        payload (Login2FA): Contains the user ID and TOTP code.

    Returns:
        dict: JWT credentials.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Raises 401 Unauthorized if verification fails.
    """
    # Process 2FA login using the handler.
    return await handle_login_2fa(payload.user_id, payload.totp_code)


@router.post("/2fa/disable")
async def disable_2fa(request: Request, payload: dict):
    """
    Disables 2FA for a user.

    Purpose:
        Disables 2FA and deletes the TOTP secret key.

    Parameters:
        request (Request): The incoming request.
        payload (dict): A dictionary containing `user_id`.

    Returns:
        dict: Success status message.

    Side Effects / State Changes:
        - Deletes the TOTP secret key and sets `two_factor_enabled` to False in the database.

    Errors / Exceptions:
        - Raises 400 Bad Request if the user ID is missing.
    """
    # Disable 2FA.
    return await handle_disable_2fa(payload.get("user_id"))

