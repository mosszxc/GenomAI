"""
CHECK 2: Death Memory

Purpose: Prevent repetition of dead ideas
Rule: If Idea or its cluster is marked as DEAD → REJECT
"""


def death_memory(idea, death_memory=None):
    """
    Check if idea or cluster is marked as dead

    Args:
        idea: Idea object
        death_memory: Death memory state (optional)

    Returns:
        dict: Check result with 'name', 'result' ('PASSED' or 'FAILED'), and 'details'
    """
    # Check death_state (soft_dead, hard_dead, permanent_dead)
    death_state = idea.get("death_state")
    if death_state is not None:
        return {
            "name": "death_memory",
            "result": "FAILED",
            "details": {
                "reason": "idea_marked_as_dead",
                "idea_id": idea.get("id"),
                "death_state": death_state,
            },
        }

    # Future: Check cluster death status
    # if death_memory and death_memory.get('cluster_dead'):
    #     return {
    #         'name': 'death_memory',
    #         'result': 'FAILED',
    #         'details': {'reason': 'cluster_marked_as_dead'}
    #     }

    return {"name": "death_memory", "result": "PASSED", "details": {}}
