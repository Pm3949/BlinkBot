import os
import zlib
import base64
from cryptography.fernet import Fernet
from utils.logger import get_department_logger

logger = get_department_logger("agent")

# Initialize Fernet cipher. Fall back to generating a key if ENCRYPTION_KEY is missing or invalid.
encryption_key = os.getenv("ENCRYPTION_KEY")
if not encryption_key:
    logger.warning("ENCRYPTION_KEY environment variable is missing. Generating temporary key.")
    encryption_key = Fernet.generate_key().decode()

try:
    # Handle single or double quotes wrapped in the env variable
    clean_key = encryption_key.strip("'\"").encode()
    cipher = Fernet(clean_key)
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher with provided ENCRYPTION_KEY: {str(e)}. Generating temporary key.")
    cipher = Fernet(Fernet.generate_key())

def secure_pack(text: str) -> str:
    """
    Compresses and encrypts the input string, returning a URL-safe base64 string.
    """
    if not text:
        return text
    try:
        data_bytes = text.encode("utf-8")
        compressed_bytes = zlib.compress(data_bytes)
        encrypted_bytes = cipher.encrypt(compressed_bytes)
        return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Error packing data: {str(e)}")
        return text

def secure_unpack(b64_string: str) -> str:
    """
    Decrypts and decompresses the input base64 string.
    Falls back to returning the original string if decryption/decompression fails (for legacy unencrypted data).
    """
    if not b64_string:
        return b64_string
    try:
        # Decode and decrypt the string
        encrypted_bytes = base64.urlsafe_b64decode(b64_string.encode("utf-8"))
        compressed_bytes = cipher.decrypt(encrypted_bytes)
        data_bytes = zlib.decompress(compressed_bytes)
        return data_bytes.decode("utf-8")
    except Exception as e:
        # Log failure at debug level as this is expected for legacy unencrypted text rows
        logger.debug(f"Parsing/unpacking failed (likely legacy unencrypted record): {str(e)}")
        return b64_string
