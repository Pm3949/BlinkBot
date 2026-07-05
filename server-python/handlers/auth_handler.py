import logging
import secrets
import pyotp
import httpx
import psycopg2
import psycopg2.extras
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
from database import get_db_connection

logger = logging.getLogger(__name__)

def generate_otp():
    """Generates a secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def create_default_workspace(cur, user_id: str, email: str):
    """
    What it does: Creates a default workspace for a brand new user upon registration.
    Args:
        cur: The psycopg2 database cursor.
        user_id (str): The ID of the new user.
        email (str): The email of the new user.
    Returns: None
    """
    cur.execute("SELECT id FROM workspaces WHERE owner_id = %s", (user_id,))
    if cur.fetchone():
        return
        
    workspace_name = f"{email.split('@')[0]}'s Workspace"
    cur.execute("INSERT INTO workspaces (name, owner_id) VALUES (%s, %s) RETURNING id", (workspace_name, user_id))
    workspace_id = cur.fetchone()[0]
    
    permissions = '{"agents": true, "database": true, "notes": true}'
    cur.execute("""
        INSERT INTO workspace_members (workspace_id, user_id, email, name, role, permissions)
        VALUES (%s, %s, %s, %s, 'Owner', %s::jsonb)
    """, (workspace_id, user_id, email, email.split('@')[0], permissions))


async def handle_google_login(base_url: str):
    """
    What it does: Generates the Google OAuth2 consent screen URL.
    Args:
        base_url (str): The base URL of the request.
    Returns: The Google OAuth URL to redirect the user to.
    """
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
    """
    What it does: Exchanges the Google Auth code for a JWT access token, creates an account if necessary, and logs the user in.
    Args:
        base_url (str): The base URL of the backend.
        request_url (str): The full URL of the incoming request.
        code (str): The authorization code from Google.
    Returns: The frontend redirect URL with the JWT token attached.
    """
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
        
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id FROM public.users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            dummy_password_hash = get_password_hash(secrets.token_urlsafe(32))
            cur.execute("""
                INSERT INTO public.users (email, password_hash, is_verified)
                VALUES (%s, %s, TRUE) RETURNING id
            """, (email, dummy_password_hash))
            user_id = str(cur.fetchone()[0])
        else:
            user_id = str(user['id'])
            cur.execute("UPDATE public.users SET is_verified = TRUE WHERE id = %s", (user_id,))
            
        create_default_workspace(cur, user_id, email)
        conn.commit()
        
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
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_register(email: str, password: str):
    """
    What it does: Registers a new user, hashes their password, and sends them an email OTP to verify their address.
    Args:
        email (str): The user's email.
        password (str): The raw plaintext password to hash.
    Returns: A success dict with requires_otp flag.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM public.users WHERE email = %s", (email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(password)
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        cur.execute("""
            INSERT INTO public.users (email, password_hash, otp_secret, otp_expires_at, is_verified)
            VALUES (%s, %s, %s, %s, FALSE) RETURNING id
        """, (email, hashed_password, otp, otp_expiry))
        user_id = cur.fetchone()[0]
        conn.commit()

        send_otp_email(email, otp)
        return {"message": "User registered. Please check your email for the OTP.", "user_id": user_id, "requires_otp": True}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_verify_otp(email: str, otp: str):
    """
    What it does: Verifies the email OTP. If valid, marks the user as verified and logs them in.
    Args:
        email (str): The user's email.
        otp (str): The 6-digit code.
    Returns: The JWT access token and user info.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, otp_secret, otp_expires_at, is_verified FROM public.users WHERE email = %s", (email,))
        user = cur.fetchone()
        
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

        cur.execute("UPDATE public.users SET is_verified = TRUE, otp_secret = NULL, otp_expires_at = NULL WHERE id = %s", (user['id'],))
        
        create_default_workspace(cur, str(user['id']), email)
        conn.commit()

        access_token = create_access_token(user_id=str(user['id']), email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": str(user['id']), "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_login(email: str, password: str):
    """
    What it does: Authenticates a user. Enforces 2FA if enabled.
    Args:
        email (str): The user's email.
        password (str): The raw password.
    Returns: The JWT token, or a flag indicating 2FA/OTP is required.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, password_hash, is_verified, two_factor_enabled FROM public.users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user or not verify_password(password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user['is_verified']:
            otp = generate_otp()
            otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            cur.execute("UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", (otp, otp_expiry, user['id']))
            conn.commit()
            send_otp_email(email, otp)
            return {"message": "Account not verified. A new OTP has been sent to your email.", "requires_otp": True}
            
        create_default_workspace(cur, str(user['id']), email)
        conn.commit()

        if user.get('two_factor_enabled'):
            return {"requires_2fa": True, "user_id": str(user['id'])}

        access_token = create_access_token(user_id=str(user['id']), email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": str(user['id']), "email": email}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_forgot_password(email: str):
    """
    What it does: Generates a password reset link/OTP and sends it via email.
    Args:
        email (str): The user's email.
    Returns: A generic success message to prevent email enumeration attacks.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, is_verified FROM public.users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            return {"message": "If that email exists, we've sent a password reset link."}
            
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        cur.execute("UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", (otp, otp_expiry, user['id']))
        conn.commit()
        
        send_password_reset_email(email, otp)
        return {"message": "If that email exists, we've sent a password reset link."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_reset_password(email: str, token: str, new_password: str):
    """
    What it does: Resets a user's password using the OTP token sent to their email.
    Args:
        email (str): The user's email.
        token (str): The reset OTP.
        new_password (str): The new plaintext password.
    Returns: A success message.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, otp_secret, otp_expires_at FROM public.users WHERE email = %s", (email,))
        user = cur.fetchone()
        
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
        
        cur.execute("""
            UPDATE public.users 
            SET password_hash = %s, otp_secret = NULL, otp_expires_at = NULL, is_verified = TRUE 
            WHERE id = %s
        """, (hashed_password, user['id']))
        conn.commit()
        
        return {"message": "Password reset successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_setup_2fa(user_id: str):
    """
    What it does: Generates a secure Base32 TOTP secret and returns the provision URI for Authenticator apps.
    Args:
        user_id (str): The user enabling 2FA.
    Returns: The provisioning URI and secret.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT two_factor_enabled FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cur.fetchone()
        if settings and settings['two_factor_enabled']:
            raise HTTPException(status_code=400, detail="2FA already enabled")
            
        cur.execute("SELECT email FROM auth.users WHERE id = %s", (user_id,))
        auth_user = cur.fetchone()
        email = auth_user['email'] if auth_user else None
        
        if not email:
            cur.execute("SELECT email FROM public.users WHERE id = %s", (user_id,))
            legacy_user = cur.fetchone()
            if not legacy_user:
                raise HTTPException(status_code=404, detail="User not found")
            email = legacy_user['email']
            
        secret = pyotp.random_base32()
        
        if not settings:
            cur.execute("INSERT INTO user_settings (user_id, totp_secret) VALUES (%s, %s)", (user_id, secret))
        else:
            cur.execute("UPDATE user_settings SET totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        cur.execute("UPDATE public.users SET totp_secret = %s WHERE id = %s", (secret, user_id))
        conn.commit()
        
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="BlinkBot")
        return {"provisioning_uri": uri, "secret": secret}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_verify_2fa_setup(user_id: str, totp_code: str):
    """
    What it does: Verifies the user's first TOTP code to finalize 2FA setup.
    Args:
        user_id (str): The user's ID.
        totp_code (str): The 6-digit Authenticator code.
    Returns: A success message.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT totp_secret FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cur.fetchone()
        
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        if not secret:
            cur.execute("SELECT totp_secret FROM public.users WHERE id = %s", (user_id,))
            legacy_user = cur.fetchone()
            if not legacy_user or not legacy_user['totp_secret']:
                raise HTTPException(status_code=400, detail="2FA setup not initiated")
            secret = legacy_user['totp_secret']
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")
            
        if not settings:
            cur.execute("INSERT INTO user_settings (user_id, two_factor_enabled, totp_secret) VALUES (%s, TRUE, %s)", (user_id, secret))
        else:
            cur.execute("UPDATE user_settings SET two_factor_enabled = TRUE, totp_secret = %s WHERE user_id = %s", (secret, user_id))
            
        cur.execute("UPDATE public.users SET two_factor_enabled = TRUE, totp_secret = %s WHERE id = %s", (secret, user_id))
        conn.commit()
        return {"message": "2FA successfully enabled"}
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


async def handle_login_2fa(user_id: str, totp_code: str):
    """
    What it does: Logs in a user who has 2FA enabled.
    Args:
        user_id (str): The user's ID.
        totp_code (str): The 6-digit Authenticator code.
    Returns: The JWT token and user info.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT totp_secret FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cur.fetchone()
        
        cur.execute("SELECT email, totp_secret FROM public.users WHERE id = %s", (user_id,))
        legacy_user = cur.fetchone()
        
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        if not secret and legacy_user:
            secret = legacy_user['totp_secret']
            
        if not secret:
            raise HTTPException(status_code=400, detail="Invalid request or 2FA not setup")
            
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            raise HTTPException(status_code=401, detail="Invalid Authenticator code")
            
        cur.execute("SELECT email FROM auth.users WHERE id = %s", (user_id,))
        auth_user = cur.fetchone()
        email = auth_user['email'] if auth_user else (legacy_user['email'] if legacy_user else None)
        
        if not email:
            raise HTTPException(status_code=404, detail="User not found")
            
        access_token = create_access_token(user_id=user_id, email=email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": user_id, "email": email}
        }
    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
