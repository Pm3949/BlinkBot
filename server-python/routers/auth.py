from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import psycopg2
import psycopg2.extras
import secrets
from datetime import datetime, timedelta
import httpx
from urllib.parse import urlencode

from core.auth import get_password_hash, verify_password, create_access_token, send_otp_email, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, FRONTEND_URL, send_password_reset_email
from database import get_db_connection
from schemas import UserRegister, VerifyOTP, UserLogin, ForgotPassword, ResetPassword, Verify2FA, Login2FA
import pyotp

from slowapi import Limiter
from slowapi.util import get_remote_address

def create_default_workspace(cur, user_id: str, email: str):
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

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/google/login")
async def google_login(request: Request):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    base_url = str(request.base_url).rstrip("/")
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
    return RedirectResponse(f"{auth_url}?{urlencode(params)}")

@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    if not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    base_url = str(request.base_url).rstrip("/")
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
            if "localhost" in str(request.url) or "127.0.0.1" in str(request.url):
                frontend_redirect = "http://localhost:5173"
            else:
                frontend_redirect = "https://blinkbot.in"
        return RedirectResponse(f"{frontend_redirect}/auth/callback?token={jwt_token}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
def generate_otp():
    return str(secrets.randbelow(900000) + 100000)

@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM public.users WHERE email = %s", (payload.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(payload.password)
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        cur.execute("""
            INSERT INTO public.users (email, password_hash, otp_secret, otp_expires_at, is_verified)
            VALUES (%s, %s, %s, %s, FALSE) RETURNING id
        """, (payload.email, hashed_password, otp, otp_expiry))
        user_id = cur.fetchone()[0]
        conn.commit()

        send_otp_email(payload.email, otp)
        return {"message": "User registered. Please check your email for the OTP.", "user_id": user_id, "requires_otp": True}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, payload: VerifyOTP):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, otp_secret, otp_expires_at, is_verified FROM public.users WHERE email = %s", (payload.email,))
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user['is_verified']:
            raise HTTPException(status_code=400, detail="User already verified")
        if user['otp_secret'] != payload.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Check expiry timezone safely
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP expired")

        # Mark verified
        cur.execute("UPDATE public.users SET is_verified = TRUE, otp_secret = NULL, otp_expires_at = NULL WHERE id = %s", (user['id'],))
        
        create_default_workspace(cur, str(user['id']), payload.email)
        conn.commit()

        access_token = create_access_token(user_id=str(user['id']), email=payload.email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": str(user['id']), "email": payload.email}
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, password_hash, is_verified, two_factor_enabled FROM public.users WHERE email = %s", (payload.email,))
        user = cur.fetchone()
        
        if not user or not verify_password(payload.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user['is_verified']:
            # Resend OTP
            otp = generate_otp()
            otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            cur.execute("UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", (otp, otp_expiry, user['id']))
            conn.commit()
            send_otp_email(payload.email, otp)
            return {"message": "Account not verified. A new OTP has been sent to your email.", "requires_otp": True}
            
        create_default_workspace(cur, str(user['id']), payload.email)
        conn.commit()

        if user.get('two_factor_enabled'):
            return {"requires_2fa": True, "user_id": str(user['id'])}

        access_token = create_access_token(user_id=str(user['id']), email=payload.email)
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": str(user['id']), "email": payload.email}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, payload: ForgotPassword):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, is_verified FROM public.users WHERE email = %s", (payload.email,))
        user = cur.fetchone()
        
        if not user:
            return {"message": "If that email exists, we've sent a password reset link."}
            
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        cur.execute("UPDATE public.users SET otp_secret = %s, otp_expires_at = %s WHERE id = %s", (otp, otp_expiry, user['id']))
        conn.commit()
        
        send_password_reset_email(payload.email, otp)
        return {"message": "If that email exists, we've sent a password reset link."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, payload: ResetPassword):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT id, otp_secret, otp_expires_at FROM public.users WHERE email = %s", (payload.email,))
        user = cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")
            
        if user['otp_secret'] != payload.token:
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP expired")
            
        hashed_password = get_password_hash(payload.new_password)
        
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

@router.post("/2fa/setup")
async def setup_2fa(request: Request, payload: dict):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT email, two_factor_enabled FROM public.users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user['two_factor_enabled']:
            raise HTTPException(status_code=400, detail="2FA already enabled")
            
        secret = pyotp.random_base32()
        cur.execute("UPDATE public.users SET totp_secret = %s WHERE id = %s", (secret, user_id))
        conn.commit()
        
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user['email'], issuer_name="RAGMate")
        return {"provisioning_uri": uri, "secret": secret}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: Request, payload: dict):
    user_id = payload.get("user_id")
    totp_code = payload.get("totp_code")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT totp_secret FROM public.users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user or not user['totp_secret']:
            raise HTTPException(status_code=400, detail="2FA setup not initiated")
            
        totp = pyotp.TOTP(user['totp_secret'])
        if not totp.verify(totp_code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")
            
        cur.execute("UPDATE public.users SET two_factor_enabled = TRUE WHERE id = %s", (user_id,))
        # The user_settings table has its own boolean
        cur.execute("UPDATE user_settings SET two_factor_enabled = TRUE WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"message": "2FA successfully enabled"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.post("/login/2fa")
@limiter.limit("5/minute")
async def login_2fa(request: Request, payload: Login2FA):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT email, totp_secret, is_verified FROM public.users WHERE id = %s", (payload.user_id,))
        user = cur.fetchone()
        
        if not user or not user['totp_secret']:
            raise HTTPException(status_code=400, detail="Invalid request")
            
        totp = pyotp.TOTP(user['totp_secret'])
        if not totp.verify(payload.totp_code):
            raise HTTPException(status_code=401, detail="Invalid Authenticator code")
            
        access_token = create_access_token(user_id=payload.user_id, email=user['email'])
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "user": {"id": payload.user_id, "email": user['email']}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
