"""
================================================================================
AES SYMMETRIC DATA ENCRYPTION ENGINE (security.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module provides symmetric encryption and decryption services for RAGMate.
It implements AES-128 in CBC mode using the Cryptography library's `Fernet` specification.
It secures:
1. Credentials-at-rest: Encrypts integration keys (e.g. OpenAI API keys) before storing them.
2. Files-at-rest: Encrypts raw uploaded files (like PDFs) and parsed text chunks.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `os`: Environment variables.
   - `base64`: Key formatting.
   - `logging`: Diagnostic logging.
   - `Fernet`: Symmetric encryption engine.

2. Encryption Key Lifecycle:
   - Resolves the master key (`ENCRYPTION_KEY`). Generates a fallback key in dev environments if missing.
   - Initializes the `Fernet` suite. Handles validation errors by falling back to the dev key.

3. Module Functions:
   - `encrypt_key(plain_text)` / `decrypt_key(cipher_text)`: Encrypts/decrypts string keys.
     Checks for the Fernet header prefix `gAAAA` to prevent decoding raw text.
   - `encrypt_data(data)` / `decrypt_data(cipher_data)`: Encrypts/decrypts binary file streams.
"""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet

from utils.logger import get_department_logger

# Initialize module-level logger using the centralized departmental system.
logger = get_department_logger("system")

# ==========================================
# KEY MANAGEMENT
# ==========================================
# Fetch the master symmetric encryption key from environment configurations.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Check if the encryption key is configured.
if not ENCRYPTION_KEY:
    # If the key is missing (e.g. in dev environments), generate a stable fallback key
    # to prevent startup crashes.
    # urlsafe_b64encode ensures the generated key is base64-encoded and url-safe, as required by Fernet.
    ENCRYPTION_KEY = base64.urlsafe_b64encode(b"blinkbot_dev_encryption_secret_32b").decode("utf-8")
    logger.warning("⚠️ ENCRYPTION_KEY not set in environment. Using a default development key.")

try:
    # Initialize the Fernet suite. The key must be passed as raw UTF-8 bytes.
    fernet = Fernet(ENCRYPTION_KEY.encode("utf-8"))
except Exception as e:
    logger.error(f"Failed to initialize Fernet with ENCRYPTION_KEY: {e}")
    # If initialization fails (e.g. invalid key length), fall back to the dev key.
    dev_key = base64.urlsafe_b64encode(b"blinkbot_dev_encryption_secret_32b").decode("utf-8")
    fernet = Fernet(dev_key.encode("utf-8"))


# ==========================================
# ENCRYPTION FUNCTIONS (Strings)
# ==========================================

def encrypt_key(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypts a plaintext string.

    Purpose:
        Secures sensitive string data (like user API keys) before storing it in the database.

    Parameters:
        plain_text (str | None): The plaintext string to encrypt.

    Returns:
        str | None: The encrypted ciphertext string, or the original input if it is empty.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Catches encryption errors and returns the input text to prevent data loss.
    """
    # Return the input if it is empty or None.
    if not plain_text:
        return plain_text
    try:
        # Encode the string to bytes, encrypt it, and decode the output bytes back to UTF-8.
        return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        # Return the original text if encryption fails to prevent data loss.
        return plain_text


def decrypt_key(cipher_text: Optional[str]) -> Optional[str]:
    """
    Decrypts an encrypted ciphertext string.

    Purpose:
        Decrypts sensitive credentials retrieved from the database.
        Checks for the standard Fernet prefix ('gAAAA') to avoid trying to decrypt
        plaintext keys.

    Parameters:
        cipher_text (str | None): The encrypted ciphertext string.

    Returns:
        str | None: The decrypted plaintext string, or the input if it is empty or unencrypted.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Catches decryption errors and returns the input string.
    """
    # Return the input if it is empty or None.
    if not cipher_text:
        return cipher_text
    try:
        # Check if the string starts with the standard Fernet token prefix ('gAAAA').
        # This prevents errors if we try to decrypt a plaintext string.
        if cipher_text.startswith("gAAAA"):
            # Encode the ciphertext to bytes, decrypt it, and decode the result back to a string.
            return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed, assuming plain text or key mismatch: {e}")
    # Return the original string if decryption fails or the token was not encrypted.
    return cipher_text


# ==========================================
# ENCRYPTION FUNCTIONS (Bytes/Files)
# ==========================================

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypts raw binary data.

    Purpose:
        Encrypts uploaded files (e.g. PDFs) before saving them to disk.

    Parameters:
        data (bytes): The raw binary data to encrypt.

    Returns:
        bytes: The encrypted binary data.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Catches encryption errors and returns the input bytes.
    """
    # Return the input if it is empty.
    if not data:
        return data
    try:
        # Encrypt the raw bytes.
        return fernet.encrypt(data)
    except Exception as e:
        logger.error(f"Data encryption failed: {e}")
        return data


def decrypt_data(cipher_data: bytes) -> bytes:
    """
    Decrypts encrypted binary data.

    Purpose:
        Decrypts binary files before parsing or serving them.
        Checks for the standard Fernet prefix (b'gAAAA') to avoid trying to decrypt
        unencrypted files.

    Parameters:
        cipher_data (bytes): The encrypted binary data.

    Returns:
        bytes: The decrypted binary data.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - Catches decryption errors and returns the input bytes.
    """
    # Return the input if it is empty.
    if not cipher_data:
        return cipher_data
    try:
        # Check if the bytes start with the standard Fernet token prefix (b'gAAAA').
        if cipher_data.startswith(b"gAAAA"):
            # Decrypt the bytes.
            return fernet.decrypt(cipher_data)
    except Exception as e:
        logger.warning(f"Data decryption failed, assuming unencrypted data: {e}")
    # Return the original bytes if decryption fails or the data was not encrypted.
    return cipher_data

