"""
Safe parsing utilities for API responses.
"""


def safe_int(value, default: int = 0) -> int:
    """
    Safely convert a value to int.

    Args:
        value: Value to convert (can be str, int, float, None)
        default: Default value if conversion fails

    Returns:
        int: Converted value or default
    """
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert a value to float.

    Args:
        value: Value to convert (can be str, int, float, None)
        default: Default value if conversion fails

    Returns:
        float: Converted value or default
    """
    try:
        return float(value or default)
    except (ValueError, TypeError):
        return default
