import secrets
import pyotp
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException
from urllib.parse import urlencode

from core.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    send_otp_email, 
    send_password_reset_email,
    GOOGLE_CLIENT_ID, 
    GOOGLE_CLIENT_SECRET, 
    FRONTEND_URL
)
from db import auth_repository, workspace_repository
from utils.logger import get_department_logger

logger = get_department_logger("auth")

def generate_otp():
    logger.debug("Generating secure 6-digit OTP...")
    otp = str(secrets.randbelow(900000) + 100000)
    logger.debug("Successfully generated a new OTP.")
    return otp

async def handle_google_login(base_url: str):
    logger.info(f"Initiating Google login process with base_url: {base_url}")
    if not GOOGLE_CLIENT_ID:
        logger.error("Google Auth configuration failure: GOOGLE_CLIENT_ID is not configured")
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    redirect_uri = f"{base_url}/auth/google/callback"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    target_url = f"{auth_url}?{urlencode(params)}"
    logger.debug(f"Generated Google OAuth authorization URL: {target_url}")
    return target_url


async def handle_google_callback(base_url: str, request_url: str, code: str):
    logger.info(f"Handling Google OAuth callback. Request URL: {request_url}")
    if not GOOGLE_CLIENT_SECRET:
        logger.error("Google Auth configuration failure: GOOGLE_CLIENT_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    redirect_uri = f"{base_url}/auth/google/callback"
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    logger.debug(f"Requesting Google OAuth token from: {token_url}")
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        token_data = response.json()
        
        if "error" in token_data:
            logger.error(f"Google token request failed: {token_data.get('error_description')}")
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "Failed to fetch token"))
            
        logger.debug("Successfully retrieved access token from Google.")
        access_token = token_data["access_token"]
        
        logger.debug("Fetching user profile information from Google userinfo endpoint...")
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()
        
    email = user_info.get("email")
    if not email:
        logger.error("Google login failed: Failed to fetch email from user info endpoint.")
        raise HTTPException(status_code=400, detail="Failed to fetch email from Google")
        
    logger.info(f"Google login verified for user email: {email}")
    try:
        logger.debug(f"Querying database for existing user with email: {email}")
        user = await auth_repository.get_user_by_email(email)
        
        if not user:
            logger.info(f"No existing user found for email {email}. Creating a new unverified user...")
            dummy_password_hash = get_password_hash(secrets.token_urlsafe(32))
            user_id = await auth_repository.create_unverified_user(email, dummy_password_hash)
            logger.debug(f"Created unverified user entry with ID: {user_id}")
        else:
            user_id = str(user['id'])
            logger.debug(f"Found existing user with ID: {user_id}. Verifying user status...")
            await auth_repository.verify_user(user_id)
            logger.debug(f"User {user_id} verified successfully.")
            
        logger.debug(f"Ensuring default workspace exists for user ID: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)
        
        logger.info(f"Generating access token for user ID: {user_id}")
        jwt_token = create_access_token(user_id=user_id, email=email)
        
        frontend_redirect = FRONTEND_URL
        if frontend_redirect == "*":
            frontend_redirect = "http://localhost:5173"
        elif "," in frontend_redirect:
            if "localhost" in request_url or "127.0.0.1" in request_url:
                frontend_redirect = "http://localhost:5173"
            else:
                frontend_redirect = "https://blinkbot.in"
                
        redirect_target = f"{frontend_redirect}/auth/callback?token={jwt_token}"
        logger.info(f"Google login success. Redirecting to target: {frontend_redirect}")
        return redirect_target
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Google callback login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_register(email: str, password: str):
    logger.info(f"Registering new user with email: {email}")
    try:
        logger.debug(f"Checking if email {email} is already registered...")
        user = await auth_repository.get_user_by_email(email)
        if user:
            logger.warning(f"Registration rejected: Email {email} already registered")
            raise HTTPException(status_code=400, detail="Email already registered")

        logger.debug("Hashing password and generating OTP...")
        hashed_password = get_password_hash(password)
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        logger.debug(f"Creating user entry with OTP expiring at: {otp_expiry}")
        user_id = await auth_repository.create_user_with_otp(email, hashed_password, otp, otp_expiry)
        
        logger.info(f"Sending verification OTP email to: {email}")
        send_otp_email(email, otp)
        
        logger.info(f"User registration record created successfully. User ID: {user_id}")
        return {"message": "User registered. Please check your email for the OTP.", "user_id": user_id, "requires_otp": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_verify_otp(email: str, otp: str):
    logger.info(f"Verifying registration OTP for email: {email}")
    try:
        logger.debug(f"Retrieving user details for email: {email}")
        user = await auth_repository.get_user_by_email(email)
        if not user:
            logger.warning(f"OTP verification failed: User not found for email: {email}")
            raise HTTPException(status_code=404, detail="User not found")
        if user['is_verified']:
            logger.warning(f"OTP verification rejected: User {email} is already verified")
            raise HTTPException(status_code=400, detail="User already verified")
        if user['otp_secret'] != otp:
            logger.warning(f"OTP verification rejected: Invalid OTP supplied for {email}")
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            logger.warning(f"OTP verification rejected: OTP expired for {email} (expiry: {expiry})")
            raise HTTPException(status_code=400, detail="OTP expired")

        user_id = str(user['id'])
        logger.debug(f"Verification successful. Verifying user {user_id} and clearing registration OTP...")
        await auth_repository.verify_user_and_clear_otp(user_id)
        
        logger.debug(f"Creating default workspace for verified user: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)

        logger.info(f"Generating access token for verified user ID: {user_id}")
        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_login(email: str, password: str):
    logger.info(f"Attempting login for email: {email}")
    try:
        logger.debug(f"Retrieving user details for login email: {email}")
        user = await auth_repository.get_user_by_email(email)
        
        if not user or not verify_password(password, user['password_hash']):
            logger.warning(f"Login failed: Invalid credentials for email: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = str(user['id'])
        logger.debug(f"Credentials valid. Checking verification status for user ID: {user_id}")
        
        if not user['is_verified']:
            logger.info(f"User {email} is unverified. Triggering a new verification OTP...")
            otp = generate_otp()
            otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            await auth_repository.update_user_otp(user_id, otp, otp_expiry)
            send_otp_email(email, otp)
            logger.info(f"Sent new OTP to unverified login user: {email}")
            return {"message": "Account not verified. A new OTP has been sent to your email.", "requires_otp": True}
            
        logger.debug(f"Creating or verifying default workspace for user ID: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)

        if user.get('two_factor_enabled'):
            logger.info(f"Two-factor authentication (2FA) is enabled for user ID: {user_id}. Restricting login.")
            return {"requires_2fa": True, "user_id": user_id}

        logger.info(f"Generating access token for user ID: {user_id}")
        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed with unexpected error for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_forgot_password(email: str):
    logger.info(f"Requesting password reset link for email: {email}")
    try:
        logger.debug(f"Checking if user {email} exists in database...")
        user = await auth_repository.get_user_by_email(email)
        if not user:
            logger.warning(f"Forgot password request: User not found for email: {email}. Silently returning.")
            return {"message": "If that email exists, we've sent a password reset link."}
            
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        logger.debug(f"Updating OTP credentials for password reset. Expiry: {otp_expiry}")
        await auth_repository.update_user_otp(str(user['id']), otp, otp_expiry)
        
        logger.info(f"Sending password reset instructions to email: {email}")
        send_password_reset_email(email, otp)
        
        return {"message": "If that email exists, we've sent a password reset link."}
    except Exception as e:
        logger.error(f"Forgot password request failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_reset_password(email: str, token: str, new_password: str):
    logger.info(f"Resetting password for email: {email}")
    try:
        logger.debug(f"Retrieving user details for email: {email}")
        user = await auth_repository.get_user_by_email(email)
        if not user:
            logger.warning(f"Password reset failed: User not found for email: {email}")
            raise HTTPException(status_code=400, detail="Invalid request")
            
        if user['otp_secret'] != token:
            logger.warning(f"Password reset failed: Invalid reset token supplied for {email}")
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            logger.warning(f"Password reset failed: Reset token expired for {email} (expiry: {expiry})")
            raise HTTPException(status_code=400, detail="OTP expired")
            
        logger.debug(f"Hashing new password for user ID: {user['id']}")
        hashed_password = get_password_hash(new_password)
        await auth_repository.reset_user_password(str(user['id']), hashed_password)
        
        logger.info(f"Password reset successfully for email: {email}")
        return {"message": "Password reset successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_setup_2fa(user_id: str):
    logger.info(f"Setting up 2FA for user ID: {user_id}")
    if not user_id:
        logger.error("Failed to setup 2FA: user_id is missing")
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        logger.debug(f"Checking current 2FA settings status for user: {user_id}")
        settings = await auth_repository.get_user_settings(user_id)
        if settings and settings['two_factor_enabled']:
            logger.warning(f"2FA Setup aborted: 2FA is already enabled for user {user_id}")
            raise HTTPException(status_code=400, detail="2FA already enabled")
            
        logger.debug(f"Retrieving user email for ID: {user_id}")
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            logger.warning(f"2FA Setup failed: User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        logger.debug("Generating random base32 secret for TOTP...")
        secret = pyotp.random_base32()
        settings_exist = bool(settings)
        
        logger.debug(f"Saving TOTP secret in settings. Record exists: {settings_exist}")
        await auth_repository.update_user_totp_secret(user_id, secret, settings_exist)
        
        logger.debug("Generating provisioning URI for authenticator application...")
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="BlinkBot")
        logger.info(f"2FA setup successfully initiated for user {user_id}")
        return {"provisioning_uri": uri, "secret": secret}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup 2FA for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_verify_2fa_setup(user_id: str, totp_code: str):
    logger.info(f"Verifying 2FA setup for user ID: {user_id}")
    try:
        logger.debug(f"Fetching user 2FA settings for user: {user_id}")
        settings = await auth_repository.get_user_settings(user_id)
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        
        if not secret:
            logger.debug("No active 2FA settings found. Querying legacy user table...")
            legacy_user = await auth_repository.get_user_by_id(user_id)
            if not legacy_user or not legacy_user['totp_secret']:
                logger.warning(f"2FA verification rejected: 2FA setup not initiated for user {user_id}")
                raise HTTPException(status_code=400, detail="2FA setup not initiated")
            secret = legacy_user['totp_secret']
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            logger.warning(f"2FA verification failed: Invalid authenticator code supplied by user {user_id}")
            raise HTTPException(status_code=400, detail="Invalid OTP code")
            
        settings_exist = bool(settings)
        logger.debug(f"Enabling 2FA for user {user_id}. settings_exist: {settings_exist}")
        await auth_repository.enable_2fa(user_id, secret, settings_exist)
        
        logger.info(f"2FA verified and enabled successfully for user {user_id}")
        return {"message": "2FA successfully enabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA setup verification failed for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_login_2fa(user_id: str, totp_code: str):
    logger.info(f"Attempting 2FA login verification for user ID: {user_id}")
    try:
        logger.debug(f"Fetching 2FA secret credentials for user ID: {user_id}")
        settings = await auth_repository.get_user_settings(user_id)
        legacy_user = await auth_repository.get_user_by_id(user_id)
        
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        if not secret and legacy_user:
            secret = legacy_user['totp_secret']
            
        if not secret:
            logger.warning(f"2FA login failed: No 2FA secret found for user ID: {user_id}")
            raise HTTPException(status_code=400, detail="Invalid request or 2FA not setup")
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            logger.warning(f"2FA login verification failed: Invalid Authenticator code for user {user_id}")
            raise HTTPException(status_code=401, detail="Invalid Authenticator code")
            
        logger.debug(f"Retrieving user email for generating JWT token: {user_id}")
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            logger.warning(f"2FA login failed: User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        logger.info(f"2FA login successful. Generating access token for user ID: {user_id}")
        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA login verification failed for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def handle_disable_2fa(user_id: str):
    logger.info(f"Disabling 2FA for user ID: {user_id}")
    if not user_id:
        logger.error("Failed to disable 2FA: user_id is missing")
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        await auth_repository.disable_2fa(user_id)
        logger.info(f"2FA disabled successfully for user ID: {user_id}")
        return {"message": "2FA successfully disabled"}
    except Exception as e:
        logger.error(f"Failed to disable 2FA for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
