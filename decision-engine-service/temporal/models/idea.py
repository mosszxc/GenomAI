"""
Idea Registry Models

Models for the Idea Registry workflow/activity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class IdeaInput:
    """Input for idea registry activity."""

    creative_id: str
    decomposed_creative_id: str
    canonical_hash: str
    schema_version: str = "v1"


@dataclass
class IdeaResult:
    """Result from idea registry activity."""

    idea_id: str
    status: str  # new | reused
    canonical_hash: str
    avatar_id: Optional[str] = None
    avatar_status: Optional[str] = None  # new | existing
    created_at: Optional[datetime] = None
