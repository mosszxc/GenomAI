"""
CHECK 4: Risk Budget

Purpose: Control exposure
Rule: If max_active_ideas exceeded → DEFER

MVP: Basic risk cap check
"""


def risk_budget(idea, system_state):
    """
    Check risk budget constraint

    Args:
        idea: Idea object
        system_state: System state with active_ideas_count and max_active_ideas

    Returns:
        dict: Check result with 'name', 'result' ('PASSED' or 'FAILED'), and 'details'
    """
    active_ideas_count = system_state.get("active_ideas_count", 0)
    max_active_ideas = system_state.get("max_active_ideas", 100)

    if active_ideas_count >= max_active_ideas:
        return {
            "name": "risk_budget",
            "result": "FAILED",
            "details": {
                "reason": "max_active_ideas_exceeded",
                "active_ideas_count": active_ideas_count,
                "max_active_ideas": max_active_ideas,
            },
        }

    return {
        "name": "risk_budget",
        "result": "PASSED",
        "details": {
            "active_ideas_count": active_ideas_count,
            "max_active_ideas": max_active_ideas,
            "remaining_slots": max_active_ideas - active_ideas_count,
        },
    }
