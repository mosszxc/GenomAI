"""
Time Decay utilities for Learning Loop.

Based on LEARNING_MEMORY_POLICY.md:
- Day 0: confidence_weight = 1.0
- ~30 days: confidence_weight ~ 0.3-0.4
- ~60 days: confidence_weight ~ 0.1
- ~90 days: confidence_weight ~ 0.0
"""

from datetime import datetime, date
from typing import Union


def time_decay(days_since_outcome: int, half_life: int = 20) -> float:
    """
    Calculate time decay factor using exponential decay.

    Args:
        days_since_outcome: Number of days since the outcome occurred
        half_life: Number of days for confidence to decay by half (default: 20)

    Returns:
        Decay factor between 0.0 and 1.0

    Examples:
        >>> time_decay(0)   # 1.0
        >>> time_decay(20)  # ~0.5
        >>> time_decay(30)  # ~0.35
        >>> time_decay(60)  # ~0.12
        >>> time_decay(90)  # ~0.04
    """
    if days_since_outcome < 0:
        return 1.0

    return max(0.0, 2 ** (-days_since_outcome / half_life))


def days_since(reference_date: Union[datetime, date, str]) -> int:
    """
    Calculate days elapsed since a reference date.

    Args:
        reference_date: The date to calculate from (datetime, date, or ISO string)

    Returns:
        Number of days since reference_date (0 if today or future)
    """
    today = date.today()

    if isinstance(reference_date, str):
        # Parse ISO date string (YYYY-MM-DD or datetime)
        reference_date = datetime.fromisoformat(reference_date.replace('Z', '+00:00'))

    if isinstance(reference_date, datetime):
        reference_date = reference_date.date()

    delta = today - reference_date
    return max(0, delta.days)


def apply_time_decay(
    base_value: float,
    outcome_date: Union[datetime, date, str],
    half_life: int = 20
) -> float:
    """
    Apply time decay to a base value.

    Args:
        base_value: The original value to decay
        outcome_date: When the outcome occurred
        half_life: Decay half-life in days

    Returns:
        Decayed value
    """
    days = days_since(outcome_date)
    decay_factor = time_decay(days, half_life)
    return base_value * decay_factor
