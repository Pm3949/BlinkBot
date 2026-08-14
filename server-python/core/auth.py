"""
================================================================================
AUTHENTICATION AND SECURITY CORE LAYER (auth.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module forms the security and authentication core of the RAGMate backend. It handles:
1. Cryptographic Password Security: Safe password hashing via `bcrypt` using random salt salts
   to guard database records against rainbow table database breaches.
2. Token Lifecycle Management: Crafting cryptographically signed JSON Web Tokens (JWT) using PyJWT.
   The tokens are structured with specific metadata properties (like claims `sub`, `email`, `role`, and `aud`)
   designed to comply with Supabase's Row Level Security (RLS) policies.
3. User Verification & Delivery (SMTP): Sending automated verification alerts, One-Time Passwords (OTPs)
   for login registration, and password reset codes over SMTP connections using Python's `smtplib`.
4. Endpoint Authorization: Middleware checks implementing FastAPI dependency injection (`get_current_user`).
   It extracts incoming HTTP Bearer tokens, validates signatures against the `SUPABASE_JWT_SECRET`,
   and sets a contextual thread logger variable for tracing user actions.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `os`: Fetching credentials from environment variables.
   - `jwt`: Generating and decoding JSON Web Tokens.
   - `smtplib`: Standard SMTP email sender client.
   - `datetime`/`timedelta`: Managing expiration timestamps.
   - `email.mime`: Reconstructing MIME headers and HTML emails.
   - `bcrypt`: Cryptographic password processor.
   - `fastapi`: Routing utilities and security dependency checks.

2. Global Configurations:
   - Sets JWT variables (`JWT_SECRET`, `ALGORITHM`, expiration rules).
   - Configures SMTP host parameters and credentials.

3. Module Functions:
   - `verify_password(...)`: Validates plaintext attempts against database hashes.
   - `get_password_hash(...)`: Hashes passwords.
   - `create_access_token(...)`: Generates JWT tokens.
   - `send_otp_email(...)`: Dispatches registration verification codes via SMTP with TLS encryption.
   - `send_password_reset_email(...)`: Dispatches password reset codes.
   - `get_current_user(...)`: Middleware that decrypts, validates, and extracts user details from JWTs.
"""

import os
import jwt
import smtplib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
from utils.logger import get_department_logger

# Module-level logger for authentication events
logger = get_department_logger("auth")

# ==========================================
# JWT CONFIGURATION
# ==========================================
# JWT (JSON Web Tokens) are used to verify who the user is on every API request.
# The secret MUST match the Supabase JWT secret so that tokens generated here 
# can be securely verified by Supabase Row Level Security (RLS) policies.
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")
# The hashing algorithm used to sign the tokens cryptographically.
ALGORITHM = "HS256"
# Define default access token expiration period (7 days).
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

# Google OAuth configurations used during client integration processes.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# The client dashboard URL, used to redirect users back after social logins.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ==========================================
# SMTP / EMAIL CONFIGURATION
# ==========================================
# Parameters for setting up mail pipelines.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) # Default SMTP port (using TLS)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@blinkbot.in")


# ==========================================
# PASSWORD SECURITY
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plaintext password attempt with the securely hashed version in the database.

    Purpose:
        Verifies user logins. Securely checks passwords using bcrypt's constant-time comparison
        utility to protect against timing attacks.

    Parameters:
        plain_password (str): Plaintext password submitted by the user.
        hashed_password (str): The corresponding salted bcrypt hash retrieved from the database.

    Returns:
        bool: True if the password matches, False otherwise.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Catches all exceptions and returns False.
    """
    try:
        # Encode inputs as bytes because bcrypt requires raw byte arrays for hashing.
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # Return False if any hashing errors occur (e.g. malformed hash formats).
        return False


def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a random salt.

    Purpose:
        Saves passwords securely. Generates a random cryptographic salt, applies it to the password,
        and hashes it. This ensures that identical passwords yield different database hashes,
        preventing rainbow table lookup attacks.

    Parameters:
        password (str): The user's plaintext password.

    Returns:
        str: The generated salted bcrypt hash string.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - May raise encoding exceptions if input characters are not UTF-8 compatible.
    """
    # Generate a secure random salt.
    salt = bcrypt.gensalt()
    # Hash the password bytes using the generated salt.
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Decode the hash bytes to UTF-8 to store it as a text string in the database.
    return hashed.decode('utf-8')


# ==========================================
# TOKEN GENERATION
# ==========================================

