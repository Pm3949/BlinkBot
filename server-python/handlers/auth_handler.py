"""
================================================================================
ARCHITECTURAL CONTEXT & FILE OVERVIEW
================================================================================
This script handles the authentication and registration lifecycle for RAGMate users.
It orchestrates login validations, secure registration with OTP (One-Time Password) verification,
password resetting, multi-factor authentication (2FA), and Google OAuth integration.

From top to bottom, the file executes as follows:
1. Imports: Loads cryptographic randomizers (secrets), multi-factor token generators (pyotp),
   async HTTP requests wrappers (httpx), time helpers (datetime, timedelta), FastAPI exceptions,
   and URL encoders.
2. Local Dependencies: imports password hashing and token generation helpers,
   database repositories for user data, and a department-scoped logger.
3. OTP Generation helper: Randomly creates a secure 6-digit numeric OTP code.
4. Google OAuth routines:
   - `handle_google_login`: Prepares the URL to redirect users to Google's sign-in consent screen.
   - `handle_google_callback`: Exchanges callback parameters for tokens, pulls profile emails,
     verifies/registers the user, and signs a JWT authorization token.
5. Email/Password flow:
   - `handle_register`: Registers new users, generates OTPs, and triggers verification emails.
   - `handle_verify_otp`: Checks user-submitted OTP codes and activates verified statuses.
   - `handle_login`: Validates user passwords, checks 2FA requirements, and returns JWT tokens.
6. Reset Password routines:
   - `handle_forgot_password`: Emails a recovery OTP token to the user.
   - `handle_reset_password`: Validates the recovery OTP and updates the user's password.
7. Two-Factor Authentication (2FA) routines:
   - `handle_setup_2fa`: Initiates TOTP base32 key configurations and outputs QR-code URIs.
   - `handle_verify_2fa_setup`: Validates setup tokens and permanently locks accounts behind 2FA.
   - `handle_login_2fa`: Performs second-factor checks on login and returns JWT keys.
   - `handle_disable_2fa`: Turns off TOTP multi-factor verification on request.
"""

import secrets  # Cryptographically secure random generators (safer than python's standard 'random' module)
import pyotp  # Library for generating and verifying One-Time Passwords (for Google Authenticator 2FA)
import httpx  # Async HTTP client to make API calls to external services (like Google's OAuth endpoints)
from datetime import datetime, timedelta  # Time parameters to measure session timeouts and OTP expiries
from fastapi import HTTPException  # Web exception class to raise clean client-side HTTP errors
from urllib.parse import urlencode  # URL utility to format dictionary parameters into query strings

# Import core authentication and hashing parameters
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
from db import auth_repository, workspace_repository  # Database query methods for users and workspaces
from utils.logger import get_department_logger  # Scope loggers to specific app modules

# Instantiate a logging object specifically under the "auth" category
logger = get_department_logger("auth")

def generate_otp():
    """
    Generates a secure, cryptographically random 6-digit One-Time Password (OTP).

    Returns:
        str: A 6-digit numeric string (e.g. '352981').
    """
    logger.debug("Generating secure 6-digit OTP...")
    # secrets.randbelow(900000) generates an integer from 0 to 899,999.
    # Adding 100,000 ensures it is always a 6-digit number between 100,000 and 999,999.
    otp = str(secrets.randbelow(900000) + 100000)
    logger.debug("Successfully generated a new OTP.")
    return otp

async def handle_google_login(base_url: str):
    """
    Constructs the redirect URL pointing to Google's OAuth 2.0 login screen.

    Parameters:
        base_url (str): The server backend host URL (used to configure callback paths).

    Returns:
        str: The full Google OAuth consent redirection URL.

    Exceptions Raised:
        HTTPException(500): Raised if Google client ID configuration is missing.
    """
    logger.info(f"Initiating Google login process with base_url: {base_url}")
    # Verify that the environment variable for Google OAuth Client ID exists
    if not GOOGLE_CLIENT_ID:
        logger.error("Google Auth configuration failure: GOOGLE_CLIENT_ID is not configured")
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    # The URL where Google will send the user back after they authenticate
    redirect_uri = f"{base_url}/auth/google/callback"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    
    # Configure parameters required by Google's OAuth API
    params = {
        "client_id": GOOGLE_CLIENT_ID,                 # Google API Console Project ID
        "redirect_uri": redirect_uri,                 # Callback endpoint link
        "response_type": "code",                       # Tells Google we expect an authorization code back
        "scope": "openid email profile",               # Extent of access requested (profile info and email)
        "access_type": "offline",                     # Requests refresh token to keep user logged in
        "prompt": "consent"                            # Forces consent screen layout to show every time
    }
    # Encode parameters into query format (e.g. 'client_id=123&scope=openid')
    target_url = f"{auth_url}?{urlencode(params)}"
    logger.debug(f"Generated Google OAuth authorization URL: {target_url}")
    return target_url


