"""
Knowledge Extraction Models

Dataclasses for Knowledge Extraction workflows.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class KnowledgeSourceInput:
    """Input for transcript ingestion."""

    title: str
    content: str
    source_type: str  # 'youtube', 'file', 'manual'
    url: Optional[str] = None
    created_by: Optional[str] = None  # admin telegram_id


@dataclass
class KnowledgeIngestionResult:
    """Result of transcript ingestion."""

    source_id: str
    extraction_count: int
    status: str  # 'pending_review', 'no_extractions', 'error'
    error_message: Optional[str] = None


@dataclass
class KnowledgeExtraction:
    """Single knowledge extraction."""

    id: str
    source_id: str
    knowledge_type: (
        str  # 'premise', 'creative_attribute', 'process_rule', 'component_weight'
    )
    name: str
    description: Optional[str]
    payload: dict
    confidence_score: Optional[float]
    supporting_quotes: Optional[List[str]]
    status: str  # 'pending', 'approved', 'rejected', 'applied'


@dataclass
class ApplyKnowledgeInput:
    """Input for applying approved knowledge."""

    extraction_id: str
    reviewed_by: Optional[str] = None


@dataclass
class ApplyKnowledgeResult:
    """Result of knowledge application."""

    extraction_id: str
    target_table: str
    target_id: Optional[str]
    operation: str  # 'insert', 'update', 'schema_extend'
    success: bool
    error_message: Optional[str] = None
    note: Optional[str] = None


@dataclass
class ReviewDecision:
    """User decision on extraction."""

    extraction_id: str
    decision: str  # 'approve', 'reject', 'skip'
    notes: Optional[str] = None