def create_access_token(user_id: str, email: str, expires_delta: timedelta = None) -> str:
    """
    Generates a secure, signed JSON Web Token (JWT) for user sessions.

    Purpose:
        Constructs a JWT payload containing user ID details and session metadata. The audience and
        role properties are structured to match Supabase's authentication claims, enabling
        the token to pass Supabase's Row Level Security (RLS) check policies.

    Parameters:
        user_id (str): The database UUID of the user.
        email (str): The email address of the user.
        expires_delta (timedelta, optional): Custom expiration duration. Defaults to None.

    Returns:
        str: The signed and encoded JWT token string.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - May raise PyJWT encoding errors.
    """
    # Create the payload structure.
    # sub: Subject claim (contains the unique user UUID).
    # role/aud: MUST match 'authenticated' to pass Supabase RLS security policies.
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated"
    }
    # Calculate expiration timestamp.
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Update the payload with the expiration claim ("exp").
    to_encode.update({"exp": expire})
    # Cryptographically sign the token using the secret key and HS256 algorithm.
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


# ==========================================
# EMAIL DELIVERY UTILITIES
# ==========================================

def send_otp_email(to_email: str, otp: str):
    """
    Sends a 6-digit verification code email for account registration or 2FA checks.

    Purpose:
        Assembles a multipart email (plain text fallback + modern HTML styling) and dispatches it
        to the user's address.

    Parameters:
        to_email (str): Recipient email address.
        otp (str): The 6-digit verification code string.

    Returns:
        None.

    Side Effects / State Changes:
        - Establishes a socket connection to SMTP hosts and sends an email.

    Errors / Exceptions:
        - Gracefully handles and prints errors if connection, authentication, or dispatch fails.
    """
    # Bypass execution if mail coordinates are unconfigured in environment variables.
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping OTP email dispatch.")
        logger.debug(f"Dev-only OTP for {to_email}: {otp}")
        return
        
    # Configure mail headers.
    msg = MIMEMultipart("alternative")
    msg['From'] = f"BlinkBot <{SENDER_EMAIL}>"
    msg['To'] = to_email
    msg['Subject'] = "Your BlinkBot Verification Code"

    # Plain text body fallback.
    text_body = f"Hello,\n\nYour BlinkBot verification code is: {otp}\n\nIt will expire in 10 minutes.\n\nThanks,\nThe BlinkBot Team"
    
    # Modern HTML body styling with HSL/vibrant elements.
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
    
    # Attach both parts.
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        # Establish connection to the SMTP server.
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        # Upgrade the connection to use secure TLS encryption.
        server.starttls()
        # Log in with SMTP user credentials.
        server.login(SMTP_USER, SMTP_PASSWORD)
        # Send email.
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        # Close connection.
        server.quit()
        logger.info(f"OTP email dispatched successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}", exc_info=True)


def send_password_reset_email(to_email: str, otp: str):
    """
    Sends a 6-digit password reset verification email.

    Purpose:
        Assembles a multipart email and dispatches password recovery codes to users.

    Parameters:
        to_email (str): Recipient email address.
        otp (str): The 6-digit recovery code string.

    Returns:
        None.

    Side Effects / State Changes:
        - Establishes a socket connection to SMTP hosts and sends an email.

    Errors / Exceptions:
        - Gracefully handles and prints errors if connection or dispatch fails.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Skipping password reset email dispatch.")
        logger.debug(f"Dev-only password reset OTP for {to_email}: {otp}")
        return
        
    msg = MIMEMultipart("alternative")
    msg['From'] = f"BlinkBot <{SENDER_EMAIL}>"
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
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info(f"Password reset email dispatched successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}", exc_info=True)


# ==========================================
# AUTHENTICATION DEPENDENCY
# ==========================================
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure the HTTPBearer security handler. Set auto_error=False
# to manually check the token and customize authentication exception payloads.
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency middleware that extracts and validates incoming JWT Bearer tokens.

    Purpose:
        Protects API routes. Inspects authorization headers, validates token signatures against
        the JWT secret, checks expiration timestamps, and configures the thread context
        logger variable for tracking user actions.

    Parameters:
        credentials (HTTPAuthorizationCredentials): Automatically parsed Authorization header.

    Returns:
        dict: The decoded JWT claim payload containing `sub`, `email`, and `role`.

    Side Effects / State Changes:
        - Sets the context-local `user_id_var` to trace actions of the authenticated user in log outputs.

    Errors / Exceptions:
        - Raises `HTTPException` with status code 401 if credentials are missing, expired, or invalid.
    """
    # If no token is provided in the headers, raise a 401 error.
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization credentials")
    
    token = credentials.credentials
    try:
        # Decode the token, verifying the signature and checking the audience claim.
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], audience="authenticated")
        
        # Set user tracking variable in the thread context log context.
        from utils.logger import user_id_var
        # Safely extract the subject claim ("sub") containing the user UUID, defaulting to a dash.
        user_id_var.set(payload.get("sub", "-"))
        
        return payload
    except jwt.ExpiredSignatureError:
        # Catch signature expiration errors (token has expired).
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        # Catch other decoding issues (tampered tokens or incorrect formats).
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


