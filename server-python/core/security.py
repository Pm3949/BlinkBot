import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Fetch ENCRYPTION_KEY from environment or generate a stable fallback for development
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # A standard development fallback key (32 bytes url-safe base64)
    ENCRYPTION_KEY = base64.urlsafe_b64encode(b"ragmate_dev_encryption_secret_32b").decode("utf-8")
    logger.warning("⚠️ ENCRYPTION_KEY not set in environment. Using a default development key.")

try:
    fernet = Fernet(ENCRYPTION_KEY.encode("utf-8"))
except Exception as e:
    logger.error(f"Failed to initialize Fernet with ENCRYPTION_KEY: {e}")
    # Fallback to dev key if provided key is invalid
    dev_key = base64.urlsafe_b64encode(b"ragmate_dev_encryption_secret_32b").decode("utf-8")
    fernet = Fernet(dev_key.encode("utf-8"))

def encrypt_key(plain_text: Optional[str]) -> Optional[str]:
    if not plain_text:
        return plain_text
    try:
        return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plain_text

def decrypt_key(cipher_text: Optional[str]) -> Optional[str]:
    if not cipher_text:
        return cipher_text
    try:
        # Fernet tokens always start with 'gAAAA' due to the version byte 0x80
        if cipher_text.startswith("gAAAA"):
            return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed, assuming plain text or key mismatch: {e}")
    return cipher_text
