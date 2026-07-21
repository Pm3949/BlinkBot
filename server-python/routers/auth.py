import logging
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from schemas import UserRegister, VerifyOTP, UserLogin, ForgotPassword, ResetPassword, Login2FA
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/google/login")
async def google_login(request: Request):
    """
    What it does: HTTP endpoint to initiate Google OAuth login.
    Args:
        request (Request): The incoming request.
    Returns: A redirect to the Google consent screen.
    """
    base_url = str(request.base_url).rstrip("/")
    auth_url = await handle_google_login(base_url)
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    """
    What it does: HTTP endpoint that Google redirects back to after user consent.
    Args:
        request (Request): The incoming request.
        code (str): The OAuth code.
    Returns: A redirect to the frontend with the access token.
    """
    base_url = str(request.base_url).rstrip("/")
    request_url = str(request.url)
    redirect_url = await handle_google_callback(base_url, request_url, code)
    return RedirectResponse(redirect_url)


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister):
    """
    What it does: HTTP endpoint to register a new user and trigger an OTP email.
    Args:
        request (Request): The incoming request.
        payload (UserRegister): The user's registration details.
    Returns: A success message.
    """
    return await handle_register(payload.email, payload.password)


@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, payload: VerifyOTP):
    """
    What it does: HTTP endpoint to verify the email OTP during registration.
    Args:
        request (Request): The incoming request.
        payload (VerifyOTP): The OTP details.
    Returns: The access token and user info.
    """
    return await handle_verify_otp(payload.email, payload.otp)


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin):
    """
    What it does: HTTP endpoint to log a user in.
    Args:
        request (Request): The incoming request.
        payload (UserLogin): The login details.
    Returns: The access token or a 2FA requirement flag.
    """
    return await handle_login(payload.email, payload.password)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, payload: ForgotPassword):
    """
    What it does: HTTP endpoint to trigger a password reset email.
    Args:
        request (Request): The incoming request.
        payload (ForgotPassword): The user's email.
    Returns: A generic success message.
    """
    return await handle_forgot_password(payload.email)


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPassword):
    """
    What it does: HTTP endpoint to finalize a password reset.
    Args:
        request (Request): The incoming request.
        payload (ResetPassword): The reset details.
    Returns: A success message.
    """
    return await handle_reset_password(payload.email, payload.token, payload.new_password)


@router.post("/2fa/setup")
async def setup_2fa(request: Request, payload: dict):
    """
    What it does: HTTP endpoint to generate a new 2FA setup QR code/URI.
    Args:
        request (Request): The incoming request.
        payload (dict): The user ID.
    Returns: The provisioning URI and secret.
    """
    return await handle_setup_2fa(payload.get("user_id"))


@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: Request, payload: dict):
    """
    What it does: HTTP endpoint to verify the first 2FA code and finalize setup.
    Args:
        request (Request): The incoming request.
        payload (dict): The user ID and TOTP code.
    Returns: A success message.
    """
    return await handle_verify_2fa_setup(payload.get("user_id"), payload.get("totp_code"))


@router.post("/login/2fa")
@limiter.limit("5/minute")
async def login_2fa(request: Request, payload: Login2FA):
    """
    What it does: HTTP endpoint to process a 2FA login attempt.
    Args:
        request (Request): The incoming request.
        payload (Login2FA): The login details.
    Returns: The access token and user info.
    """
    return await handle_login_2fa(payload.user_id, payload.totp_code)

@router.post("/2fa/disable")
async def disable_2fa(request: Request, payload: dict):
    """
    What it does: HTTP endpoint to disable 2FA.
    Args:
        request (Request): The incoming request.
        payload (dict): The user ID.
    Returns: A success message.
    """
    return await handle_disable_2fa(payload.get("user_id"))
