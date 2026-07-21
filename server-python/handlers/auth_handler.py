import logging
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
from db import auth_repository

logger = logging.getLogger(__name__)

def generate_otp():
    """Generates a secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)

async def handle_google_login(base_url: str):
    if not GOOGLE_CLIENT_ID:
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
    return f"{auth_url}?{urlencode(params)}"


async def handle_google_callback(base_url: str, request_url: str, code: str):
    if not GOOGLE_CLIENT_SECRET:
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
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        token_data = response.json()
        
        if "error" in token_data:
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "Failed to fetch token"))
            
        access_token = token_data["access_token"]
        
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()
        
    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Failed to fetch email from Google")
        
    try:
        user = await auth_repository.get_user_by_email(email)
        
        if not user:
            dummy_password_hash = get_password_hash(secrets.token_urlsafe(32))
            user_id = await auth_repository.create_unverified_user(email, dummy_password_hash)
        else:
            user_id = str(user['id'])
            await auth_repository.verify_user(user_id)
            
        await auth_repository.create_default_workspace(user_id, email)
        
        jwt_token = create_access_token(user_id=user_id, email=email)
        
        frontend_redirect = FRONTEND_URL
        if frontend_redirect == "*":
            frontend_redirect = "http://localhost:5173"
        elif "," in frontend_redirect:
            if "localhost" in request_url or "127.0.0.1" in request_url:
                frontend_redirect = "http://localhost:5173"
            else:
                frontend_redirect = "https://blinkbot.in"
        return f"{frontend_redirect}/auth/callback?token={jwt_token}"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_register(email: str, password: str):
    try:
        user = await auth_repository.get_user_by_email(email)
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(password)
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        user_id = await auth_repository.create_user_with_otp(email, hashed_password, otp, otp_expiry)
        send_otp_email(email, otp)
        
        return {"message": "User registered. Please check your email for the OTP.", "user_id": user_id, "requires_otp": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_verify_otp(email: str, otp: str):
    try:
        user = await auth_repository.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user['is_verified']:
            raise HTTPException(status_code=400, detail="User already verified")
        if user['otp_secret'] != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP expired")

        user_id = str(user['id'])
        await auth_repository.verify_user_and_clear_otp(user_id)
        await auth_repository.create_default_workspace(user_id, email)

        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_login(email: str, password: str):
    try:
        user = await auth_repository.get_user_by_email(email)
        if not user or not verify_password(password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = str(user['id'])
        if not user['is_verified']:
            otp = generate_otp()
            otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            await auth_repository.update_user_otp(user_id, otp, otp_expiry)
            send_otp_email(email, otp)
            return {"message": "Account not verified. A new OTP has been sent to your email.", "requires_otp": True}
            
        await auth_repository.create_default_workspace(user_id, email)

        if user.get('two_factor_enabled'):
            return {"requires_2fa": True, "user_id": user_id}

        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed with an unexpected error")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_forgot_password(email: str):
    try:
        user = await auth_repository.get_user_by_email(email)
        if not user:
            return {"message": "If that email exists, we've sent a password reset link."}
            
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        await auth_repository.update_user_otp(str(user['id']), otp, otp_expiry)
        send_password_reset_email(email, otp)
        
        return {"message": "If that email exists, we've sent a password reset link."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_reset_password(email: str, token: str, new_password: str):
    try:
        user = await auth_repository.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")
            
        if user['otp_secret'] != token:
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP expired")
            
        hashed_password = get_password_hash(new_password)
        await auth_repository.reset_user_password(str(user['id']), hashed_password)
        
        return {"message": "Password reset successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_setup_2fa(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        settings = await auth_repository.get_user_settings(user_id)
        if settings and settings['two_factor_enabled']:
            raise HTTPException(status_code=400, detail="2FA already enabled")
            
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            raise HTTPException(status_code=404, detail="User not found")
            
        secret = pyotp.random_base32()
        settings_exist = bool(settings)
        await auth_repository.update_user_totp_secret(user_id, secret, settings_exist)
        
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="BlinkBot")
        return {"provisioning_uri": uri, "secret": secret}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_verify_2fa_setup(user_id: str, totp_code: str):
    try:
        settings = await auth_repository.get_user_settings(user_id)
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        
        if not secret:
            legacy_user = await auth_repository.get_user_by_id(user_id)
            if not legacy_user or not legacy_user['totp_secret']:
                raise HTTPException(status_code=400, detail="2FA setup not initiated")
            secret = legacy_user['totp_secret']
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")
            
        settings_exist = bool(settings)
        await auth_repository.enable_2fa(user_id, secret, settings_exist)
        
        return {"message": "2FA successfully enabled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_login_2fa(user_id: str, totp_code: str):
    try:
        settings = await auth_repository.get_user_settings(user_id)
        legacy_user = await auth_repository.get_user_by_id(user_id)
        
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        if not secret and legacy_user:
            secret = legacy_user['totp_secret']
            
        if not secret:
            raise HTTPException(status_code=400, detail="Invalid request or 2FA not setup")
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=401, detail="Invalid Authenticator code")
            
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            raise HTTPException(status_code=404, detail="User not found")
            
        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def handle_disable_2fa(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        await auth_repository.disable_2fa(user_id)
        return {"message": "2FA successfully disabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
