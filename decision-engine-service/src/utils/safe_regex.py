"""
Safe Regex Utilities

Protection against ReDoS (Regular Expression Denial of Service) attacks.
Provides input length limits and safe pattern matching functions.

Issue #541: Potential ReDoS in URL regex patterns
"""

import re
from typing import Optional, Pattern

# Maximum input length for regex operations
# Prevents exponential backtracking on long malicious strings
MAX_INPUT_LENGTH = 2048


def safe_search(
    pattern: str | Pattern[str],
    text: str,
    flags: int = 0,
    max_length: int = MAX_INPUT_LENGTH,
) -> Optional[re.Match[str]]:
    """
    Safely search for a regex pattern with input length limit.

    Args:
        pattern: Regex pattern (string or compiled)
        text: Input text to search
        flags: Regex flags (ignored if pattern is compiled)
        max_length: Maximum input length (default: 2048)

    Returns:
        Match object if found, None otherwise

    Note:
        Truncates input to max_length to prevent ReDoS.
        For URL matching, 2048 chars is sufficient (URLs rarely exceed 2000).
    """
    if not text:
        return None

    # Truncate input to prevent ReDoS
    safe_text = text[:max_length]

    if isinstance(pattern, str):
        return re.search(pattern, safe_text, flags)
    return pattern.search(safe_text)


def safe_match(
    pattern: str | Pattern[str],
    text: str,
    flags: int = 0,
    max_length: int = MAX_INPUT_LENGTH,
) -> Optional[re.Match[str]]:
    """
    Safely match a regex pattern at the start of string with input length limit.

    Args:
        pattern: Regex pattern (string or compiled)
        text: Input text to match
        flags: Regex flags (ignored if pattern is compiled)
        max_length: Maximum input length (default: 2048)

    Returns:
        Match object if found, None otherwise
    """
    if not text:
        return None

    safe_text = text[:max_length]

    if isinstance(pattern, str):
        return re.match(pattern, safe_text, flags)
    return pattern.match(safe_text)


def safe_any_match(
    patterns: list[str],
    text: str,
    flags: int = 0,
    max_length: int = MAX_INPUT_LENGTH,
) -> bool:
    """
    Check if any pattern matches the text, with input length limit.

    Args:
        patterns: List of regex patterns
        text: Input text to search
        flags: Regex flags
        max_length: Maximum input length (default: 2048)

    Returns:
        True if any pattern matches, False otherwise
    """
    if not text:
        return False

    safe_text = text[:max_length]
    return any(re.search(p, safe_text, flags) for p in patterns)
