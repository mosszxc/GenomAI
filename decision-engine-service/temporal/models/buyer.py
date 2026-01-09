"""
Buyer Models for Temporal Workflows

Models for buyer onboarding and historical import workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class OnboardingState(str, Enum):
    """Buyer onboarding state machine states."""

    AWAITING_NAME = "AWAITING_NAME"
    AWAITING_GEO = "AWAITING_GEO"
    AWAITING_VERTICAL = "AWAITING_VERTICAL"
    AWAITING_KEITARO = "AWAITING_KEITARO"
    LOADING_HISTORY = "LOADING_HISTORY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


@dataclass
class BuyerOnboardingInput:
    """Input for BuyerOnboardingWorkflow."""

    telegram_id: str
    telegram_username: Optional[str] = None
    chat_id: str = ""

    def __post_init__(self):
        if not self.chat_id:
            self.chat_id = self.telegram_id


@dataclass
class CreateBuyerInput:
    """Input for create_buyer activity."""

    telegram_id: str
    telegram_username: Optional[str] = None
    name: Optional[str] = None
    geos: Optional[List[str]] = None
    verticals: Optional[List[str]] = None
    keitaro_source: Optional[str] = None


@dataclass
class BuyerData:
    """Buyer data collected during onboarding."""

    telegram_id: str
    telegram_username: Optional[str] = None
    name: Optional[str] = None
    geos: List[str] = field(default_factory=list)
    verticals: List[str] = field(default_factory=list)
    keitaro_source: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for database insert."""
        return {
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "name": self.name,
            "geos": self.geos if self.geos else None,
            "verticals": self.verticals if self.verticals else None,
            "keitaro_source": self.keitaro_source,
            "status": "active",
        }


@dataclass
class BuyerOnboardingResult:
    """Result of buyer onboarding workflow."""

    buyer_id: Optional[str] = None
    state: str = OnboardingState.AWAITING_NAME.value
    completed: bool = False
    error: Optional[str] = None
    historical_import_started: bool = False
    campaigns_count: int = 0


@dataclass
class BuyerMessage:
    """Signal message from user during onboarding."""

    text: str
    message_id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HistoricalImportInput:
    """Input for HistoricalImportWorkflow."""

    buyer_id: str
    keitaro_source: str
    date_from: Optional[str] = None  # ISO date string
    date_to: Optional[str] = None  # ISO date string
    batch_size: int = 10


@dataclass
class HistoricalImportResult:
    """Result of historical import workflow."""

    buyer_id: str
    keitaro_source: str
    total_campaigns: int = 0
    processed_campaigns: int = 0
    queued_creatives: int = 0
    failed_imports: int = 0
    error: Optional[str] = None
    completed: bool = False


@dataclass
class CampaignData:
    """Campaign data from Keitaro."""

    campaign_id: str
    name: str
    video_url: Optional[str] = None
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    cost: float = 0.0
    status: str = "pending"


# Valid geos and verticals for validation
VALID_GEOS = [
    "US", "UK", "DE", "FR", "IT", "ES", "NL", "BE", "AT", "CH",
    "AU", "CA", "NZ", "IE", "PL", "CZ", "HU", "RO", "BG", "SE",
    "NO", "DK", "FI", "PT", "GR", "TR", "RU", "UA", "BY", "KZ",
    "BR", "MX", "AR", "CO", "CL", "PE", "VE", "EC", "BO", "PY",
    "IN", "ID", "TH", "VN", "PH", "MY", "SG", "JP", "KR", "TW",
    "ZA", "NG", "EG", "KE", "MA", "TN", "DZ", "GH", "TZ", "UG",
]

VALID_VERTICALS = [
    "gambling", "nutra", "crypto", "dating", "ecommerce",
    "finance", "gaming", "sweepstakes", "insurance", "health",
]
