"""
Validation utilities
"""

from __future__ import annotations


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
