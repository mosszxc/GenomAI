"""
Validation utilities
"""

from __future__ import annotations


VALID_DECISION_MODES = ("strict", "advisory")


def validate_decision_request(body: dict) -> str | None:
    """
    Validate Decision Request

    Optimized: Only idea_id is required. Render API will load all necessary data.

    Args:
        body: Request body

    Returns:
        str: Error message if invalid, None if valid
    """
    if not body:
        return "Request body is required"

    # idea_id is required (optimized approach)
    if not body.get("idea_id"):
        return "idea_id is required"

    if not isinstance(body.get("idea_id"), str):
        return "idea_id must be a string (UUID)"

    # mode validation (optional, defaults to "strict")
    mode = body.get("mode")
    if mode is not None:
        if not isinstance(mode, str):
            return "mode must be a string"
        if mode not in VALID_DECISION_MODES:
            return f"mode must be one of: {', '.join(VALID_DECISION_MODES)}"

    # Optional fields (for backward compatibility)
    if body.get("idea") and not isinstance(body.get("idea"), dict):
        return "idea must be an object (if provided)"

    if body.get("system_state") and not isinstance(body.get("system_state"), dict):
        return "system_state must be an object (if provided)"

    if body.get("fatigue_state") and not isinstance(body.get("fatigue_state"), dict):
        return "fatigue_state must be an object (if provided)"

    if body.get("death_memory") and not isinstance(body.get("death_memory"), dict):
        return "death_memory must be an object (if provided)"

    return None  # Valid
