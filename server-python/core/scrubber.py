import re

# Simple Regex patterns for PII scrubbing
PII_PATTERNS = [
    # SSN: 3 digits, hyphen, 2 digits, hyphen, 4 digits
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[REDACTED_SSN]'),
    # Credit Card: 13-19 digits, possibly separated by space or hyphen
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), '[REDACTED_CREDIT_CARD]'),
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), '[REDACTED_EMAIL]'),
    # Phone numbers (basic US pattern)
    (re.compile(r'\b(?:\+?1[-.●]?)?\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})\b'), '[REDACTED_PHONE]')
]

def scrub_pii(text: str) -> str:
    """Scrub PII (SSN, Credit Cards, Emails, Phone Numbers) from the input text."""
    if not text:
        return text
    
    scrubbed_text = text
    for pattern, replacement in PII_PATTERNS:
        scrubbed_text = pattern.sub(replacement, scrubbed_text)
        
    return scrubbed_text
