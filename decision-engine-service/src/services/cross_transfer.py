"""
Cross-Segment Transfer Service

Transfers successful components from one segment (avatar/geo) to another.
Part of Inspiration System to prevent creative degradation.

When a component has high win_rate in segment A, inject it into segment B
with sample_size=0 so Thompson Sampling will naturally explore it.

Issue: Inspiration System
"""

import os
from src.core.http_client import get_http_client
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Minimum win rate for transfer candidate
MIN_WIN_RATE_FOR_TRANSFER = 0.6

# Minimum sample size to trust the source data
MIN_SAMPLE_SIZE_FOR_TRANSFER = 30

# Maximum sample size in target segment to consider for transfer
# (if target already has data, don't overwrite)
MAX_TARGET_SAMPLE_SIZE = 10

# Discount factor for transfer confidence (30% haircut)
TRANSFER_CONFIDENCE_DISCOUNT = 0.7


@dataclass
class TransferCandidate:
    """Candidate component for cross-segment transfer"""

    component_type: str
    component_value: str
    source_win_rate: float
    source_sample_size: int
    source_avatar_id: Optional[str]
    source_geo: Optional[str]
    target_avatar_id: Optional[str]
    target_geo: Optional[str]
    transfer_confidence: float


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


async def find_transfer_candidates(
    target_avatar_id: Optional[str] = None,
    target_geo: Optional[str] = None,
    limit: int = 5,
) -> List[TransferCandidate]:
    """
    Find components from OTHER segments that could be transferred to target segment.

    Algorithm:
    1. Find components with high win_rate in other segments
    2. Check if they exist in target segment
    3. If not (or low sample), they are candidates

    Args:
        target_avatar_id: Target avatar (None = global)
        target_geo: Target geo
        limit: Maximum candidates to return

    Returns:
        List of TransferCandidate sorted by transfer_confidence
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build filter to EXCLUDE target segment
    exclude_filters = []
    if target_avatar_id:
        exclude_filters.append(f"avatar_id=neq.{target_avatar_id}")
    else:
        exclude_filters.append("avatar_id=not.is.null")  # Exclude global if target is global

    if target_geo:
        exclude_filters.append(f"geo=neq.{target_geo}")

    # Filter for high performers
    filters = [
        f"win_rate=gte.{MIN_WIN_RATE_FOR_TRANSFER}",
        f"sample_size=gte.{MIN_SAMPLE_SIZE_FOR_TRANSFER}",
        *exclude_filters,
    ]
    filter_str = "&".join(filters)

    client = get_http_client()
    # Get high performing components from other segments
    response = await client.get(
        f"{rest_url}/component_learnings?"
        f"{filter_str}"
        f"&select=id,component_type,component_value,win_rate,sample_size,avatar_id,geo"
        f"&order=win_rate.desc"
        f"&limit=50",  # Get more than needed for filtering
        headers=headers,
    )
    response.raise_for_status()
    source_components = response.json()

    if not source_components:
        return []

    # Check which ones are missing or low-sample in target segment
    candidates = []

    client = get_http_client()
    for comp in source_components:
        # Build filter for target segment
        target_filters = [
            f"component_type=eq.{comp['component_type']}",
            f"component_value=eq.{comp['component_value']}",
        ]
        if target_avatar_id:
            target_filters.append(f"avatar_id=eq.{target_avatar_id}")
        else:
            target_filters.append("avatar_id=is.null")
        if target_geo:
            target_filters.append(f"geo=eq.{target_geo}")

        target_filter_str = "&".join(target_filters)

        # Check if exists in target
        response = await client.get(
            f"{rest_url}/component_learnings?{target_filter_str}&select=id,sample_size",
            headers=headers,
        )
        response.raise_for_status()
        target_data = response.json()

        # Skip if target already has sufficient data
        if target_data and target_data[0].get("sample_size", 0) >= MAX_TARGET_SAMPLE_SIZE:
            continue

        # This is a candidate!
        source_win_rate = float(comp["win_rate"] or 0)
        candidates.append(
            TransferCandidate(
                component_type=comp["component_type"],
                component_value=comp["component_value"],
                source_win_rate=source_win_rate,
                source_sample_size=comp["sample_size"],
                source_avatar_id=comp.get("avatar_id"),
                source_geo=comp.get("geo"),
                target_avatar_id=target_avatar_id,
                target_geo=target_geo,
                transfer_confidence=source_win_rate * TRANSFER_CONFIDENCE_DISCOUNT,
            )
        )

        if len(candidates) >= limit:
            break

    # Sort by transfer confidence
    candidates.sort(key=lambda c: c.transfer_confidence, reverse=True)

    return candidates[:limit]


async def inject_component(
    component_type: str,
    component_value: str,
    target_avatar_id: Optional[str],
    target_geo: Optional[str],
    origin_type: str,
    origin_segment: Optional[dict] = None,
    origin_source_id: Optional[str] = None,
) -> dict:
    """
    Inject a new component into component_learnings with sample_size=0.

    Thompson Sampling will naturally explore it due to high uncertainty.

    Args:
        component_type: Type of component (e.g., 'hook_mechanism')
        component_value: Value of component
        target_avatar_id: Target avatar (None = global)
        target_geo: Target geo
        origin_type: 'cross_transfer' or 'external_injection'
        origin_segment: Source segment info for cross_transfer
        origin_source_id: Reference to external_inspirations.id

    Returns:
        Created component_learning record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "component_type": component_type,
        "component_value": component_value,
        "avatar_id": target_avatar_id,
        "geo": target_geo,
        "sample_size": 0,
        "win_count": 0,
        "loss_count": 0,
        "total_spend": 0,
        "total_revenue": 0,
        "origin_type": origin_type,
        "origin_segment": origin_segment,
        "origin_source_id": origin_source_id,
        "injected_at": datetime.utcnow().isoformat(),
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/component_learnings",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return data[0] if data else {}


