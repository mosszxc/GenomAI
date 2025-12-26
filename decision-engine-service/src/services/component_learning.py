"""
Component Learning Service

Extracts components from decomposed_creatives and updates component_learnings
based on outcome results (win/loss).

Issue: #122
"""

import os
import httpx
from typing import Optional
from dataclasses import dataclass

from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Components to track from decomposed_creative payload
TRACKABLE_COMPONENTS = [
    "angle_type",
    "hook_mechanism",
    "proof_type",
    "source_type",
    "emotion_primary",
    "message_structure",
    "opening_type",
    "promise_type",
    "core_belief",
    "context_frame",
    "horizon",
    "risk_level",
]

# Win thresholds per issue #122
WIN_THRESHOLD_LOW_SPEND = {"max_spend": 50, "max_cpa": 4}
WIN_THRESHOLD_HIGH_SPEND = {"min_spend": 50, "max_cpa": 5}


@dataclass
class ComponentUpdate:
    """Single component learning update"""
    component_type: str
    component_value: str
    geo: Optional[str]
    avatar_id: Optional[str]
    was_win: bool
    spend: float
    revenue: float


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
        "Content-Type": "application/json"
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


def is_win(cpa: float, spend: float) -> bool:
    """
    Determine if outcome is a win based on CPA and spend.

    Win conditions (from issue #122):
    - Low spend (<50): CPA < 4
    - High spend (>=50): CPA < 5
    """
    if spend < WIN_THRESHOLD_LOW_SPEND["max_spend"]:
        return cpa < WIN_THRESHOLD_LOW_SPEND["max_cpa"]
    else:
        return cpa < WIN_THRESHOLD_HIGH_SPEND["max_cpa"]


def extract_components(payload: dict) -> list[tuple[str, str]]:
    """
    Extract trackable components from decomposed_creative payload.

    Returns list of (component_type, component_value) tuples.
    """
    components = []

    for component_type in TRACKABLE_COMPONENTS:
        value = payload.get(component_type)
        if value and isinstance(value, str) and value.strip():
            components.append((component_type, value.strip()))

    return components


async def get_decomposed_creative(creative_id: str) -> Optional[dict]:
    """Fetch decomposed_creative payload for a creative_id"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?creative_id=eq.{creative_id}"
            f"&select=payload,idea_id",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data:
            return data[0]
        return None


async def get_idea_avatar(idea_id: str) -> Optional[str]:
    """Get avatar_id for an idea"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/ideas"
            f"?id=eq.{idea_id}"
            f"&select=avatar_id",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and data[0].get('avatar_id'):
            return data[0]['avatar_id']
        return None


async def get_creative_geo(creative_id: str) -> Optional[str]:
    """Get geo for a creative via creatives -> buyer -> geos"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    try:
        async with httpx.AsyncClient() as client:
            # Get buyer_id from creative
            response = await client.get(
                f"{rest_url}/creatives"
                f"?id=eq.{creative_id}"
                f"&select=buyer_id",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if not data or not data[0].get('buyer_id'):
                return None

            buyer_id = data[0]['buyer_id']

            # Get geos from buyer
            response = await client.get(
                f"{rest_url}/buyers"
                f"?id=eq.{buyer_id}"
                f"&select=geos",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if data and data[0].get('geos'):
                # Return first geo if multiple
                geos = data[0]['geos']
                return geos[0] if geos else None
            return None
    except Exception:
        # Geo is optional, don't fail if unavailable
        return None


async def upsert_component_learning(
    component_type: str,
    component_value: str,
    geo: Optional[str],
    avatar_id: Optional[str],
    was_win: bool,
    spend: float,
    revenue: float
) -> dict:
    """
    Upsert component learning record.

    Updates sample_size, win_count/loss_count, totals, and recalculates metrics.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Build filter for existing record
    filters = [
        f"component_type=eq.{component_type}",
        f"component_value=eq.{component_value}",
    ]
    if geo:
        filters.append(f"geo=eq.{geo}")
    else:
        filters.append("geo=is.null")
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        # Check if record exists
        response = await client.get(
            f"{rest_url}/component_learnings?{filter_str}",
            headers=_get_headers(supabase_key)
        )
        response.raise_for_status()
        existing = response.json()

        if existing:
            # Update existing record
            record = existing[0]
            new_sample = (record.get('sample_size') or 0) + 1
            new_wins = (record.get('win_count') or 0) + (1 if was_win else 0)
            new_losses = (record.get('loss_count') or 0) + (0 if was_win else 1)
            new_spend = float(record.get('total_spend') or 0) + spend
            new_revenue = float(record.get('total_revenue') or 0) + revenue

            # win_rate and avg_roi are generated columns, don't update them
            response = await client.patch(
                f"{rest_url}/component_learnings?id=eq.{record['id']}",
                headers=headers,
                json={
                    "sample_size": new_sample,
                    "win_count": new_wins,
                    "loss_count": new_losses,
                    "total_spend": new_spend,
                    "total_revenue": new_revenue,
                    "updated_at": "now()"
                }
            )
            response.raise_for_status()
            return response.json()[0] if response.json() else {}
        else:
            # Insert new record (win_rate and avg_roi are generated columns)
            response = await client.post(
                f"{rest_url}/component_learnings",
                headers=headers,
                json={
                    "component_type": component_type,
                    "component_value": component_value,
                    "geo": geo,
                    "avatar_id": avatar_id,
                    "sample_size": 1,
                    "win_count": 1 if was_win else 0,
                    "loss_count": 0 if was_win else 1,
                    "total_spend": spend,
                    "total_revenue": revenue
                }
            )
            response.raise_for_status()
            return response.json()[0] if response.json() else {}


async def process_component_learnings(
    creative_id: str,
    cpa: float,
    spend: float,
    revenue: float
) -> dict:
    """
    Main entry point: process component learnings for an outcome.

    1. Load decomposed_creative for creative
    2. Extract components from payload
    3. Get geo and avatar_id
    4. Update component_learnings for each component (global + per-avatar)

    Returns summary of updates.
    """
    result = {
        "creative_id": creative_id,
        "components_updated": 0,
        "global_updates": 0,
        "avatar_updates": 0,
        "errors": []
    }

    # Get decomposed creative
    dc = await get_decomposed_creative(creative_id)
    if not dc or not dc.get('payload'):
        result["errors"].append(f"No decomposed_creative found for {creative_id}")
        return result

    payload = dc['payload']
    idea_id = dc.get('idea_id')

    # Extract components
    components = extract_components(payload)
    if not components:
        result["errors"].append("No trackable components found in payload")
        return result

    # Get context
    geo = await get_creative_geo(creative_id)
    avatar_id = await get_idea_avatar(idea_id) if idea_id else None

    # Determine win/loss
    was_win = is_win(cpa, spend)

    # Update for each component
    for component_type, component_value in components:
        try:
            # Global update (avatar_id = NULL)
            await upsert_component_learning(
                component_type=component_type,
                component_value=component_value,
                geo=geo,
                avatar_id=None,
                was_win=was_win,
                spend=spend,
                revenue=revenue
            )
            result["global_updates"] += 1
            result["components_updated"] += 1

            # Per-avatar update (if avatar known)
            if avatar_id:
                await upsert_component_learning(
                    component_type=component_type,
                    component_value=component_value,
                    geo=geo,
                    avatar_id=avatar_id,
                    was_win=was_win,
                    spend=spend,
                    revenue=revenue
                )
                result["avatar_updates"] += 1
                result["components_updated"] += 1

        except Exception as e:
            result["errors"].append(f"Error updating {component_type}={component_value}: {str(e)}")

    return result