async def handle_google_callback(base_url: str, request_url: str, code: str):
    """
    Processes the OAuth callback request from Google.
    Exchanges the authorization code for an access token, pulls email profile info,
    registers or signs in the user, and redirects them to the frontend with a signed JWT key.

    Parameters:
        base_url (str): Backend API base URL.
        request_url (str): The actual request callback URL triggered by the client.
        code (str): The authorization code returned by Google.

    Returns:
        str: The frontend redirect target URL containing the user's signed JWT token.

    Exceptions Raised:
        HTTPException(400): Raised if token exchange with Google fails.
        HTTPException(500): Raised if server errors occur.
    """
    logger.info(f"Handling Google OAuth callback. Request URL: {request_url}")
    # Verify that Google client secret configuration is present
    if not GOOGLE_CLIENT_SECRET:
        logger.error("Google Auth configuration failure: GOOGLE_CLIENT_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Google Auth is not configured")
        
    redirect_uri = f"{base_url}/auth/google/callback"
    token_url = "https://oauth2.googleapis.com/token"
    
    # Prepare form post fields to exchange authorization code for an OAuth Access Token
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    logger.debug(f"Requesting Google OAuth token from: {token_url}")
    async with httpx.AsyncClient() as client:
        # POST form data to Google's token endpoint
        response = await client.post(token_url, data=data)
        token_data = response.json()
        
        # If Google reports an error in the token exchange
        if "error" in token_data:
            logger.error(f"Google token request failed: {token_data.get('error_description')}")
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "Failed to fetch token"))
            
        logger.debug("Successfully retrieved access token from Google.")
        access_token = token_data["access_token"]
        
        # Call Google userinfo endpoint to retrieve profile info
        logger.debug("Fetching user profile information from Google userinfo endpoint...")
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()
        
    # Extract email from Google's profile payload
    email = user_info.get("email")
    if not email:
        logger.error("Google login failed: Failed to fetch email from user info endpoint.")
        raise HTTPException(status_code=400, detail="Failed to fetch email from Google")
        
    logger.info(f"Google login verified for user email: {email}")
    try:
        logger.debug(f"Querying database for existing user with email: {email}")
        user = await auth_repository.get_user_by_email(email)
        
        # If the user is logging in with Google for the first time, register them automatically
        if not user:
            logger.info(f"No existing user found for email {email}. Creating a new unverified user...")
            # Create a random, secure long dummy password since they authenticate via Google OAuth
            dummy_password_hash = get_password_hash(secrets.token_urlsafe(32))
            user_id = await auth_repository.create_unverified_user(email, dummy_password_hash)
            logger.debug(f"Created unverified user entry with ID: {user_id}")
        else:
            user_id = str(user['id'])
            logger.debug(f"Found existing user with ID: {user_id}. Verifying user status...")
            # Mark the user account as verified in the DB
            await auth_repository.verify_user(user_id)
            logger.debug(f"User {user_id} verified successfully.")
            
        # Ensure user has a default workspace and claim any pending team invitations
        logger.debug(f"Ensuring default workspace exists for user ID: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)
        
        # Issue a signed JWT Access Token for RAGMate authentication
        logger.debug(f"Generating access token for user ID: {user_id}")
        jwt_token = create_access_token(user_id=user_id, email=email)
        
        # Configure frontend redirect targets
        frontend_redirect = FRONTEND_URL
        if frontend_redirect == "*":
            frontend_redirect = "http://localhost:5173"
        elif "," in frontend_redirect:
            # If multiple origins exist, route local dev clients to localhost
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
    """
    Registers a new user account with email/password.
    Generates a secure OTP code and sends it via verification email.

    Parameters:
        email (str): The email address input.
        password (str): The plain-text password input.

    Returns:
        dict: A status dictionary containing confirmation message.

    Exceptions Raised:
        HTTPException(400): Raised if the email is already registered.
        HTTPException(500): Raised if SQL database writes or email service fails.
    """
    logger.info(f"Registering new user with email: {email}")
    try:
        logger.debug(f"Checking if email {email} is already registered...")
        user = await auth_repository.get_user_by_email(email)
        if user:
            logger.warning(f"Registration rejected: Email {email} already registered")
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash the password (using bcrypt/argon2) to store it securely at rest
        logger.debug("Hashing password and generating OTP...")
        hashed_password = get_password_hash(password)
        # Create a new registration validation OTP
        otp = generate_otp()
        # Set code validity time to 10 minutes from now
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        # Write user records to database as unverified along with validation OTP
        logger.debug(f"Creating user entry with OTP expiring at: {otp_expiry}")
        user_id = await auth_repository.create_user_with_otp(email, hashed_password, otp, otp_expiry)
        
        # Send confirmation email
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
    """
    Verifies the email verification OTP code supplied during user registration.
    If valid, marks user as verified, creates default workspace, and issues a JWT token.

    Parameters:
        email (str): The email address of the registering user.
        otp (str): The 6-digit verification code.

    Returns:
        dict: A payload dictionary containing access token.

    Exceptions Raised:
        HTTPException(400): Raised if OTP is invalid, expired, or user is already verified.
        HTTPException(404): Raised if the user cannot be found.
        HTTPException(500): Raised for database exceptions.
    """
    logger.info(f"Verifying registration OTP for email: {email}")
    try:
        # Fetch user records
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
        
        # Strip timezone configurations before comparison to prevent offset mismatch errors
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        # Check if the code has expired
        if expiry < datetime.utcnow():
            logger.warning(f"OTP verification rejected: OTP expired for {email} (expiry: {expiry})")
            raise HTTPException(status_code=400, detail="OTP expired")

        user_id = str(user['id'])
        # Update user status to verified and clear the temporary verification secrets
        logger.debug(f"Verification successful. Verifying user {user_id} and clearing registration OTP...")
        await auth_repository.verify_user_and_clear_otp(user_id)
        
        # Allocate default workspaces
        logger.debug(f"Creating default workspace for verified user: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)

        # Issue JWT authentication token
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
    """
    Authenticates a user using email and password.
    Supports accounts requiring OTP activation, accounts protected by 2FA (TOTP),
    and claims workspace team invites on successful login.

    Parameters:
        email (str): The email address input.
        password (str): The plain-text password input.

    Returns:
        dict: A dictionary structure indicating authentication result:
            - JWT Token payload if fully authenticated.
            - "requires_otp": True if registration needs OTP activation.
            - "requires_2fa": True if TOTP code entry is required.

    Exceptions Raised:
        HTTPException(401): Raised for invalid credentials.
        HTTPException(500): Raised if SQL database queries fail.
    """
    logger.info(f"Attempting login for email: {email}")
    try:
        # Load user row matching email
        logger.debug(f"Retrieving user details for login email: {email}")
        user = await auth_repository.get_user_by_email(email)
        
        # Validate hash password matches
        if not user or not verify_password(password, user['password_hash']):
            logger.warning(f"Login failed: Invalid credentials for email: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = str(user['id'])
        logger.debug(f"Credentials valid. Checking verification status for user ID: {user_id}")
        
        # If user registered but never entered verification OTP
        if not user['is_verified']:
            logger.info(f"User {email} is unverified. Triggering a new verification OTP...")
            otp = generate_otp()
            otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            # Update user records with new OTP
            await auth_repository.update_user_otp(user_id, otp, otp_expiry)
            send_otp_email(email, otp)
            logger.info(f"Sent new OTP to unverified login user: {email}")
            return {"message": "Account not verified. A new OTP has been sent to your email.", "requires_otp": True}
            
        # Ensure default workspace claims
        logger.debug(f"Creating or verifying default workspace for user ID: {user_id}")
        await auth_repository.create_default_workspace(user_id, email)
        await workspace_repository.claim_pending_workspace_invites(user_id, email)

        # If user has configured and enabled Two-Factor Authenticator settings
        if user.get('two_factor_enabled'):
            logger.info(f"Two-factor authentication (2FA) is enabled for user ID: {user_id}. Restricting login.")
            return {"requires_2fa": True, "user_id": user_id}

        # Successful authentication: generate standard bearer JWT access token
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
    """
    Initiates password recovery procedures.
    If email matches a user account, generates recovery OTP and sends recovery email.
    Silently returns success even if user doesn't exist (to prevent email enumeration attacks).

    Parameters:
        email (str): The email address input.

    Returns:
        dict: A status confirmation message payload.
    """
    logger.info(f"Requesting password reset link for email: {email}")
    try:
        # Fetch user
        logger.debug(f"Checking if user {email} exists in database...")
        user = await auth_repository.get_user_by_email(email)
        if not user:
            logger.warning(f"Forgot password request: User not found for email: {email}. Silently returning.")
            return {"message": "If that email exists, we've sent a password reset link."}
            
        # Create OTP token
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        # Save password recovery OTP inside user record
        logger.debug(f"Updating OTP credentials for password reset. Expiry: {otp_expiry}")
        await auth_repository.update_user_otp(str(user['id']), otp, otp_expiry)
        
        # Dispatch email
        logger.info(f"Sending password reset instructions to email: {email}")
        send_password_reset_email(email, otp)
        
        return {"message": "If that email exists, we've sent a password reset link."}
    except Exception as e:
        logger.error(f"Forgot password request failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_reset_password(email: str, token: str, new_password: str):
    """
    Resets the password for a user using the recovery OTP token.

    Parameters:
        email (str): The email address of the user.
        token (str): The recovery OTP code received via email.
        new_password (str): The new password to save.

    Returns:
        dict: A success message payload.

    Exceptions Raised:
        HTTPException(400): Raised if token is invalid, expired, or user not found.
        HTTPException(500): Raised if SQL database updates fail.
    """
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
            
        # Strip timezone configurations before comparison
        expiry = user['otp_expires_at']
        if expiry.tzinfo:
            expiry = expiry.replace(tzinfo=None)
            
        if expiry < datetime.utcnow():
            logger.warning(f"Password reset failed: Reset token expired for {email} (expiry: {expiry})")
            raise HTTPException(status_code=400, detail="OTP expired")
            
        # Hash new password
        logger.debug(f"Hashing new password for user ID: {user['id']}")
        hashed_password = get_password_hash(new_password)
        # Update user records in database
        await auth_repository.reset_user_password(str(user['id']), hashed_password)
        
        logger.info(f"Password reset successfully for email: {email}")
        return {"message": "Password reset successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed for {email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def handle_setup_2fa(user_id: str):
    """
    Starts Two-Factor Authentication (2FA) setup for a user.
    Generates a unique TOTP base32 key, saves it in settings,
    and returns a provisioning URI to configure Authenticator apps (e.g. Google Authenticator).

    Parameters:
        user_id (str): The unique database UUID of the user.

    Returns:
        dict: A dictionary containing:
            - "provisioning_uri": Key parameters to compile a QR code.
            - "secret": The plain base32 secret token.

    Exceptions Raised:
        HTTPException(400): Raised if user ID is missing, or 2FA is already active.
        HTTPException(404): Raised if the user cannot be found.
        HTTPException(500): Raised for database operations failures.
    """
    logger.info(f"Setting up 2FA for user ID: {user_id}")
    if not user_id:
        logger.error("Failed to setup 2FA: user_id is missing")
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        # Check if they already have 2FA enabled
        logger.debug(f"Checking current 2FA settings status for user: {user_id}")
        settings = await auth_repository.get_user_settings(user_id)
        if settings and settings['two_factor_enabled']:
            logger.warning(f"2FA Setup aborted: 2FA is already enabled for user {user_id}")
            raise HTTPException(status_code=400, detail="2FA already enabled")
            
        # Get email to label the authenticator key
        logger.debug(f"Retrieving user email for ID: {user_id}")
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            logger.warning(f"2FA Setup failed: User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Generate random base32 key
        logger.debug("Generating random base32 secret for TOTP...")
        secret = pyotp.random_base32()
        settings_exist = bool(settings)
        
        # Save TOTP secret in database user settings table
        logger.debug(f"Saving TOTP secret in settings. Record exists: {settings_exist}")
        await auth_repository.update_user_totp_secret(user_id, secret, settings_exist)
        
        # Generate the standard URI which client can convert to a QR-Code image
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
    """
    Completes 2FA setup by verifying a user-submitted code from their Authenticator app.
    If valid, enables 2FA permanently on the user's account settings.

    Parameters:
        user_id (str): The unique database UUID of the user.
        totp_code (str): The 6-digit verification code from the Authenticator app.

    Returns:
        dict: A success message payload.

    Exceptions Raised:
        HTTPException(400): Raised if code is invalid or setup wasn't initiated.
        HTTPException(500): Raised for database exceptions.
    """
    logger.info(f"Verifying 2FA setup for user ID: {user_id}")
    try:
        # Load the totp secret key saved during handle_setup_2fa
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
            
        # Verify the 6-digit TOTP code against the base32 key
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            logger.warning(f"2FA verification failed: Invalid authenticator code supplied by user {user_id}")
            raise HTTPException(status_code=400, detail="Invalid OTP code")
            
        # Enable 2FA permanently
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
    """
    Verifies the TOTP code submitted during user login (second factor).
    If valid, issues a bearer JWT access token.

    Parameters:
        user_id (str): The unique database UUID of the logging user.
        totp_code (str): The 6-digit authenticator code.

    Returns:
        dict: A dictionary structure containing access token.

    Exceptions Raised:
        HTTPException(400): Raised if 2FA is not set up.
        HTTPException(401): Raised if the code is incorrect.
        HTTPException(404): Raised if the user doesn't exist.
        HTTPException(500): Raised for database exceptions.
    """
    logger.info(f"Attempting 2FA login verification for user ID: {user_id}")
    try:
        # Load the TOTP secret key
        logger.debug(f"Fetching 2FA secret credentials for user ID: {user_id}")
        settings = await auth_repository.get_user_settings(user_id)
        legacy_user = await auth_repository.get_user_by_id(user_id)
        
        secret = settings['totp_secret'] if settings and settings['totp_secret'] else None
        if not secret and legacy_user:
            secret = legacy_user['totp_secret']
            
        if not secret:
            logger.warning(f"2FA login failed: No 2FA secret found for user ID: {user_id}")
            raise HTTPException(status_code=400, detail="Invalid request or 2FA not setup")
            
        # Validate the authenticator code
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code):
            logger.warning(f"2FA login verification failed: Invalid Authenticator code for user {user_id}")
            raise HTTPException(status_code=401, detail="Invalid Authenticator code")
            
        # Fetch email to build JWT credentials
        logger.debug(f"Retrieving user email for generating JWT token: {user_id}")
        email = await auth_repository.get_auth_user_email(user_id)
        if not email:
            logger.warning(f"2FA login failed: User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Login success: issue Access Token
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
    """
    Disables 2FA (Two-Factor Authentication) on a user's account.

    Parameters:
        user_id (str): The unique database UUID of the user.

    Returns:
        dict: A success message payload.

    Exceptions Raised:
        HTTPException(400): Raised if user_id is missing.
        HTTPException(500): Raised if database updates fail.
    """
    logger.info(f"Disabling 2FA for user ID: {user_id}")
    if not user_id:
        logger.error("Failed to disable 2FA: user_id is missing")
        raise HTTPException(status_code=400, detail="User ID required")
    try:
        # Wipe TOTP configurations inside repository settings
        await auth_repository.disable_2fa(user_id)
        logger.info(f"2FA disabled successfully for user ID: {user_id}")
        return {"message": "2FA successfully disabled"}
    except Exception as e:
        logger.error(f"Failed to disable 2FA for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