async def execute_cross_transfer(candidate: TransferCandidate) -> dict:
    """
    Execute cross-segment transfer for a single candidate.

    Args:
        candidate: TransferCandidate to inject

    Returns:
        Created component_learning record
    """
    origin_segment = {
        "avatar_id": candidate.source_avatar_id,
        "geo": candidate.source_geo,
        "win_rate": candidate.source_win_rate,
        "sample_size": candidate.source_sample_size,
    }

    return await inject_component(
        component_type=candidate.component_type,
        component_value=candidate.component_value,
        target_avatar_id=candidate.target_avatar_id,
        target_geo=candidate.target_geo,
        origin_type="cross_transfer",
        origin_segment=origin_segment,
    )


async def execute_bulk_cross_transfer(
    candidates: List[TransferCandidate],
) -> List[dict]:
    """
    Execute cross-segment transfer for multiple candidates.

    Args:
        candidates: List of TransferCandidate to inject

    Returns:
        List of created component_learning records
    """
    results = []
    for candidate in candidates:
        try:
            result = await execute_cross_transfer(candidate)
            results.append(result)
        except Exception as e:
            # Log but continue with other candidates
            results.append({"error": str(e), "candidate": candidate.component_value})

    return results


async def get_transfer_stats() -> dict:
    """
    Get statistics about cross-segment transfers.

    Returns:
        dict with transfer counts and success rates
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Count total cross-transfers
    response = await client.get(
        f"{rest_url}/component_learnings?origin_type=eq.cross_transfer&select=id",
        headers={**headers, "Prefer": "count=exact"},
    )
    total_transfers = int(response.headers.get("content-range", "*/0").split("/")[-1])

    # Get transfers with outcomes
    response = await client.get(
        f"{rest_url}/component_learnings?"
        "origin_type=eq.cross_transfer"
        "&sample_size=gt.0"
        "&select=id,win_rate,sample_size",
        headers=headers,
    )
    response.raise_for_status()
    tested = response.json()

    # Calculate success rate
    tested_count = len(tested)
    if tested_count > 0:
        avg_win_rate = sum(float(t["win_rate"] or 0) for t in tested) / tested_count
        successful = sum(1 for t in tested if float(t.get("win_rate") or 0) >= 0.5)
        success_rate = successful / tested_count
    else:
        avg_win_rate = 0
        success_rate = 0

    return {
        "total_transfers": total_transfers,
        "tested_count": tested_count,
        "avg_win_rate": round(avg_win_rate, 4),
        "success_rate": round(success_rate, 4),
        "pending_count": total_transfers - tested_count,
    }
