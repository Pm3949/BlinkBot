"""
Authentication & Authorization Core Utilities.
Responsibility: Handles secure password hashing (bcrypt), JSON Web Token (JWT) 
generation for session management, and sending One-Time Passwords (OTP) via email.
"""
import os
import jwt
import smtplib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# JWT CONFIGURATION
# ==========================================
# JWT (JSON Web Tokens) are used to verify who the user is on every API request.
# The secret MUST match the Supabase JWT secret so that tokens generated here 
# can be securely verified by Supabase Row Level Security (RLS) policies.
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # Tokens expire in 7 days for security

# Google OAuth configurations
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ==========================================
# SMTP / EMAIL CONFIGURATION
# ==========================================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

import bcrypt

# ==========================================
# PASSWORD SECURITY
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plaintext password attempt with the securely hashed version in the database.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a random salt.
    Why Salt? A salt ensures that even if two users have the same password ("password123"),
    their database hashes will look completely different, preventing Rainbow Table attacks.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# ==========================================
# TOKEN GENERATION
# ==========================================

def create_access_token(user_id: str, email: str, expires_delta: timedelta = None) -> str:
    """
    Generates a secure, signed JWT string that the frontend will store in LocalStorage.
    """
    # Important: role MUST be "authenticated" to work with Supabase RLS policies.
    # If this is anything else, Supabase database queries will treat the user as anonymous.
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated"
    }
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration time to payload so the token naturally becomes invalid
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

# ==========================================
# EMAIL DELIVERY UTILITIES
# ==========================================

def send_otp_email(to_email: str, otp: str):
    """
    Sends a 6-digit Verification Code for registration or 2FA.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Skipping email since SMTP_USER or SMTP_PASSWORD is not set. OTP: {otp}")
        return
        
    msg = MIMEMultipart("alternative")
    msg['From'] = f"BlinkBot <{SMTP_USER}>"
    msg['To'] = to_email
    msg['Subject'] = "Your BlinkBot Verification Code"

    # Plain text fallback for old/strict email clients
    text_body = f"Hello,\n\nYour BlinkBot verification code is: {otp}\n\nIt will expire in 10 minutes.\n\nThanks,\nThe BlinkBot Team"
    
    # Premium HTML version for modern email clients
    html_body = f"""
    <html>
      <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f4f4f5; padding: 40px 0; margin: 0;">
        <div style="margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02); text-align: center; max-width: 450px;">
          <h1 style="color: #ff4d00; font-size: 28px; margin-bottom: 5px; font-weight: 800; letter-spacing: -0.5px;">BlinkBot</h1>
          <h2 style="color: #09090b; font-size: 20px; font-weight: 600; margin-bottom: 25px;">Verify your identity</h2>
          <p style="color: #52525b; font-size: 15px; margin-bottom: 35px; line-height: 1.6;">Enter the following one-time password to securely access your BlinkBot workspace. This code expires in 10 minutes.</p>
          
          <div style="background-color: #fafafa; border: 1px solid #e4e4e7; border-radius: 16px; padding: 24px; margin-bottom: 35px;">
            <span style="font-size: 36px; font-weight: 800; letter-spacing: 12px; color: #09090b;">{otp}</span>
          </div>
          
          <p style="color: #a1a1aa; font-size: 13px;">If you didn't request this code, you can safely ignore this email.</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        # Connect to SMTP server and encrypt the connection with TLS
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"OTP Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def send_password_reset_email(to_email: str, otp: str):
    """
    Sends a 6-digit Verification Code for password resets.
    Very similar to send_otp_email, just with different subject/copy logic.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Skipping email since SMTP_USER or SMTP_PASSWORD is not set. OTP: {otp}")
        return
        
    msg = MIMEMultipart("alternative")
    msg['From'] = f"BlinkBot <{SMTP_USER}>"
    msg['To'] = to_email
    msg['Subject'] = "Reset your BlinkBot Password"

    text_body = f"Hello,\n\nYour password reset code is: {otp}\n\nIt will expire in 10 minutes.\n\nThanks,\nThe BlinkBot Team"
    
    html_body = f"""
    <html>
      <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f4f4f5; padding: 40px 0; margin: 0;">
        <div style="margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02); text-align: center; max-width: 450px;">
          <h1 style="color: #ff4d00; font-size: 28px; margin-bottom: 5px; font-weight: 800; letter-spacing: -0.5px;">BlinkBot</h1>
          <h2 style="color: #09090b; font-size: 20px; font-weight: 600; margin-bottom: 25px;">Reset Your Password</h2>
          <p style="color: #52525b; font-size: 15px; margin-bottom: 35px; line-height: 1.6;">You requested a password reset. Use this code to create a new password. This code expires in 10 minutes.</p>
          
          <div style="background-color: #fafafa; border: 1px solid #e4e4e7; border-radius: 16px; padding: 24px; margin-bottom: 35px;">
            <span style="font-size: 36px; font-weight: 800; letter-spacing: 12px; color: #09090b;">{otp}</span>
          </div>
          
          <p style="color: #a1a1aa; font-size: 13px;">If you didn't request a password reset, you can safely ignore this email.</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"Password reset email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

# ==========================================
# AUTHENTICATION DEPENDENCY
# ==========================================
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to verify the incoming JWT bearer token using SUPABASE_JWT_SECRET.
    Returns the decoded payload if valid.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization credentials")
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

