"""
Hygiene System Models

Dataclasses for Hygiene workflows (cleanup, health checks, alerts).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"  # Immediate send (connection fail, score < 0.5)
    WARNING = "warning"    # Batch at next run (orphans, backlog)
    INFO = "info"          # Daily digest (stats, trends)


@dataclass
class CleanupStats:
    """Stats from cleanup operations."""
    import_queue_deleted: int = 0
    knowledge_deleted: int = 0
    raw_metrics_deleted: int = 0
    buyer_states_deleted: int = 0
    staleness_archived: int = 0

    def total(self) -> int:
        return (
            self.import_queue_deleted
            + self.knowledge_deleted
            + self.raw_metrics_deleted
            + self.buyer_states_deleted
            + self.staleness_archived
        )

    def to_dict(self) -> dict:
        return {
            "import_queue": self.import_queue_deleted,
            "knowledge": self.knowledge_deleted,
            "raw_metrics": self.raw_metrics_deleted,
            "buyer_states": self.buyer_states_deleted,
            "staleness": self.staleness_archived,
        }


@dataclass
class IntegrityIssue:
    """Single integrity issue found during checks."""
    severity: str  # critical, warning, info
    table: str
    issue_type: str  # orphan, duplicate, stuck
    count: int
    sample_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "table": self.table,
            "issue_type": self.issue_type,
            "count": self.count,
            "sample_ids": self.sample_ids[:5],  # Limit to 5 samples
        }


@dataclass
class HealthMetrics:
    """Health check metrics."""
    supabase_connected: bool = True
    supabase_latency_ms: Optional[float] = None
    temporal_connected: bool = True
    temporal_latency_ms: Optional[float] = None
    table_sizes: Dict[str, int] = field(default_factory=dict)
    pending_counts: Dict[str, int] = field(default_factory=dict)
    health_score: float = 1.0  # 0.0 = critical, 1.0 = healthy

    def compute_score(self) -> float:
        """Compute weighted health score."""
        score = 1.0

        # Connection failures are critical
        if not self.supabase_connected:
            score -= 0.5
        if not self.temporal_connected:
            score -= 0.3

        # High latency reduces score
        if self.supabase_latency_ms and self.supabase_latency_ms > 3000:
            score -= 0.1
        if self.temporal_latency_ms and self.temporal_latency_ms > 3000:
            score -= 0.1

        # Large pending backlog reduces score
        total_pending = sum(self.pending_counts.values())
        if total_pending > 100:
            score -= 0.1
        elif total_pending > 50:
            score -= 0.05

        self.health_score = max(0.0, min(1.0, score))
        return self.health_score


# ─────────────────────────────────────────────────────────────────────────────
# Health Check Workflow Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HealthCheckInput:
    """Input for HealthCheckWorkflow."""
    check_supabase: bool = True
    check_temporal: bool = True
    check_table_sizes: bool = True
    check_pending: bool = True
    alert_on_warning: bool = True
    alert_on_critical: bool = True
    critical_threshold: float = 0.5  # Below this = CRITICAL alert
    warning_threshold: float = 0.8   # Below this = WARNING alert


@dataclass
class HealthCheckResult:
    """Result of HealthCheckWorkflow."""
    health_score: float = 1.0
    supabase_ok: bool = True
    temporal_ok: bool = True
    table_sizes: Dict[str, int] = field(default_factory=dict)
    pending_counts: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    alerts_sent: int = 0
    completed_at: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Extended Maintenance Models (cleanup additions)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CleanupInput:
    """Input for cleanup operations."""
    run_cleanup: bool = True
    import_queue_retention_days: int = 7
    knowledge_retention_days: int = 30
    buyer_states_retention_days: int = 30
    staleness_archive_days: int = 90


@dataclass
class HygieneReport:
    """Complete hygiene report for storage."""
    report_type: str  # 'maintenance' or 'health_check'
    health_score: Optional[float] = None
    supabase_connected: Optional[bool] = None
    supabase_latency_ms: Optional[float] = None
    temporal_connected: Optional[bool] = None
    temporal_latency_ms: Optional[float] = None
    cleanup_stats: Optional[Dict] = None
    integrity_issues: Optional[List[Dict]] = None
    table_sizes: Optional[Dict[str, int]] = None
    pending_counts: Optional[Dict[str, int]] = None
    alerts_sent: int = 0
    alert_details: Optional[List[Dict]] = None
    workflow_id: Optional[str] = None
