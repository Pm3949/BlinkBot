"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script acts as the HTTP routing entry point for all Authentication and User Registry
actions in the RAGMate backend. It maps incoming HTTP REST requests directly to the
underlying business logic executors defined inside the authentication handler modules.

From top to bottom, the file performs the following tasks:
1. Imports: Loads standard logging controllers, FastAPI routing modules and responses,
   slowapi Limiter modules (rate-limiting protections), schema definitions, and auth handlers.
2. Routing & Limiter Initializations: Declares the APIRouter with prefix '/auth' and tags.
   Initializes slowapi Limiter using client IP addresses as key parameters (`get_remote_address`).
3. HTTP Auth Endpoints:
   - Google Login (`google_login` & `google_callback`): Initiates consent and receives code.
   - User Registration (`register` & `verify_otp`): Formulates registration entries and validates email OTPs.
   - User Login (`login` & `login_2fa`): Authenticates credentials or processes TOTP verification tokens.
   - Password Resets (`forgot_password` & `reset_password`): Dispatches reset emails and updates passwords.
   - 2FA Configuration (`setup_2fa`, `verify_2fa_setup`, `disable_2fa`): Configures or disables Authenticator TOTP.
"""

import logging  # Import python logging library
from fastapi import APIRouter, Request  # FastAPI APIRouter and Request parsing structures
from fastapi.responses import RedirectResponse  # HTTP Redirection responses
from slowapi import Limiter  # Import slowapi for HTTP rate-limiting protections
from slowapi.util import get_remote_address  # Rate limit key utility matching remote client IP addresses

# Input validation schemas
from schemas import UserRegister, VerifyOTP, UserLogin, ForgotPassword, ResetPassword, Login2FA

# Import authentication logic handlers
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

# Instantiate a scoped file logger
logger = logging.getLogger(__name__)

# Initialize FastAPI router with prefix "/auth" and grouping tags
router = APIRouter(prefix="/auth", tags=["auth"])
# Instantiate rate-limiter wrapper using remote client IP as unique constraint key
limiter = Limiter(key_func=get_remote_address)


@router.get("/google/login")
async def google_login(request: Request):
    """
    HTTP GET endpoint to initiate Google OAuth 2.0 login redirect.

    Parameters:
        request (Request): The incoming HTTP request payload context.

    Returns:
        RedirectResponse: Directs client browser to Google's OAuth consent screen.

    Exceptions Raised:
        HTTPException(500): Raised if OAuth client configuration is missing.
    """
    base_url = str(request.base_url).rstrip("/")  # Extract the backend base URL dynamically
    auth_url = await handle_google_login(base_url)  # Fetch the formatted redirect URL
    return RedirectResponse(auth_url)  # Return Redirect Response (HTTP 307 Temporary Redirect)


@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    """
    HTTP GET callback endpoint that Google redirects back to after user consent.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        code (str): The authorization code returned by Google.

    Returns:
        RedirectResponse: Directs the client browser back to the frontend with access tokens.

    Exceptions Raised:
        HTTPException(500): Raised if token exchange with Google fails.
    """
    base_url = str(request.base_url).rstrip("/")  # Fetch base url dynamically
    request_url = str(request.url)  # Fetch full request path url (required for callback validation matching)
    redirect_url = await handle_google_callback(base_url, request_url, code)  # Trade code for access tokens
    return RedirectResponse(redirect_url)  # Redirect client back to frontend dashboard


@router.post("/register")
@limiter.limit("5/minute")  # Limit submissions to 5 attempts per minute per IP address
async def register(request: Request, payload: UserRegister):
    """
    HTTP POST endpoint to register a new user and dispatch registration email OTP.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (UserRegister): Pydantic-validated request payload.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400): Raised if user email already exists.
        HTTPException(500): Raised if database inserts crash.
    """
    return await handle_register(payload.email, payload.password)  # Route task execution to handlers layer


@router.post("/verify-otp")
@limiter.limit("5/minute")  # Limit submissions to 5 attempts per minute per IP address
async def verify_otp(request: Request, payload: VerifyOTP):
    """
    HTTP POST endpoint to verify registration email OTP.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (VerifyOTP): Pydantic-validated request payload.

    Returns:
        dict: A dictionary containing JWT access token and user information.

    Exceptions Raised:
        HTTPException(400): Raised if OTP is incorrect or expired.
        HTTPException(500): Raised if verification crashes.
    """
    return await handle_verify_otp(payload.email, payload.otp)  # Route task execution to handlers layer


@router.post("/login")
@limiter.limit("10/minute")  # Limit logins to 10 attempts per minute per IP address
async def login(request: Request, payload: UserLogin):
    """
    HTTP POST endpoint to log a user in.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (UserLogin): Pydantic-validated request payload.

    Returns:
        dict: JWT access token details, or 2FA verification requirement challenge flags.

    Exceptions Raised:
        HTTPException(401): Raised if credentials check fails.
        HTTPException(500): Raised if login query crashes.
    """
    return await handle_login(payload.email, payload.password)  # Route task execution to handlers layer


@router.post("/forgot-password")
@limiter.limit("3/minute")  # Limit reset email requests to 3 attempts per minute per IP address
async def forgot_password(request: Request, payload: ForgotPassword):
    """
    HTTP POST endpoint to request a password reset email token.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (ForgotPassword): Pydantic-validated request payload.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if mail systems or database token saves fail.
    """
    return await handle_forgot_password(payload.email)  # Route task execution to handlers layer


@router.post("/reset-password")
@limiter.limit("5/minute")  # Limit submissions to 5 attempts per minute per IP address
async def reset_password(request: Request, payload: ResetPassword):
    """
    HTTP POST endpoint to execute password reset using verification tokens.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (ResetPassword): Pydantic-validated request payload.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(400): Raised if token is invalid or expired.
        HTTPException(500): Raised if update transactions crash.
    """
    # Route execution to handlers layer
    return await handle_reset_password(payload.email, payload.token, payload.new_password)


@router.post("/2fa/setup")
async def setup_2fa(request: Request, payload: dict):
    """
    HTTP POST endpoint to generate 2FA configuration provisioning URI QR code.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (dict): A dictionary payload containing 'user_id'.

    Returns:
        dict: A dictionary containing the provisioning URI string.

    Exceptions Raised:
        HTTPException(500): Raised if 2FA setups crash.
    """
    return await handle_setup_2fa(payload.get("user_id"))  # Route task execution to handlers layer


@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: Request, payload: dict):
    """
    HTTP POST endpoint to verify first setup verification TOTP code and enable 2FA status.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (dict): A dictionary payload containing 'user_id' and 'totp_code'.

    Returns:
        dict: Status confirmation message payload.

    Exceptions Raised:
        HTTPException(400): Raised if TOTP code check fails.
        HTTPException(500): Raised if updates fail.
    """
    # Route execution to handlers layer
    return await handle_verify_2fa_setup(payload.get("user_id"), payload.get("totp_code"))


@router.post("/login/2fa")
@limiter.limit("5/minute")  # Limit verification attempts to 5 attempts per minute per IP address
async def login_2fa(request: Request, payload: Login2FA):
    """
    HTTP POST endpoint to authenticate 2FA login challenge TOTP codes.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (Login2FA): Pydantic-validated request payload.

    Returns:
        dict: A dictionary containing JWT access token and user information.

    Exceptions Raised:
        HTTPException(401): Raised if TOTP code verification fails.
        HTTPException(500): Raised if logins crash.
    """
    return await handle_login_2fa(payload.user_id, payload.totp_code)  # Route task execution to handlers layer


@router.post("/2fa/disable")
async def disable_2fa(request: Request, payload: dict):
    """
    HTTP POST endpoint to disable 2FA authentication requirements.

    Parameters:
        request (Request): The incoming HTTP request payload context.
        payload (dict): A dictionary payload containing 'user_id'.

    Returns:
        dict: A confirmation message dictionary.

    Exceptions Raised:
        HTTPException(500): Raised if database updates crash.
    """
    return await handle_disable_2fa(payload.get("user_id"))  # Route task execution to handlers layer
