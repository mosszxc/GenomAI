"""
Temporal Workflow Models

Pydantic models for workflow inputs/outputs.
These replace the n8n contracts (infrastructure/contracts/*.json).
"""

from temporal.models.creative import (
    CreativeInput,
    TranscriptResult,
    DecompositionResult,
    PipelineResult,
)
from temporal.models.decision import (
    DecisionInput,
    DecisionResult,
    DecisionTrace,
)
from temporal.models.idea import (
    IdeaInput,
    IdeaResult,
)
from temporal.models.buyer import (
    OnboardingState,
    BuyerOnboardingInput,
    BuyerData,
    BuyerOnboardingResult,
    BuyerMessage,
    HistoricalImportInput,
    HistoricalImportResult,
    CampaignData,
)
from temporal.models.hygiene import (
    AlertSeverity,
    CleanupStats,
    IntegrityIssue,
    HealthMetrics,
    HealthCheckInput,
    HealthCheckResult,
    CleanupInput,
    HygieneReport,
)

__all__ = [
    "CreativeInput",
    "TranscriptResult",
    "DecompositionResult",
    "PipelineResult",
    "DecisionInput",
    "DecisionResult",
    "DecisionTrace",
    "IdeaInput",
    "IdeaResult",
    "OnboardingState",
    "BuyerOnboardingInput",
    "BuyerData",
    "BuyerOnboardingResult",
    "BuyerMessage",
    "HistoricalImportInput",
    "HistoricalImportResult",
    "CampaignData",
    # Hygiene
    "AlertSeverity",
    "CleanupStats",
    "IntegrityIssue",
    "HealthMetrics",
    "HealthCheckInput",
    "HealthCheckResult",
    "CleanupInput",
    "HygieneReport",
]
