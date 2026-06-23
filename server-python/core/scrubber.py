"""
Data Privacy & PII Scrubber.
Responsibility: Automatically detects and redacts Personally Identifiable Information (PII) 
from text before it gets sent to external LLM providers or saved in the database.
This is critical for enterprise compliance (GDPR, HIPAA).
"""
import re

# ==========================================
# REGULAR EXPRESSION PATTERNS
# ==========================================
# We define these regexes once at module load time for performance.
# Compiling them on every request would be computationally expensive.
PII_PATTERNS = [
    # SSN: Matches the standard 3-2-4 hyphenated format
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[REDACTED_SSN]'),
    
    # Credit Card: Matches 13 to 19 digits, accounting for spaces or hyphens
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), '[REDACTED_CREDIT_CARD]'),
    
    # Email addresses: Standard alphanumeric matching before and after the @ symbol
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), '[REDACTED_EMAIL]'),
    
    # Phone numbers: Matches basic US patterns including optional +1, area codes in parentheses, and different separators
    (re.compile(r'\b(?:\+?1[-.●]?)?\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})\b'), '[REDACTED_PHONE]')
]

def scrub_pii(text: str) -> str:
    """
    Takes a raw string and returns it with all detected PII replaced by redaction markers.
    Data Flow: Input Text -> Loop through Regex Patterns -> Return Clean Text.
    """
    if not text:
        return text
    
    scrubbed_text = text
    # Iteratively apply each pattern. 
    # E.g., First remove SSNs, then remove Credit Cards from the *remaining* text.
    for pattern, replacement in PII_PATTERNS:
        scrubbed_text = pattern.sub(replacement, scrubbed_text)
        
    return scrubbed_text
