"""
Keitaro API Activities

Activities for fetching metrics from Keitaro tracker.
Uses POST /admin_api/v1/report/build endpoint.

Based on docs/layer-4-implementation-planning/KEITARO_API_DATA_CLASSIFICATION.md
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError

from temporal.config import settings
from src.utils.parsing import safe_int, safe_float


@dataclass
class KeitaroMetrics:
    """Metrics from Keitaro API"""

    tracker_id: str
    date: str  # ISO date string
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    cost: float = 0.0
    profit_confirmed: float = 0.0  # Confirmed profit from Keitaro

    def to_dict(self) -> dict:
        return {
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue": self.revenue,
            "cost": self.cost,
            "profit_confirmed": self.profit_confirmed,
        }


@dataclass
class GetAllTrackersInput:
    """Input for get_all_trackers activity"""

    interval: str = "yesterday"  # yesterday, today, last_7_days, etc.


@dataclass
class GetAllTrackersOutput:
    """Output from get_all_trackers activity"""

    tracker_ids: list[str]
    total: int


@dataclass
class GetTrackerMetricsInput:
    """Input for get_tracker_metrics activity"""

    tracker_id: str
    interval: str = "yesterday"


@dataclass
class GetTrackerMetricsOutput:
    """Output from get_tracker_metrics activity"""

    metrics: Optional[KeitaroMetrics]
    found: bool


def _get_keitaro_headers() -> dict:
    """Get headers for Keitaro API requests"""
    api_key = settings.external.keitaro_api_key
    if not api_key:
        raise ValueError("KEITARO_API_KEY not configured")

    return {"Api-Key": api_key, "Content-Type": "application/json"}


def _get_keitaro_url(path: str) -> str:
    """Build Keitaro API URL"""
    base_url = settings.external.keitaro_base_url
    if not base_url:
        raise ValueError("KEITARO_BASE_URL not configured")

    return f"{base_url.rstrip('/')}/admin_api/v1{path}"


@activity.defn
async def get_all_trackers(input: GetAllTrackersInput) -> GetAllTrackersOutput:
    """
    Get all active tracker IDs from Keitaro.

    Uses report/build with dimensions: ["sub_id_1"] to get unique tracker IDs.

    Args:
        input: Contains interval (yesterday, today, etc.)

    Returns:
        GetAllTrackersOutput with list of tracker_ids
    """
    activity.logger.info(f"Fetching all trackers for interval: {input.interval}")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks"],
        "dimensions": ["sub_id_1"],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    rows = data.get("rows", [])
    tracker_ids = [row.get("sub_id_1") for row in rows if row.get("sub_id_1")]

    activity.logger.info(f"Found {len(tracker_ids)} trackers")

    return GetAllTrackersOutput(tracker_ids=tracker_ids, total=len(tracker_ids))


@activity.defn
async def get_tracker_metrics(input: GetTrackerMetricsInput) -> GetTrackerMetricsOutput:
    """
    Get metrics for a specific tracker from Keitaro.

    Uses report/build with filter on sub_id_1.

    Args:
        input: Contains tracker_id and interval

    Returns:
        GetTrackerMetricsOutput with metrics or not found
    """
    activity.logger.info(f"Fetching metrics for tracker: {input.tracker_id}")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks", "conversions", "revenue", "cost", "profit_confirmed"],
        "filters": [
            {"name": "sub_id_1", "operator": "EQUALS", "expression": input.tracker_id}
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    rows = data.get("rows", [])

    if not rows:
        activity.logger.info(f"No metrics found for tracker: {input.tracker_id}")
        return GetTrackerMetricsOutput(metrics=None, found=False)

    row = rows[0]

    # Calculate date based on interval
    if input.interval == "yesterday":
        metrics_date = (datetime.now() - timedelta(days=1)).date().isoformat()
    elif input.interval == "today":
        metrics_date = datetime.now().date().isoformat()
    else:
        metrics_date = datetime.now().date().isoformat()

    metrics = KeitaroMetrics(
        tracker_id=input.tracker_id,
        date=metrics_date,
        clicks=safe_int(row.get("clicks", 0)),
        conversions=safe_int(row.get("conversions", 0)),
        revenue=safe_float(row.get("revenue", 0)),
        cost=safe_float(row.get("cost", 0)),
        profit_confirmed=safe_float(row.get("profit_confirmed", 0)),
    )

    activity.logger.info(
        f"Metrics for {input.tracker_id}: "
        f"clicks={metrics.clicks}, conversions={metrics.conversions}, "
        f"cost={metrics.cost}, profit_confirmed={metrics.profit_confirmed}"
    )

    return GetTrackerMetricsOutput(metrics=metrics, found=True)


@dataclass
class BatchMetricsInput:
    """Input for batch metrics fetch"""

    tracker_ids: list[str]
    interval: str = "yesterday"


@dataclass
class BatchMetricsOutput:
    """Output from batch metrics fetch"""

    metrics: list[KeitaroMetrics]
    failed_ids: list[str]


@dataclass
class GetCampaignsBySourceInput:
    """Input for get_campaigns_by_source activity"""

    source: str  # Keitaro source/affiliate parameter
    date_from: Optional[str] = None  # ISO date string
    date_to: Optional[str] = None  # ISO date string


@dataclass
class CampaignInfo:
    """Campaign information from Keitaro"""

    campaign_id: str
    name: str
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    cost: float = 0.0
    offer_id: Optional[str] = None
    landing_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue": self.revenue,
            "cost": self.cost,
        }


@dataclass
class GetCampaignsBySourceOutput:
    """Output from get_campaigns_by_source activity"""

    campaigns: list[CampaignInfo]
    total: int
    source: str


@activity.defn
async def get_campaigns_by_source(
    input: GetCampaignsBySourceInput,
) -> GetCampaignsBySourceOutput:
    """
    Get all campaigns for a specific source/affiliate from Keitaro.

    Fetches campaigns list and filters by:
    1. Campaign name contains source (e.g., "TU")
    2. Created within last 30 days (or specified date range)

    Args:
        input: Contains source and optional date range

    Returns:
        GetCampaignsBySourceOutput with list of campaigns
    """
    from datetime import datetime, timedelta

    activity.logger.info(f"Fetching campaigns for source: {input.source}")

    # Step 1: Get all campaigns from Keitaro
    url = _get_keitaro_url("/campaigns")
    headers = _get_keitaro_headers()

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        all_campaigns = response.json()

    # Step 2: Calculate date cutoff (last 30 days by default)
    if input.date_from:
        try:
            cutoff = datetime.fromisoformat(input.date_from)
        except ValueError:
            raise ApplicationError(
                f"Invalid date format: {input.date_from}", non_retryable=True
            )
    else:
        cutoff = datetime.utcnow() - timedelta(days=30)

    # Step 3: Filter campaigns by name and creation date
    source_upper = input.source.upper()
    campaigns = []

    for c in all_campaigns:
        name = c.get("name", "")
        created_at = c.get("created_at", "")

        # Filter by source in name (case-insensitive)
        if source_upper not in name.upper():
            continue

        # Filter by creation date
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", ""))
            if created_dt < cutoff:
                continue
        except (ValueError, TypeError):
            continue

        campaigns.append(
            CampaignInfo(
                campaign_id=str(c.get("id", "")),
                name=name,
                clicks=0,  # Will be populated by metrics if needed
                conversions=0,
                revenue=0.0,
                cost=0.0,
            )
        )

    activity.logger.info(
        f"Found {len(campaigns)} campaigns for source '{input.source}' "
        f"(created after {cutoff.date()})"
    )

    return GetCampaignsBySourceOutput(
        campaigns=campaigns, total=len(campaigns), source=input.source
    )


@dataclass
class GetCampaignCreativesInput:
    """Input for get_campaign_creatives activity"""

    campaign_id: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@dataclass
class CreativeInfo:
    """Creative/landing information from Keitaro"""

    landing_id: str
    name: str
    url: Optional[str] = None
    clicks: int = 0
    conversions: int = 0


@dataclass
class GetCampaignCreativesOutput:
    """Output from get_campaign_creatives activity"""

    creatives: list[CreativeInfo]
    campaign_id: str
    total: int


@activity.defn
async def get_campaign_creatives(
    input: GetCampaignCreativesInput,
) -> GetCampaignCreativesOutput:
    """
    Get creatives (landings) for a specific campaign from Keitaro.

    Args:
        input: Contains campaign_id and optional date range

    Returns:
        GetCampaignCreativesOutput with list of creatives
    """
    activity.logger.info(f"Fetching creatives for campaign: {input.campaign_id}")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    # Build date range
    range_config = {}
    if input.date_from and input.date_to:
        range_config = {"from": input.date_from, "to": input.date_to, "timezone": "UTC"}
    else:
        range_config = {"interval": "last_30_days"}

    payload = {
        "range": range_config,
        "metrics": ["clicks", "conversions"],
        "dimensions": ["landing_id", "landing"],
        "filters": [
            {
                "name": "campaign_id",
                "operator": "EQUALS",
                "expression": input.campaign_id,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    rows = data.get("rows", [])
    creatives = []

    for row in rows:
        landing_id = row.get("landing_id")
        if not landing_id:
            continue

        creatives.append(
            CreativeInfo(
                landing_id=str(landing_id),
                name=row.get("landing", f"Landing {landing_id}"),
                clicks=safe_int(row.get("clicks", 0)),
                conversions=safe_int(row.get("conversions", 0)),
            )
        )

    activity.logger.info(
        f"Found {len(creatives)} creatives for campaign: {input.campaign_id}"
    )

    return GetCampaignCreativesOutput(
        creatives=creatives, campaign_id=input.campaign_id, total=len(creatives)
    )


@activity.defn
async def get_batch_metrics(input: BatchMetricsInput) -> BatchMetricsOutput:
    """
    Get metrics for multiple trackers in a single API call.

    More efficient than calling get_tracker_metrics for each tracker.
    Uses report/build with dimensions to get all metrics at once.

    Args:
        input: Contains list of tracker_ids and interval

    Returns:
        BatchMetricsOutput with all metrics and any failed IDs
    """
    activity.logger.info(
        f"Fetching batch metrics for {len(input.tracker_ids)} trackers"
    )

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    # Get all metrics with sub_id_1 dimension
    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks", "conversions", "revenue", "cost", "profit_confirmed"],
        "dimensions": ["sub_id_1"],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    # Calculate date based on interval
    if input.interval == "yesterday":
        metrics_date = (datetime.now() - timedelta(days=1)).date().isoformat()
    elif input.interval == "today":
        metrics_date = datetime.now().date().isoformat()
    else:
        metrics_date = datetime.now().date().isoformat()

    # Build lookup from response
    rows = data.get("rows", [])
    metrics_by_tracker = {
        row.get("sub_id_1"): row for row in rows if row.get("sub_id_1")
    }

    # Match with requested tracker IDs
    results = []
    failed_ids = []

    for tracker_id in input.tracker_ids:
        if tracker_id in metrics_by_tracker:
            row = metrics_by_tracker[tracker_id]
            metrics = KeitaroMetrics(
                tracker_id=tracker_id,
                date=metrics_date,
                clicks=safe_int(row.get("clicks", 0)),
                conversions=safe_int(row.get("conversions", 0)),
                revenue=safe_float(row.get("revenue", 0)),
                cost=safe_float(row.get("cost", 0)),
                profit_confirmed=safe_float(row.get("profit_confirmed", 0)),
            )
            results.append(metrics)
        else:
            failed_ids.append(tracker_id)

    activity.logger.info(
        f"Batch metrics: {len(results)} found, {len(failed_ids)} not found"
    )

    return BatchMetricsOutput(metrics=results, failed_ids=failed_ids)
