"""
Staleness Detector Service

Detects system staleness to trigger inspiration injection.
When staleness_score > 0.6, system needs external inspiration.

Metrics:
- diversity_score: unique component values / expected diversity
- win_rate_trend: 7d MA vs 30d MA (negative = declining)
- fatigue_ratio: ideas with high fatigue / total active
- days_since_new_component: days since last new component added
- exploration_success_rate: successful explorations / total

Composite formula (weights sum to 1.0):
staleness_score = 0.25*diversity + 0.25*win_rate_decline +
                  0.20*fatigue + 0.15*days_stale + 0.15*exploration_fail

Issue: Inspiration System
"""

import os
import httpx
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Staleness threshold - above this triggers injection
STALENESS_THRESHOLD = 0.6

# Weights for composite score (must sum to 1.0)
WEIGHT_DIVERSITY = 0.25
WEIGHT_WIN_RATE = 0.25
WEIGHT_FATIGUE = 0.20
WEIGHT_DAYS_STALE = 0.15
WEIGHT_EXPLORATION = 0.15

# Expected diversity per component type
EXPECTED_DIVERSITY_PER_TYPE = 5

# Days threshold for "stale" component pool
DAYS_STALE_THRESHOLD = 14

# Fatigue threshold for counting as "high fatigue"
FATIGUE_THRESHOLD = 0.7


@dataclass
class StalenessMetrics:
    """Staleness metrics for a segment or global"""

    diversity_score: float
    win_rate_trend: float
    fatigue_ratio: float
    days_since_new_component: int
    exploration_success_rate: float
    staleness_score: float
    is_stale: bool

    # Context
    avatar_id: Optional[str] = None
    geo: Optional[str] = None
    vertical: Optional[str] = None


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with schema"""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


async def calculate_diversity_score(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> float:
    """
    Calculate diversity score: unique component values / expected.

    Low diversity = system using same components repeatedly.

    Returns:
        float 0.0-1.0 (higher = more diverse = less stale)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = []
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    filter_str = "&".join(filters) if filters else ""

    async with httpx.AsyncClient() as client:
        # Count distinct component_type + component_value pairs
        url = f"{rest_url}/component_learnings?select=component_type,component_value"
        if filter_str:
            url += f"&{filter_str}"

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Count unique values per type
    types_seen = set()
    values_per_type = {}
    for row in data:
        ct = row["component_type"]
        cv = row["component_value"]
        types_seen.add(ct)
        if ct not in values_per_type:
            values_per_type[ct] = set()
        values_per_type[ct].add(cv)

    if not types_seen:
        return 0.0  # No data = fully stale

    # Calculate diversity: average values per type / expected
    total_values = sum(len(v) for v in values_per_type.values())
    expected = len(types_seen) * EXPECTED_DIVERSITY_PER_TYPE
    diversity = min(1.0, total_values / expected)

    return diversity


