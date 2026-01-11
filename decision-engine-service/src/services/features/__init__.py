"""
ML Feature implementations.

Each feature module provides:
- SQL_DEFINITION: SQL query for computing feature
- compute_for_idea(idea_id): Compute feature value for single idea
- compute_all(): Batch compute for all entities

Issue: #304
"""

from src.services.features.component_pair_winrate import (
    compute_pair_winrate_for_idea,
    get_pair_stats,
    register_feature,
    SQL_DEFINITION,
)

__all__ = [
    "compute_pair_winrate_for_idea",
    "get_pair_stats",
    "register_feature",
    "SQL_DEFINITION",
]
