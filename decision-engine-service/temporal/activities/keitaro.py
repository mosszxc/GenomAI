"""
Keitaro API Activities

Activities for fetching metrics from Keitaro tracker.
Uses POST /admin_api/v1/report/build endpoint.

Based on docs/layer-4-implementation-planning/KEITARO_API_DATA_CLASSIFICATION.md
"""

from src.core.http_client import get_http_client
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from temporal.config import settings
from src.utils.parsing import safe_int, safe_float


# HTTP status codes that indicate temporary errors (should retry)
_TEMPORARY_ERROR_CODES = {502, 503, 504, 429}


def _handle_http_response(response: httpx.Response, context: str = "Keitaro API") -> None:
    """
    Handle HTTP response with proper error classification for Temporal retry.

    Args:
        response: The HTTP response to check
        context: Description for error messages

    Raises:
        ApplicationError: With non_retryable=False for temporary errors (will retry)
        ApplicationError: With non_retryable=True for permanent errors (won't retry)
    """
    if response.is_success:
        return

    status_code = response.status_code
    error_body = response.text[:500] if response.text else "No response body"

    if status_code in _TEMPORARY_ERROR_CODES:
        # Temporary error - Temporal should retry
        activity.logger.warning(
            f"{context} temporary error: status={status_code}, body={error_body}"
        )
        raise ApplicationError(
            f"{context} temporarily unavailable: HTTP {status_code}",
            non_retryable=False,
        )
    else:
        # Permanent error - no point in retrying
        activity.logger.error(f"{context} permanent error: status={status_code}, body={error_body}")
        raise ApplicationError(
            f"{context} error: HTTP {status_code} - {error_body}",
            non_retryable=True,
        )


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

    Uses report/build with dimensions: ["campaign_id"] to get unique tracker IDs.
    Issue #705: Changed from sub_id_1 to campaign_id to match creatives.tracker_id.

    Args:
        input: Contains interval (yesterday, today, etc.)

    Returns:
        GetAllTrackersOutput with list of tracker_ids (campaign_id values)
    """
    activity.logger.info(f"Fetching all trackers for interval: {input.interval}")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks"],
        "dimensions": ["campaign_id"],
    }

    client = get_http_client()
    response = await client.post(url, headers=headers, json=payload, timeout=60.0)
    _handle_http_response(response, "Keitaro API")
    data = response.json()

    rows = data.get("rows", [])
    # Issue #705: Use campaign_id instead of sub_id_1
    tracker_ids = [str(row.get("campaign_id")) for row in rows if row.get("campaign_id")]

    activity.logger.info(f"Found {len(tracker_ids)} trackers (campaign_ids)")

    return GetAllTrackersOutput(tracker_ids=tracker_ids, total=len(tracker_ids))


@activity.defn
async def get_tracker_metrics(input: GetTrackerMetricsInput) -> GetTrackerMetricsOutput:
    """
    Get metrics for a specific tracker from Keitaro.

    Uses report/build with filter on campaign_id.
    Issue #705: Changed from sub_id_1 to campaign_id to match creatives.tracker_id.

    Args:
        input: Contains tracker_id (campaign_id) and interval

    Returns:
        GetTrackerMetricsOutput with metrics or not found
    """
    activity.logger.info(f"Fetching metrics for tracker: {input.tracker_id}")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    # Issue #705: Filter by campaign_id instead of sub_id_1
    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks", "conversions", "revenue", "cost", "profit_confirmed"],
        "filters": [{"name": "campaign_id", "operator": "EQUALS", "expression": input.tracker_id}],
    }

    client = get_http_client()
    response = await client.post(url, headers=headers, json=payload, timeout=30.0)
    _handle_http_response(response, "Keitaro API")
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
    created_at: Optional[str] = None

    @property
    def profit(self) -> float:
        """Calculate profit (revenue - cost)"""
        return self.revenue - self.cost

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue": self.revenue,
            "cost": self.cost,
            "profit": self.profit,
            "created_at": self.created_at,
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

    client = get_http_client()
    response = await client.get(url, headers=headers, timeout=120.0)
    _handle_http_response(response, "Keitaro API")
    all_campaigns = response.json()

    # Step 2: Calculate date cutoff (last 30 days by default)
    if input.date_from:
        try:
            cutoff = datetime.fromisoformat(input.date_from)
        except ValueError:
            raise ApplicationError(
                f"Invalid date format: {input.date_from}", non_retryable=True
            ) from None
    else:
        cutoff = datetime.utcnow() - timedelta(days=30)

    # Step 3: Filter campaigns by name and creation date
    source_upper = input.source.upper()
    campaigns = []

    for c in all_campaigns:
        name = c.get("name", "")
        created_at = c.get("created_at", "")
        name_upper = name.upper()

        # Filter by source in name (case-insensitive)
        if source_upper not in name_upper:
            continue

        # Exclude COIN campaigns (different workflow)
        if "COIN" in name_upper:
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
                clicks=0,
                conversions=0,
                revenue=0.0,
                cost=0.0,
                created_at=created_at,
            )
        )

    if not campaigns:
        return GetCampaignsBySourceOutput(campaigns=[], total=0, source=input.source)

    # Step 4: Fetch metrics for all campaigns in one request
    activity.logger.info(f"Fetching metrics for {len(campaigns)} campaigns...")

    campaign_ids = [c.campaign_id for c in campaigns]
    metrics_url = _get_keitaro_url("/report/build")

    # Get metrics for last 30 days grouped by campaign_id
    # Keitaro API format: https://admin-api.docs.keitaro.io/
    # Uses: dimensions (grouping), measures (metrics), range (from/to dates)
    today = datetime.utcnow().date()
    date_from = (today - timedelta(days=30)).isoformat()
    date_to = today.isoformat()

    metrics_payload = {
        "range": {"from": date_from, "to": date_to, "timezone": "UTC"},
        "dimensions": ["campaign_id"],
        "measures": ["clicks", "sales", "confirmed_revenue", "cost", "confirmed_profit"],
    }

    try:
        activity.logger.info(
            f"Requesting metrics for {len(campaign_ids)} campaigns: {campaign_ids[:5]}..."
        )
        metrics_response = await client.post(
            metrics_url, headers=headers, json=metrics_payload, timeout=120.0
        )
        activity.logger.info(f"Metrics response status: {metrics_response.status_code}")
        if metrics_response.is_success:
            metrics_data = metrics_response.json()
            activity.logger.info(f"Metrics response keys: {list(metrics_data.keys())}")
            metrics_rows = metrics_data.get("rows", [])
            activity.logger.info(f"Got {len(metrics_rows)} rows from Keitaro")
            if metrics_rows:
                activity.logger.info(f"First row sample: {metrics_rows[0]}")

            # Build lookup dict by campaign_id
            metrics_by_id: dict[str, dict[str, int | float]] = {}
            for row in metrics_rows:
                cid = str(row.get("campaign_id", ""))
                if cid:
                    metrics_by_id[cid] = {
                        "clicks": safe_int(row.get("clicks", 0)),
                        "conversions": safe_int(row.get("sales", 0)),  # Keitaro uses "sales"
                        "revenue": safe_float(row.get("confirmed_revenue", 0.0)),
                        "cost": safe_float(row.get("cost", 0.0)),
                    }

            # Merge metrics into campaigns
            for camp in campaigns:
                if camp.campaign_id in metrics_by_id:
                    m = metrics_by_id[camp.campaign_id]
                    camp.clicks = int(m["clicks"])
                    camp.conversions = int(m["conversions"])
                    camp.revenue = float(m["revenue"])
                    camp.cost = float(m["cost"])

            activity.logger.info(f"Merged metrics for {len(metrics_by_id)} campaigns")
        else:
            activity.logger.warning(f"Failed to fetch metrics: {metrics_response.status_code}")
    except Exception as e:
        activity.logger.warning(f"Error fetching metrics (continuing without): {e}")

    # Step 5: Select top campaigns
    # - Top 10 by profit (revenue - cost)
    # - Last 20 by creation date
    total_before_filter = len(campaigns)

    # Top 10 by profit
    top_by_profit = sorted(campaigns, key=lambda c: c.profit, reverse=True)[:10]
    top_profit_ids = {c.campaign_id for c in top_by_profit}

    # Last 20 by creation date (most recent first)
    sorted_by_date = sorted(
        campaigns,
        key=lambda c: c.created_at or "",
        reverse=True,
    )[:20]

    # Combine without duplicates (profit campaigns first, then recent ones)
    selected: list[CampaignInfo] = list(top_by_profit)
    for camp in sorted_by_date:
        if camp.campaign_id not in top_profit_ids:
            selected.append(camp)

    activity.logger.info(
        f"Found {total_before_filter} campaigns for source '{input.source}' "
        f"(created after {cutoff.date()}), selected {len(selected)} "
        f"(top 10 profit + last 20 recent)"
    )

    return GetCampaignsBySourceOutput(campaigns=selected, total=len(selected), source=input.source)


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

    client = get_http_client()
    response = await client.post(url, headers=headers, json=payload, timeout=60.0)
    _handle_http_response(response, "Keitaro API")
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

    activity.logger.info(f"Found {len(creatives)} creatives for campaign: {input.campaign_id}")

    return GetCampaignCreativesOutput(
        creatives=creatives, campaign_id=input.campaign_id, total=len(creatives)
    )


@activity.defn
async def get_batch_metrics(input: BatchMetricsInput) -> BatchMetricsOutput:
    """
    Get metrics for multiple trackers in a single API call.

    More efficient than calling get_tracker_metrics for each tracker.
    Uses report/build with dimensions to get all metrics at once.
    Issue #705: Changed from sub_id_1 to campaign_id to match creatives.tracker_id.

    Args:
        input: Contains list of tracker_ids (campaign_ids) and interval

    Returns:
        BatchMetricsOutput with all metrics and any failed IDs
    """
    activity.logger.info(f"Fetching batch metrics for {len(input.tracker_ids)} trackers")

    url = _get_keitaro_url("/report/build")
    headers = _get_keitaro_headers()

    # Issue #705: Get all metrics with campaign_id dimension (not sub_id_1)
    payload = {
        "range": {"interval": input.interval},
        "metrics": ["clicks", "conversions", "revenue", "cost", "profit_confirmed"],
        "dimensions": ["campaign_id"],
    }

    client = get_http_client()
    response = await client.post(url, headers=headers, json=payload, timeout=120.0)
    _handle_http_response(response, "Keitaro API")
    data = response.json()

    # Calculate date based on interval
    if input.interval == "yesterday":
        metrics_date = (datetime.now() - timedelta(days=1)).date().isoformat()
    elif input.interval == "today":
        metrics_date = datetime.now().date().isoformat()
    else:
        metrics_date = datetime.now().date().isoformat()

    # Build lookup from response - Issue #705: use campaign_id
    rows = data.get("rows", [])
    metrics_by_tracker = {
        str(row.get("campaign_id")): row for row in rows if row.get("campaign_id")
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

    activity.logger.info(f"Batch metrics: {len(results)} found, {len(failed_ids)} not found")

    return BatchMetricsOutput(metrics=results, failed_ids=failed_ids)
