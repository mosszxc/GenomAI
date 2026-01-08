"""
Decision Engine Models

Models for the Decision Engine workflow/activity.
Replaces: decision_engine_input.json, decision_engine_output.json
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class DecisionInput:
    """Input for decision engine activity."""

    idea_id: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class CheckResult:
    """Result of a single decision check."""

    check_name: str
    order: int
    passed: bool
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class DecisionTrace:
    """Trace of decision engine execution."""

    id: str
    decision_id: str
    checks: List[CheckResult]
    execution_time_ms: float
    created_at: datetime


@dataclass
class DecisionResult:
    """Result from decision engine activity."""

    decision_id: str
    idea_id: str
    decision_type: str  # APPROVE | REJECT | DEFER
    decision_reason: str
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    trace: Optional[DecisionTrace] = None
    timestamp: Optional[datetime] = None

    @property
    def is_approved(self) -> bool:
        return self.decision_type == "APPROVE"

    @property
    def is_rejected(self) -> bool:
        return self.decision_type == "REJECT"

    @property
    def is_deferred(self) -> bool:
        return self.decision_type == "DEFER"
