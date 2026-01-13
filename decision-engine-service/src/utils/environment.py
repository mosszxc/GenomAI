"""
Environment Weighting utilities for Learning Loop.

Based on LEARNING_MEMORY_POLICY.md:
- Environment Context Weighting adjusts outcome impact
- Degraded environment: bad outcome doesn't kill idea, good outcome boosts confidence
- This is NOT normalization, it's soft weight adjustment
"""

from typing import Optional


def environment_weight(env_ctx: Optional[dict]) -> float:
    """
    Calculate environment weight factor for outcome.

    Args:
        env_ctx: Environment context dictionary from outcome_aggregates.environment_ctx

    Returns:
        Weight factor between 0.0 and 1.5

    Rules:
        - Normal environment: 1.0
        - Degraded environment with bad outcome: 0.3 (reduces negative impact)
        - Degraded environment with good outcome: 1.3 (amplifies positive impact)
    """
    if env_ctx is None:
        return 1.0

    # Check for degraded environment markers
    is_degraded = (
        env_ctx.get("degraded", False)
        or env_ctx.get("market_stress", False)
        or env_ctx.get("seasonality_impact", "normal") == "high"
    )

    if not is_degraded:
        return 1.0

    # Degraded environment - weight depends on outcome direction
    # Note: actual direction is applied in learning_loop.py
    # Here we return a marker that degraded = True
    return 0.3  # Will be adjusted based on outcome direction in apply_environment_weight


def apply_environment_weight(delta: float, env_ctx: Optional[dict]) -> float:
    """
    Apply environment weight to confidence/fatigue delta.

    Args:
        delta: The base confidence or fatigue change
        env_ctx: Environment context from outcome

    Returns:
        Weighted delta

    Logic:
        - Normal env: delta unchanged
        - Degraded env + negative delta: delta * 0.3 (reduce punishment)
        - Degraded env + positive delta: delta * 1.3 (amplify reward)
    """
    if env_ctx is None:
        return delta

    is_degraded = (
        env_ctx.get("degraded", False)
        or env_ctx.get("market_stress", False)
        or env_ctx.get("seasonality_impact", "normal") == "high"
    )

    if not is_degraded:
        return delta

    if delta < 0:
        # Bad outcome in degraded environment - reduce punishment
        return delta * 0.3
    else:
        # Good outcome in degraded environment - amplify reward
        return delta * 1.3


def is_environment_degraded(env_ctx: Optional[dict]) -> bool:
    """
    Check if environment is degraded.

    Args:
        env_ctx: Environment context dictionary

    Returns:
        True if environment is degraded
    """
    if env_ctx is None:
        return False

    return bool(
        env_ctx.get("degraded", False)
        or env_ctx.get("market_stress", False)
        or env_ctx.get("seasonality_impact", "normal") == "high"
    )
