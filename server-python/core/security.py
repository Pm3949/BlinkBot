"""
Encryption & Decryption Utilities.
Responsibility: Secures highly sensitive data (like user's OpenAI API keys or raw document chunks) 
at rest in the PostgreSQL database using AES symmetric encryption (Fernet).
"""
import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# ==========================================
# KEY MANAGEMENT
# ==========================================
# Fetch the master encryption key from the environment.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Edge Case Handled: Missing Configuration.
    # If a developer forgets to set the ENCRYPTION_KEY in their .env, we generate a 
    # stable fallback key so the app doesn't immediately crash. 
    # WARNING: This is only safe for local development, never production.
    ENCRYPTION_KEY = base64.urlsafe_b64encode(b"blinkbot_dev_encryption_secret_32b").decode("utf-8")
    logger.warning("⚠️ ENCRYPTION_KEY not set in environment. Using a default development key.")

try:
    # Initialize the Fernet symmetric encryption suite with our master key
    fernet = Fernet(ENCRYPTION_KEY.encode("utf-8"))
except Exception as e:
    logger.error(f"Failed to initialize Fernet with ENCRYPTION_KEY: {e}")
    # Fallback to dev key if the provided key is completely invalid (e.g., wrong length)
    dev_key = base64.urlsafe_b64encode(b"blinkbot_dev_encryption_secret_32b").decode("utf-8")
    fernet = Fernet(dev_key.encode("utf-8"))

# ==========================================
# ENCRYPTION FUNCTIONS (Strings)
# ==========================================

def encrypt_key(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypts a plain text string. Used primarily for User API keys before saving to the DB.
    """
    if not plain_text:
        return plain_text
    try:
        return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        # Fail-safe: Return the original text if encryption crashes so we don't lose the data entirely.
        return plain_text

def decrypt_key(cipher_text: Optional[str]) -> Optional[str]:
    """
    Decrypts a previously encrypted string. Used when fetching User API keys from the DB.
    """
    if not cipher_text:
        return cipher_text
    try:
        # Fernet tokens always start with 'gAAAA'. We check this to prevent 
        # crashing if we accidentally try to decrypt an unencrypted string.
        if cipher_text.startswith("gAAAA"):
            return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed, assuming plain text or key mismatch: {e}")
    # Return the original text if it wasn't encrypted or if decryption failed
    return cipher_text

# ==========================================
# ENCRYPTION FUNCTIONS (Bytes/Files)
# ==========================================

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypts raw byte data. Useful for encrypting actual file uploads (like PDFs) 
    before writing them to disk.
    """
    if not data:
        return data
    try:
        return fernet.encrypt(data)
    except Exception as e:
        logger.error(f"Data encryption failed: {e}")
        return data

def decrypt_data(cipher_data: bytes) -> bytes:
    """
    Decrypts raw byte data back to its original format.
    """
    if not cipher_data:
        return cipher_data
    try:
        # Check for the Fernet signature 'gAAAA' encoded in ascii bytes
        if cipher_data.startswith(b"gAAAA"):
            return fernet.decrypt(cipher_data)
    except Exception as e:
        logger.warning(f"Data decryption failed, assuming unencrypted data: {e}")
    return cipher_data
