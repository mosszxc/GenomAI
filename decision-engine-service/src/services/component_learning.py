"""
Component Learning Service

Extracts components from decomposed_creatives and updates component_learnings
based on outcome results (win/loss).

Issue: #122
"""

import os
from src.core.http_client import get_http_client
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
        "Content-Type": "application/json",
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

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/decomposed_creatives"
        f"?creative_id=eq.{creative_id}"
        f"&select=payload,idea_id",
        headers=headers,
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

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/ideas?id=eq.{idea_id}&select=avatar_id", headers=headers
    )
    response.raise_for_status()
    data = response.json()

    if data and data[0].get("avatar_id"):
        return data[0]["avatar_id"]
    return None


async def get_creative_geo(creative_id: str) -> Optional[str]:
    """Get geo for a creative via creatives -> buyer -> geos"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    try:
        client = get_http_client()
        # Get buyer_id from creative
        response = await client.get(
            f"{rest_url}/creatives?id=eq.{creative_id}&select=buyer_id",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if not data or not data[0].get("buyer_id"):
            return None

        buyer_id = data[0]["buyer_id"]

        # Get geos from buyer
        response = await client.get(
            f"{rest_url}/buyers?id=eq.{buyer_id}&select=geos", headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and data[0].get("geos"):
            # Return first geo if multiple
            geos = data[0]["geos"]
            return geos[0] if geos else None
        return None
    except Exception:
        # Geo is optional, don't fail if unavailable
        return None


def _build_component_key(
    component_type: str,
    component_value: str,
    geo: Optional[str],
    avatar_id: Optional[str],
) -> str:
    """Build unique key for component lookup."""
    return f"{component_type}|{component_value}|{geo or ''}|{avatar_id or ''}"


async def batch_upsert_component_learnings(
    updates: list[ComponentUpdate],
) -> dict:
    """
    Batch upsert multiple component learning records (O(1) instead of O(n)).

    Issue #577: Replaces N individual upserts with batch operations.

    Args:
        updates: List of ComponentUpdate objects to process

    Returns:
        Dict with counts of inserts and updates
    """
    if not updates:
        return {"inserted": 0, "updated": 0}

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)
    client = get_http_client()

    # Build unique keys for all updates
    update_keys = {}
    for u in updates:
        key = _build_component_key(
            u.component_type, u.component_value, u.geo, u.avatar_id
        )
        if key not in update_keys:
            update_keys[key] = u
        else:
            # Merge duplicates (same component in same batch)
            existing = update_keys[key]
            update_keys[key] = ComponentUpdate(
                component_type=existing.component_type,
                component_value=existing.component_value,
                geo=existing.geo,
                avatar_id=existing.avatar_id,
                was_win=existing.was_win or u.was_win,  # Count as win if any was win
                spend=existing.spend + u.spend,
                revenue=existing.revenue + u.revenue,
            )

    # Extract unique component_type/component_value pairs for batch lookup
    type_value_pairs = list(
        {(u.component_type, u.component_value) for u in update_keys.values()}
    )

    # Batch fetch existing records (O(1) query)
    # Use OR conditions for type/value pairs
    or_conditions = []
    for comp_type, comp_value in type_value_pairs:
        or_conditions.append(
            f"and(component_type.eq.{comp_type},component_value.eq.{comp_value})"
        )

    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?or=({','.join(or_conditions)})"
        "&select=id,component_type,component_value,geo,avatar_id,"
        "sample_size,win_count,loss_count,total_spend,total_revenue",
        headers=_get_headers(supabase_key),
    )
    response.raise_for_status()
    existing_records = response.json()

    # Build lookup map for existing records
    existing_map = {}
    for rec in existing_records:
        key = _build_component_key(
            rec["component_type"],
            rec["component_value"],
            rec.get("geo"),
            rec.get("avatar_id"),
        )
        existing_map[key] = rec

    # Separate into inserts and updates
    to_insert = []
    updates_by_id = {}

    for key, update in update_keys.items():
        if key in existing_map:
            # Prepare update
            rec = existing_map[key]
            updates_by_id[rec["id"]] = {
                "sample_size": (rec.get("sample_size") or 0) + 1,
                "win_count": (rec.get("win_count") or 0) + (1 if update.was_win else 0),
                "loss_count": (rec.get("loss_count") or 0)
                + (0 if update.was_win else 1),
                "total_spend": float(rec.get("total_spend") or 0) + update.spend,
                "total_revenue": float(rec.get("total_revenue") or 0) + update.revenue,
                "updated_at": "now()",
            }
        else:
            # Prepare insert
            to_insert.append(
                {
                    "component_type": update.component_type,
                    "component_value": update.component_value,
                    "geo": update.geo,
                    "avatar_id": update.avatar_id,
                    "sample_size": 1,
                    "win_count": 1 if update.was_win else 0,
                    "loss_count": 0 if update.was_win else 1,
                    "total_spend": update.spend,
                    "total_revenue": update.revenue,
                }
            )

    result = {"inserted": 0, "updated": 0}

    # Batch insert new records (single POST with array)
    if to_insert:
        response = await client.post(
            f"{rest_url}/component_learnings",
            headers=headers,
            json=to_insert,
        )
        response.raise_for_status()
        result["inserted"] = len(to_insert)

    # Batch update existing records
    # PostgREST doesn't support different values per row in single PATCH,
    # so we need individual PATCHes, but we can parallelize with asyncio.gather
    if updates_by_id:
        import asyncio

        async def update_one(record_id: str, data: dict):
            resp = await client.patch(
                f"{rest_url}/component_learnings?id=eq.{record_id}",
                headers=headers,
                json=data,
            )
            resp.raise_for_status()

        await asyncio.gather(
            *[update_one(rid, data) for rid, data in updates_by_id.items()]
        )
        result["updated"] = len(updates_by_id)

    return result


async def process_component_learnings(
    creative_id: str, cpa: float, spend: float, revenue: float
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
        "errors": [],
    }

    # Get decomposed creative
    dc = await get_decomposed_creative(creative_id)
    if not dc or not dc.get("payload"):
        result["errors"].append(f"No decomposed_creative found for {creative_id}")
        return result

    payload = dc["payload"]
    idea_id = dc.get("idea_id")

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

    # Build batch updates (O(1) instead of O(n*2) - Issue #577)
    updates = []
    for component_type, component_value in components:
        # Global update (avatar_id = NULL)
        updates.append(
            ComponentUpdate(
                component_type=component_type,
                component_value=component_value,
                geo=geo,
                avatar_id=None,
                was_win=was_win,
                spend=spend,
                revenue=revenue,
            )
        )

        # Per-avatar update (if avatar known)
        if avatar_id:
            updates.append(
                ComponentUpdate(
                    component_type=component_type,
                    component_value=component_value,
                    geo=geo,
                    avatar_id=avatar_id,
                    was_win=was_win,
                    spend=spend,
                    revenue=revenue,
                )
            )

    try:
        batch_result = await batch_upsert_component_learnings(updates)
        result["global_updates"] = len(components)
        result["avatar_updates"] = len(components) if avatar_id else 0
        result["components_updated"] = (
            batch_result["inserted"] + batch_result["updated"]
        )
    except Exception as e:
        result["errors"].append(f"Batch update error: {str(e)}")

    return result