async def calculate_win_rate_trend(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> float:
    """
    Calculate win rate trend: 7d MA vs 30d MA.

    Declining win rate = system becoming stale.

    Returns:
        float -1.0 to 1.0 (negative = declining, 0 = stable, positive = improving)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    now = datetime.utcnow()
    date_7d = (now - timedelta(days=7)).isoformat()
    date_30d = (now - timedelta(days=30)).isoformat()

    filters = [f"created_at=gte.{date_30d}"]
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        # Get outcomes from last 30 days
        response = await client.get(
            f"{rest_url}/outcomes?{filter_str}&select=cpa,created_at&limit=500",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        return 0.0  # No data = neutral

    # Split into 7d and 30d
    date_7d_dt = datetime.fromisoformat(
        date_7d.replace("Z", "+00:00").replace("+00:00", "")
    )

    wins_7d = 0
    total_7d = 0
    wins_30d = 0
    total_30d = 0

    target_cpa = 20.0  # Same as learning loop

    for row in data:
        cpa = row.get("cpa")
        created_at = row.get("created_at", "")

        if cpa is None:
            continue

        is_win = float(cpa) < target_cpa
        total_30d += 1
        if is_win:
            wins_30d += 1

        # Check if in 7d window
        try:
            row_date = datetime.fromisoformat(
                created_at.replace("Z", "+00:00").replace("+00:00", "")
            )
            if row_date >= date_7d_dt:
                total_7d += 1
                if is_win:
                    wins_7d += 1
        except (ValueError, TypeError):
            pass

    # Calculate win rates
    wr_7d = wins_7d / max(total_7d, 1)
    wr_30d = wins_30d / max(total_30d, 1)

    # Trend: positive if 7d > 30d, negative otherwise
    # Normalize to -1..1 range
    if wr_30d == 0:
        return 0.0

    trend = (wr_7d - wr_30d) / wr_30d
    return max(-1.0, min(1.0, trend))


async def calculate_fatigue_ratio(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> float:
    """
    Calculate fatigue ratio: ideas with high fatigue / total active.

    High fatigue = audience tired of seeing similar content.

    Returns:
        float 0.0-1.0 (higher = more fatigued = more stale)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = ["status=eq.active"]
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    # geo filter would require join with decomposed_creatives

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/ideas?{filter_str}&select=id,fatigue_state&limit=500",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        return 0.0

    high_fatigue_count = 0
    for row in data:
        fatigue = row.get("fatigue_state")
        if fatigue and isinstance(fatigue, dict):
            # Check if any fatigue dimension is high
            for key, value in fatigue.items():
                if isinstance(value, (int, float)) and value > FATIGUE_THRESHOLD:
                    high_fatigue_count += 1
                    break

    return high_fatigue_count / len(data)


async def calculate_days_since_new_component(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> int:
    """
    Calculate days since last new component was added.

    Long time = no innovation in component pool.

    Returns:
        int days (higher = more stale)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = []
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    filter_str = "&".join(filters) if filters else ""

    async with httpx.AsyncClient() as client:
        url = f"{rest_url}/component_learnings?select=created_at&order=created_at.desc&limit=1"
        if filter_str:
            url += f"&{filter_str}"

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    if not data:
        return DAYS_STALE_THRESHOLD * 2  # No data = very stale

    last_created = data[0].get("created_at")
    if not last_created:
        return DAYS_STALE_THRESHOLD * 2

    try:
        last_dt = datetime.fromisoformat(
            last_created.replace("Z", "+00:00").replace("+00:00", "")
        )
        now = datetime.utcnow()
        delta = now - last_dt.replace(tzinfo=None)
        return delta.days
    except (ValueError, TypeError):
        return DAYS_STALE_THRESHOLD


async def calculate_exploration_success_rate(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> float:
    """
    Calculate exploration success rate: successful explorations / total.

    Low success rate = explorations not finding winners.

    Returns:
        float 0.0-1.0 (higher = more successful = less stale)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    now = datetime.utcnow()
    date_30d = (now - timedelta(days=30)).isoformat()

    filters = [f"created_at=gte.{date_30d}"]
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/exploration_log?{filter_str}&select=was_successful&limit=500",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        return 0.5  # No data = neutral

    total = len(data)
    successful = sum(1 for row in data if row.get("was_successful") is True)

    return successful / total


def compute_staleness_score(metrics: StalenessMetrics) -> float:
    """
    Compute composite staleness score from individual metrics.

    Higher score = more stale = needs inspiration injection.
    """
    # Invert diversity (high diversity = low staleness)
    diversity_staleness = 1.0 - metrics.diversity_score

    # Invert win rate trend (positive trend = low staleness)
    # Map -1..1 to 0..1 where -1 (declining) = 1.0 staleness
    win_rate_staleness = (1.0 - metrics.win_rate_trend) / 2.0

    # Fatigue is already 0..1 where high = stale
    fatigue_staleness = metrics.fatigue_ratio

    # Normalize days to 0..1 (cap at 2x threshold)
    days_staleness = min(
        1.0, metrics.days_since_new_component / (DAYS_STALE_THRESHOLD * 2)
    )

    # Invert exploration success (high success = low staleness)
    exploration_staleness = 1.0 - metrics.exploration_success_rate

    # Weighted average
    score = (
        WEIGHT_DIVERSITY * diversity_staleness
        + WEIGHT_WIN_RATE * win_rate_staleness
        + WEIGHT_FATIGUE * fatigue_staleness
        + WEIGHT_DAYS_STALE * days_staleness
        + WEIGHT_EXPLORATION * exploration_staleness
    )

    return round(score, 4)


async def calculate_staleness_metrics(
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> StalenessMetrics:
    """
    Calculate all staleness metrics for a segment or global.

    Args:
        avatar_id: Optional avatar filter (None = global)
        geo: Optional geo filter
        vertical: Optional vertical filter (for context only)

    Returns:
        StalenessMetrics with all metrics and composite score
    """
    # Calculate individual metrics
    diversity = await calculate_diversity_score(avatar_id, geo)
    win_rate_trend = await calculate_win_rate_trend(avatar_id, geo)
    fatigue = await calculate_fatigue_ratio(avatar_id, geo)
    days_stale = await calculate_days_since_new_component(avatar_id, geo)
    exploration = await calculate_exploration_success_rate(avatar_id, geo)

    # Create metrics object
    metrics = StalenessMetrics(
        diversity_score=round(diversity, 4),
        win_rate_trend=round(win_rate_trend, 4),
        fatigue_ratio=round(fatigue, 4),
        days_since_new_component=days_stale,
        exploration_success_rate=round(exploration, 4),
        staleness_score=0.0,  # Will be computed
        is_stale=False,  # Will be computed
        avatar_id=avatar_id,
        geo=geo,
        vertical=vertical,
    )

    # Compute composite score
    metrics.staleness_score = compute_staleness_score(metrics)
    metrics.is_stale = metrics.staleness_score > STALENESS_THRESHOLD

    return metrics


async def save_staleness_snapshot(
    metrics: StalenessMetrics,
    action_taken: Optional[str] = None,
    action_details: Optional[dict] = None,
) -> dict:
    """
    Save staleness snapshot to database.

    Args:
        metrics: Calculated staleness metrics
        action_taken: Action taken in response (none, cross_transfer, external_injection)
        action_details: Details about the action taken

    Returns:
        Created snapshot record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "diversity_score": metrics.diversity_score,
        "win_rate_trend": metrics.win_rate_trend,
        "fatigue_ratio": metrics.fatigue_ratio,
        "days_since_new_component": metrics.days_since_new_component,
        "exploration_success_rate": metrics.exploration_success_rate,
        "staleness_score": metrics.staleness_score,
        "avatar_id": metrics.avatar_id,
        "geo": metrics.geo,
        "vertical": metrics.vertical,
        "action_taken": action_taken,
        "action_details": action_details,
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/staleness_snapshots", headers=headers, json=payload
        )
        response.raise_for_status()
        return response.json()[0] if response.json() else {}


async def get_latest_staleness(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> Optional[dict]:
    """
    Get latest staleness snapshot for a segment.

    Returns:
        Latest snapshot dict or None
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = []
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")
    if geo:
        filters.append(f"geo=eq.{geo}")
    else:
        filters.append("geo=is.null")

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/staleness_snapshots?{filter_str}&order=created_at.desc&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    return data[0] if data else None


async def check_staleness_and_act(
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> dict:
    """
    Check staleness and determine if action is needed.

    This is the main entry point for MaintenanceWorkflow.

    Returns:
        dict with metrics, is_stale flag, and recommended action
    """
    metrics = await calculate_staleness_metrics(avatar_id, geo, vertical)

    result = {
        "metrics": {
            "diversity_score": metrics.diversity_score,
            "win_rate_trend": metrics.win_rate_trend,
            "fatigue_ratio": metrics.fatigue_ratio,
            "days_since_new_component": metrics.days_since_new_component,
            "exploration_success_rate": metrics.exploration_success_rate,
            "staleness_score": metrics.staleness_score,
        },
        "is_stale": metrics.is_stale,
        "recommended_action": None,
        "avatar_id": avatar_id,
        "geo": geo,
    }

    if metrics.is_stale:
        # Determine recommended action
        # Priority: cross_transfer (cheaper) > external_injection
        result["recommended_action"] = "cross_transfer"

    # Save snapshot
    snapshot = await save_staleness_snapshot(
        metrics,
        action_taken="none",  # Action will be updated after actual injection
    )
    result["snapshot_id"] = snapshot.get("id")

    return result
