"""
================================================================================
FILE UPLOAD SECURITY SCANNING ENGINE (security_scan.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module implements file upload validation and security scanning. Before any uploaded file is
stored, processed, or indexed in the RAG vector store, it is scanned to block malicious content.
It handles:
1. File Magic Bytes Verification: Inspects the first few bytes (magic bytes) of a file to check if they
   match the declared extension. This blocks extension spoofing attacks (e.g. uploading an executable renamed as a PDF).
2. Plain Text Verification: Confirms plain text extensions (.txt, .csv) do not contain binary content.
3. Script and Injection Scanning (XSS/Formula Injection): Scans plain text for script tags and CSV formulas
   that execute code (formula injection).
4. Macro Detection (DOCX): Scans Office files for VBA macros (`vbaProject.bin`) to block malicious macros.
5. PDF Executable Content Scanning: Strips binary content streams from PDF structures and inspects object
   dictionaries for JavaScript (/JavaScript, /JS) or shell execution (/Launch) actions.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `re`: Regular expressions module.
   - `logging`: Diagnostic logging.
   - `Tuple`: Type hints.

2. Static Signatures Dictionary:
   - Maps extension labels to expected binary headers (magic numbers, e.g. `%PDF` for PDF).

3. Validation Functions:
   - `validate_magic_bytes(file_bytes, filename)`: Resolves the extension and validates headers or decodes text.
   - `scan_malicious_content(file_bytes, filename)`: Performs type-specific script, macro, and macro-free checks.
"""

import re
import logging
from typing import Tuple

from utils.logger import get_department_logger

# Initialize module-level logger using the centralized departmental system.
logger = get_department_logger("system")

# File signatures (magic bytes) dictionary.
# Key: extension string. Value: list of expected byte headers.
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF"], # PDFs start with ASCII %PDF
    "png": [b"\x89PNG\r\n\x1a\n"], # PNG standard file header
    "jpg": [b"\xff\xd8\xff"], # JPEG image SOI marker
    "jpeg": [b"\xff\xd8\xff"], # Same SOI marker for JPEG
    "docx": [b"PK\x03\x04"],  # Standard ZIP signature used by DOCX (OpenXML formats are packaged ZIPs)
    "csv": [],  # Validated by trying to decode content as plain text
    "txt": [],  # Validated as plain text
}

