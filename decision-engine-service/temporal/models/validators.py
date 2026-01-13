"""
Input Validators for Temporal Activities

Reusable validation functions for common data types:
- UUID (database IDs)
- SHA256 hash (canonical_hash)
- URL (video_url)
- Status enums
"""

import re
import uuid
from typing import Any, Optional

# Maximum input length for regex operations to prevent ReDoS
MAX_URL_LENGTH = 2048

# Valid characters for SHA256 hex string
HEX_CHARS = set("0123456789abcdef")

# Compiled regex patterns for performance
URL_PATTERN = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",  # path
    re.IGNORECASE,
)


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate UUID string format.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Returns:
        Validated UUID string

    Raises:
        ValueError: If not a valid UUID
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    try:
        # Parse and normalize to standard format
        parsed = uuid.UUID(value)
        return str(parsed)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"{field_name} must be a valid UUID, got: {value!r}") from e


def validate_sha256_hash(value: str, field_name: str = "canonical_hash") -> str:
    """
    Validate SHA256 hash format (64 hex characters).

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Returns:
        Validated hash string (lowercased)

    Raises:
        ValueError: If not a valid SHA256 hash
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    value = value.lower()

    if len(value) != 64:
        raise ValueError(f"{field_name} must be 64 characters (SHA256), got {len(value)}")

    if not all(c in HEX_CHARS for c in value):
        raise ValueError(f"{field_name} must contain only hex characters")

    return value


def validate_url(value: str, field_name: str = "url") -> str:
    """
    Validate URL format.

    Includes input length limit to prevent ReDoS attacks.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Returns:
        Validated URL string

    Raises:
        ValueError: If not a valid URL or exceeds max length
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    # ReDoS protection: limit input length
    if len(value) > MAX_URL_LENGTH:
        raise ValueError(f"{field_name} exceeds maximum length of {MAX_URL_LENGTH}")

    if not URL_PATTERN.match(value):
        raise ValueError(f"{field_name} must be a valid HTTP/HTTPS URL, got: {value!r}")

    return value


def validate_optional_uuid(value: Optional[str], field_name: str = "id") -> Optional[str]:
    """
    Validate optional UUID string.

    Args:
        value: String to validate or None
        field_name: Name of field for error messages

    Returns:
        Validated UUID string or None

    Raises:
        ValueError: If provided but not a valid UUID
    """
    if value is None:
        return None
    return validate_uuid(value, field_name)


def validate_enum(
    value: str,
    allowed_values: set[str],
    field_name: str = "status",
) -> str:
    """
    Validate string is one of allowed values.

    Args:
        value: String to validate
        allowed_values: Set of valid values
        field_name: Name of field for error messages

    Returns:
        Validated string

    Raises:
        ValueError: If not in allowed values
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if value not in allowed_values:
        raise ValueError(f"{field_name} must be one of {sorted(allowed_values)}, got: {value!r}")

    return value


def validate_dict_payload(value: Any, field_name: str = "payload") -> dict:
    """
    Validate payload is a dict (not string, null, array, etc.).

    Args:
        value: Value to validate
        field_name: Name of field for error messages

    Returns:
        Validated dict

    Raises:
        ValueError: If not a dict
    """
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict, got {type(value).__name__}: {value!r:.200}")
    return value


# Allowed characters for safe string interpolation in URLs
# Alphanumeric, underscore, hyphen - safe for PostgREST query params
SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_safe_string(value: str, field_name: str = "value", max_length: int = 100) -> str:
    """
    Validate string is safe for URL interpolation (no injection risk).

    Only allows alphanumeric characters, underscores, and hyphens.
    This prevents PostgREST query manipulation and URL injection.

    Args:
        value: String to validate
        field_name: Name of field for error messages
        max_length: Maximum allowed length

    Returns:
        Validated string

    Raises:
        ValueError: If string contains unsafe characters
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length}")

    if not SAFE_STRING_PATTERN.match(value):
        raise ValueError(
            f"{field_name} contains unsafe characters, "
            f"only alphanumeric, underscore and hyphen allowed: {value!r}"
        )

    return value


def validate_optional_safe_string(
    value: Optional[str], field_name: str = "value", max_length: int = 100
) -> Optional[str]:
    """
    Validate optional string is safe for URL interpolation.

    Args:
        value: String to validate or None
        field_name: Name of field for error messages
        max_length: Maximum allowed length

    Returns:
        Validated string or None

    Raises:
        ValueError: If provided but contains unsafe characters
    """
    if value is None:
        return None
    return validate_safe_string(value, field_name, max_length)


# Status enum values for validation
CREATIVE_STATUSES = {"registered", "processing", "processed", "failed"}
IDEA_STATUSES = {"active", "inactive", "archived"}
SOURCE_TYPES = {"telegram", "keitaro", "historical", "spy", "user"}
