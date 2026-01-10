"""
CHECK 3: Fatigue Constraint

Purpose: Prevent audience burnout
Rule: If fatigue_level ≥ angle AND novelty_bucket = low → REJECT

MVP: Заглушка (always passes)
"""


def fatigue_constraint(idea, fatigue_state=None):
    """
    Check fatigue constraint

    Args:
        idea: Idea object
        fatigue_state: Fatigue state (optional)

    Returns:
        dict: Check result with 'name', 'result' ('PASSED' or 'FAILED'), and 'details'
    """
    # MVP: Always pass (no fatigue logic yet)
    # Future implementation:
    # - Check fatigue_level
    # - Check novelty_bucket
    # - Apply fatigue rules

    return {
        "name": "fatigue_constraint",
        "result": "PASSED",
        "details": {"note": "MVP: fatigue check not implemented"},
    }