def validate_magic_bytes(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validates file content based on magic bytes (first few bytes) to prevent extension spoofing.

    Purpose:
        Inspects the file's binary header to verify it matches the filename extension,
        blocking executables renamed with benign extensions.

    Parameters:
        file_bytes (bytes): The raw binary content of the file.
        filename (str): The name of the file (e.g. "document.pdf").

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
                          - is_valid: True if header matches extension, False otherwise.
                          - error_message: Reason for validation failure, empty string if valid.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - None. Handles invalid decoding errors gracefully.
    """
    # Guard check: filename is required.
    if not filename:
        return False, "Filename is required"

    # Extract lowercase extension from filename.
    # rsplit(".", 1) splits once from the right. [-1] gets the suffix.
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    # Block unsupported extensions.
    if ext not in MAGIC_SIGNATURES:
        return False, f"Unsupported file extension: .{ext}"

    # Get expected binary headers.
    expected_prefixes = MAGIC_SIGNATURES[ext]
    # If the list is empty (e.g. txt, csv), verify it is plain text.
    if not expected_prefixes:
        try:
            # Attempt to decode the first 8KB of data as UTF-8.
            # If it contains binary executables, this decode step will throw a UnicodeDecodeError.
            file_bytes[:8192].decode("utf-8")
            return True, ""
        except UnicodeDecodeError:
            return False, "File content is invalid: expected plain text but contains binary data."

    # Loop through expected binary headers to check if the file starts with any of them.
    for prefix in expected_prefixes:
        if file_bytes.startswith(prefix):
            return True, ""

    # Return error if the binary header does not match expected prefixes.
    return False, f"File content does not match the expected magic bytes for a .{ext} file."


def scan_malicious_content(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Scans file bytes for script injections, malicious macros, and embedded executions.

    Purpose:
        Detects malicious payloads.
        - Text/CSV: Blocks XSS script tags and CSV formula execution injections.
        - DOCX: Blocks embedded VBA macros.
        - PDF: Blocks automatic actions and executable JavaScript.

    Parameters:
        file_bytes (bytes): The raw binary content of the file.
        filename (str): The name of the file.

    Returns:
        Tuple[bool, str]: (is_secure, error_message)
                          - is_secure: True if no malicious content is found, False otherwise.
                          - error_message: Description of the security issue.

    Side Effects / State Changes:
        - Logs warnings if text parsing fails.

    Errors / Exceptions:
        - Gracefully handles and logs exceptions during file parsing.
    """
    # Resolve suffix extension.
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # 1. Text and CSV security checks.
    if ext in ["txt", "csv"]:
        try:
            # Decode content, ignoring decode errors to scan as much text as possible.
            content = file_bytes.decode("utf-8", errors="ignore")
            # Check for HTML script tags to prevent XSS.
            if re.search(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", content, re.IGNORECASE):
                return False, "File contains potential script tags or XSS code."
            
            # CSV Formula Injection check.
            # Formulas starting with '=', '+', '-', or '@' can execute code in Excel/Sheets.
            if ext == "csv":
                lines = content.splitlines()
                # Scan the first 100 lines for formula injections to limit resource usage.
                for line in lines[:100]:
                    cells = line.split(",")
                    for cell in cells:
                        # Strip quotes and whitespace.
                        cell_strip = cell.strip().strip('"').strip("'")
                        # Check if cell content starts with a formula trigger.
                        if cell_strip.startswith(("=", "+", "-", "@")):
                            # Block cells that call system commands (e.g. system, cmd, powershell).
                            if re.search(r"=\s*(cmd|system|exec|shell|powershell)\b", cell_strip, re.IGNORECASE):
                                return False, "File rejected: Potential CSV Formula execution injection detected."
        except Exception as e:
            logger.warning(f"Error scanning text file content: {e}")

    # 2. Office Document checks (DOCX).
    elif ext == "docx":
        # DOCX is a zipped XML format. Embedded macros are stored in a file named 'vbaProject.bin'.
        # Scanning the zip archive bytes for the string 'vbaProject.bin' blocks macros.
        if b"vbaProject.bin" in file_bytes:
            return False, "File rejected: DOCX contains macro/active content (vbaProject.bin)."

    # 3. PDF checks.
    elif ext == "pdf":
        # PDFs store content streams inside 'stream' and 'endstream' markers.
        # These streams can contain compressed data, triggering false positives.
        # We strip stream blocks to scan only the metadata structure.
        uncompressed_parts = []
        idx = 0
        while True:
            # Find the start of the next stream.
            start_stream = file_bytes.find(b"stream", idx)
            if start_stream == -1:
                # No more streams, append the remaining bytes and exit the loop.
                uncompressed_parts.append(file_bytes[idx:])
                break
            # Append content preceding the stream.
            uncompressed_parts.append(file_bytes[idx:start_stream])
            # Locate the end of the stream.
            end_stream = file_bytes.find(b"endstream", start_stream)
            if end_stream == -1:
                # If stream is malformed or truncated, stop parsing.
                break
            # Skip the 'endstream' marker (9 bytes) and resume scanning.
            idx = end_stream + 9

        # Reconstruct the PDF metadata bytes.
        clean_bytes = b"".join(uncompressed_parts)

        # Scan metadata bytes for executable scripts or auto-run launch actions:
        # - /S /JavaScript: JavaScript action.
        # - /JS: Inline JavaScript payload.
        # - /S /Launch: Auto-run shell execution.
        has_js = (
            re.search(rb"/S\s*/JavaScript\b", clean_bytes, re.IGNORECASE) or
            re.search(rb"/JS\s*[\(<]", clean_bytes, re.IGNORECASE) or
            re.search(rb"/S\s*/Launch\b", clean_bytes, re.IGNORECASE) or
            re.search(rb"/Action\s*/S\s*/JavaScript\b", clean_bytes, re.IGNORECASE)
        )
        if has_js:
            return False, "File rejected: PDF contains embedded executable JavaScript or automatic actions."

    # Return True if the file passes all security checks.
    return True, ""

