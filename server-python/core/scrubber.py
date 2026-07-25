"""
================================================================================
DATA PRIVACY AND PII REDACTION SCRUBBER LAYER (scrubber.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module provides PII (Personally Identifiable Information) detection and redaction utilities.
It scans prompt inputs or database entries for sensitive parameters—such as Social Security Numbers (SSN),
Credit Card numbers, email addresses, and phone numbers—and replaces them with redaction placeholders.
This ensures GDPR, HIPAA, and custom privacy compliance by sanitizing inputs before sending data to third-party LLMs.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `re`: The Python standard library regular expressions module.

2. Regular Expression Compilations:
   - Pre-compiles regular expressions (`re.compile`) at module load time for performance optimization.
     Recompiling patterns during request lifecycles adds performance overhead.
   - Saves patterns as tuples mapping regex objects to placeholder replacement strings (e.g. `[REDACTED_SSN]`).

3. Repository Functions:
   - `scrub_pii(text)`: Runs PII scrubbing. Loops through compiled tuple structures and applies regex replacements.
"""

import re

# ==========================================
# REGULAR EXPRESSION PATTERNS
# ==========================================
# We compile regular expressions at module import time.
# Pre-compilation parses and saves the search state machine, avoiding matching penalties on each function call.
PII_PATTERNS = [
    # SSN: Matches the standard 3-2-4 hyphenated layout (e.g. 000-00-0000).
    # \b matches word boundaries, \d{N} matches exactly N digits.
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[REDACTED_SSN]'),
    
    # Credit Card: Matches standard card lengths (13 to 16 digits), allowing hyphens or spaces.
    # (?:\d[ -]*?) matches digits followed by optional spaces or hyphens without storing grouping captures.
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), '[REDACTED_CREDIT_CARD]'),
    
    # Email: Matches alphanumeric email layouts (e.g. name@domain.com).
    # [A-Za-z0-9._%+-]+ matches name prefixes, and \.[A-Z|a-z]{2,7} validates domain extensions.
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), '[REDACTED_EMAIL]'),
    
    # Phone: Matches US phone numbers, supporting country codes (+1), parenthesis area codes, and separators.
    # ([0-9]{3}) matches digit groupings.
    (re.compile(r'\b(?:\+?1[-.●]?)?\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})\b'), '[REDACTED_PHONE]')
]


def scrub_pii(text: str) -> str:
    """
    Scans a raw string and redacts PII occurrences using placeholders.

    Purpose:
        Protects client privacy by removing sensitive PII before passing prompts to external LLMs.

    Parameters:
        text (str): The raw text content to analyze.

    Returns:
        str: The sanitized text with redacted placeholders replacing sensitive data.

    Side Effects / State Changes:
        - None.

    Errors / Exceptions:
        - None. Returns input text unchanged if it is empty or None.
    """
    # Guard clause: return the input if it is empty, None, or a falsy value.
    if not text:
        return text
    
    # Assign the input string to a local variable for modification.
    scrubbed_text = text
    # Iteratively apply each pattern in our list.
    for pattern, replacement in PII_PATTERNS:
        # Use pattern.sub to replace matching PII with the redaction placeholder.
        scrubbed_text = pattern.sub(replacement, scrubbed_text)
        
    # Return the redacted text.
    return scrubbed_text

