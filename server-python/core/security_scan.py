import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# File signatures (magic bytes)
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "docx": [b"PK\x03\x04"],  # Standard ZIP signature used by DOCX
    "csv": [],  # Validated as plain text
    "txt": [],  # Validated as plain text
}

def validate_magic_bytes(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validates file content based on magic bytes (first few bytes) to prevent extension spoofing.
    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "Filename is required"

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in MAGIC_SIGNATURES:
        return False, f"Unsupported file extension: .{ext}"

    expected_prefixes = MAGIC_SIGNATURES[ext]
    if not expected_prefixes:
        # If there are no binary signatures (like txt, csv), verify it's valid text
        try:
            # Check if it can be decoded as UTF-8 or ASCII (read first 8KB)
            file_bytes[:8192].decode("utf-8")
            return True, ""
        except UnicodeDecodeError:
            return False, "File content is invalid: expected plain text but contains binary data."

    # Check matching binary signatures
    for prefix in expected_prefixes:
        if file_bytes.startswith(prefix):
            return True, ""

    return False, f"File content does not match the expected magic bytes for a .{ext} file."

def scan_malicious_content(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Scans the file bytes for obvious injection patterns, scripts, or malicious content.
    Returns (is_secure, error_message).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # 1. Text/CSV script & formula injection checks
    if ext in ["txt", "csv"]:
        try:
            content = file_bytes.decode("utf-8", errors="ignore")
            # Check for HTML script tags to prevent XSS if displayed
            if re.search(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", content, re.IGNORECASE):
                return False, "File contains potential script tags or XSS code."
            
            # CSV Formula Injection check (starts with =, +, -, @)
            if ext == "csv":
                lines = content.splitlines()
                for line in lines[:100]:  # Scan first 100 lines
                    cells = line.split(",")
                    for cell in cells:
                        cell_strip = cell.strip().strip('"').strip("'")
                        if cell_strip.startswith(("=", "+", "-", "@")):
                            # Basic warning, but we can log/block execution cells like =cmd| or =cmd|' / =SYSTEM
                            if re.search(r"=\s*(cmd|system|exec|shell|powershell)\b", cell_strip, re.IGNORECASE):
                                return False, "File rejected: Potential CSV Formula execution injection detected."
        except Exception as e:
            logger.warning(f"Error scanning text file content: {e}")

    # 2. DOCX macro checks
    elif ext == "docx":
        # Look for standard VBA macro folders/signatures inside the ZIP structure (e.g. word/vbaProject.bin)
        if b"vbaProject.bin" in file_bytes:
            return False, "File rejected: DOCX contains macro/active content (vbaProject.bin)."

    # 3. PDF Script checks
    elif ext == "pdf":
        # Strip out stream content to avoid false positives in compressed/binary data streams
        # A stream block starts with 'stream' and ends with 'endstream'
        uncompressed_parts = []
        idx = 0
        while True:
            start_stream = file_bytes.find(b"stream", idx)
            if start_stream == -1:
                uncompressed_parts.append(file_bytes[idx:])
                break
            uncompressed_parts.append(file_bytes[idx:start_stream])
            end_stream = file_bytes.find(b"endstream", start_stream)
            if end_stream == -1:
                # Malformed stream/truncated PDF, stop parsing
                break
            idx = end_stream + 9  # Skip 'endstream' plus newline buffer

        clean_bytes = b"".join(uncompressed_parts)

        # Look for explicit executable JavaScript or Launch actions in object dictionaries
        # Avoid matching font names (e.g. /AARAL) or standard metadata tags
        has_js = (
            re.search(rb"/S\s*/JavaScript\b", clean_bytes, re.IGNORECASE) or
            re.search(rb"/JS\s*[\(<]", clean_bytes, re.IGNORECASE) or
            re.search(rb"/S\s*/Launch\b", clean_bytes, re.IGNORECASE) or
            re.search(rb"/Action\s*/S\s*/JavaScript\b", clean_bytes, re.IGNORECASE)
        )
        if has_js:
            return False, "File rejected: PDF contains embedded executable JavaScript or automatic actions."

    return True, ""
