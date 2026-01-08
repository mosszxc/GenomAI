"""
Creative Pipeline Models

Models for the creative processing pipeline workflow.
Replaces: decision_engine_input.json, idea_registry_output.json
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CreativeInput:
    """Input for CreativePipelineWorkflow."""

    creative_id: str
    tracker_id: Optional[str] = None
    source_type: str = "user"  # user | spy | historical
    buyer_id: Optional[str] = None


@dataclass
class TranscriptResult:
    """Result from transcription activity."""

    creative_id: str
    transcript_id: str
    transcript_text: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None


@dataclass
class DecompositionResult:
    """Result from LLM decomposition activity."""

    creative_id: str
    decomposed_creative_id: str
    canonical_hash: str
    payload: Dict[str, Any]
    # Extracted components
    angle_type: Optional[str] = None
    core_belief: Optional[str] = None
    promise_type: Optional[str] = None
    hook_type: Optional[str] = None
    cta_type: Optional[str] = None
    emotion_primary: Optional[str] = None


@dataclass
class PipelineResult:
    """Final result of CreativePipelineWorkflow."""

    creative_id: str
    idea_id: Optional[str] = None
    idea_status: str = "new"  # new | reused
    decision_id: Optional[str] = None
    decision_type: Optional[str] = None  # APPROVE | REJECT | DEFER
    hypothesis_id: Optional[str] = None
    hypothesis_count: int = 0
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None
