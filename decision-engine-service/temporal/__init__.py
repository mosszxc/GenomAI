"""
GenomAI Temporal Workflow Orchestration

This module contains Temporal workflows and activities for the GenomAI
creative decision system, replacing n8n workflow orchestration.

Structure:
- workflows/: Temporal workflow definitions
- activities/: Activity implementations (external calls, DB operations)
- models/: Pydantic models for workflow inputs/outputs
- config.py: Environment configuration
- client.py: Temporal client singleton
- worker.py: Worker entrypoint
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from temporal.config import Settings

__all__ = ["settings", "get_settings"]


def get_settings() -> "Settings":
    """Get settings singleton. Validates required env vars on first call."""
    from temporal.config import get_settings as _get_settings

    return _get_settings()


def __getattr__(name: str):
    """Lazy loading for backward compatibility with `from temporal import settings`."""
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
