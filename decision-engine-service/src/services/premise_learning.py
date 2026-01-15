"""
Premise Learning Service

Updates premise_learnings based on hypothesis outcomes.
Called by Learning Loop when outcome has premise_id.

Issue: #167
Pattern: component_learning.py
"""

import os
from src.core.http_client import get_http_client
from typing import Any, Optional, cast
from dataclasses import dataclass

from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Win thresholds (same as component_learning)
WIN_THRESHOLD_LOW_SPEND = {"max_spend": 50, "max_cpa": 4}
WIN_THRESHOLD_HIGH_SPEND = {"min_spend": 50, "max_cpa": 5}


@dataclass
class PremiseLearningResult:
    """Result of premise learning update"""

    premise_id: str
    premise_type: str
    geo: Optional[str]
    avatar_id: Optional[str]
    was_win: bool
    updated: bool
    error: Optional[str] = None


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


async def get_hypothesis_premise(hypothesis_id: str) -> Optional[dict]:
    """
    Get premise info for a hypothesis.

    Returns dict with premise_id, premise_type if hypothesis has premise.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Get hypothesis with premise
    response = await client.get(
        f"{rest_url}/hypotheses?id=eq.{hypothesis_id}&select=premise_id,premises(id,premise_type)",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data and data[0].get("premise_id"):
        hypothesis = data[0]
        premise = hypothesis.get("premises", {})
        return {
            "premise_id": hypothesis["premise_id"],
            "premise_type": premise.get("premise_type") if premise else None,
        }
    return None


async def get_hypothesis_for_creative(creative_id: str) -> Optional[dict]:
    """
    Get hypothesis info for a creative.

    Returns dict with hypothesis_id, premise_id if creative has hypothesis.

    Lookup order:
    1. creatives.hypothesis_id (direct link)
    2. creatives.idea_id → hypotheses.idea_id (via idea)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Get creative -> hypothesis_id and idea_id
    response = await client.get(
        f"{rest_url}/creatives?id=eq.{creative_id}&select=hypothesis_id,idea_id",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        return None

    creative = data[0]
    hypothesis_id = creative.get("hypothesis_id")
    idea_id = creative.get("idea_id")

    # Path 1: Direct hypothesis_id link
    if hypothesis_id:
        response = await client.get(
            f"{rest_url}/hypotheses?id=eq.{hypothesis_id}&select=id,premise_id",
            headers=headers,
        )
        response.raise_for_status()
        hypothesis_data = cast(list[dict[str, Any]], response.json())
        if hypothesis_data:
            return hypothesis_data[0]

    # Path 2: Via idea_id → hypotheses.idea_id
    if idea_id:
        response = await client.get(
            f"{rest_url}/hypotheses?idea_id=eq.{idea_id}&select=id,premise_id&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        hypothesis_data = cast(list[dict[str, Any]], response.json())
        if hypothesis_data:
            return hypothesis_data[0]

    return None


async def get_premise_type(premise_id: str) -> Optional[str]:
    """Get premise_type for a premise_id"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/premises?id=eq.{premise_id}&select=premise_type",
        headers=headers,
    )
    response.raise_for_status()
    data = cast(list[dict[str, Any]], response.json())

    if data:
        return cast(Optional[str], data[0].get("premise_type"))
    return None


async def upsert_premise_learning(
    premise_id: str,
    premise_type: str,
    geo: Optional[str],
    avatar_id: Optional[str],
    was_win: bool,
    spend: float,
    revenue: float,
) -> dict:
    """
    Upsert premise learning record.

    Updates sample_size, win_count/loss_count, totals.
    win_rate and avg_roi are generated columns.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Build filter for existing record
    filters = [
        f"premise_id=eq.{premise_id}",
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

    client = get_http_client()
    # Check if record exists
    response = await client.get(
        f"{rest_url}/premise_learnings?{filter_str}",
        headers=_get_headers(supabase_key),
    )
    response.raise_for_status()
    existing = response.json()

    if existing:
        # Update existing record
        record = existing[0]
        new_sample = (record.get("sample_size") or 0) + 1
        new_wins = (record.get("win_count") or 0) + (1 if was_win else 0)
        new_losses = (record.get("loss_count") or 0) + (0 if was_win else 1)
        new_spend = float(record.get("total_spend") or 0) + spend
        new_revenue = float(record.get("total_revenue") or 0) + revenue

        # win_rate and avg_roi are generated columns, don't update them
        response = await client.patch(
            f"{rest_url}/premise_learnings?id=eq.{record['id']}",
            headers=headers,
            json={
                "sample_size": new_sample,
                "win_count": new_wins,
                "loss_count": new_losses,
                "total_spend": new_spend,
                "total_revenue": new_revenue,
                "updated_at": "now()",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data[0] if data else {}
    else:
        # Insert new record (win_rate and avg_roi are generated columns)
        response = await client.post(
            f"{rest_url}/premise_learnings",
            headers=headers,
            json={
                "premise_id": premise_id,
                "premise_type": premise_type,
                "geo": geo,
                "avatar_id": avatar_id,
                "sample_size": 1,
                "win_count": 1 if was_win else 0,
                "loss_count": 0 if was_win else 1,
                "total_spend": spend,
                "total_revenue": revenue,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data[0] if data else {}


async def process_premise_learning(
    creative_id: str,
    cpa: float,
    spend: float,
    revenue: float,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> dict:
    """
    Main entry point: process premise learning for an outcome.

    1. Get hypothesis for creative
    2. Check if hypothesis has premise_id
    3. Get premise_type
    4. Update premise_learnings (global + per-avatar if available)

    Returns summary of updates.
    """
    errors: list[str] = []
    result: dict[str, Any] = {
        "creative_id": creative_id,
        "premise_updated": False,
        "premise_id": None,
        "was_win": None,
        "errors": errors,
    }

    # Get hypothesis for creative
    hypothesis = await get_hypothesis_for_creative(creative_id)
    if not hypothesis:
        errors.append(f"No hypothesis found for creative {creative_id}")
        return result

    premise_id = hypothesis.get("premise_id")
    if not premise_id:
        # No premise for this hypothesis - this is normal, not an error
        return result

    result["premise_id"] = premise_id

    # Get premise_type
    premise_type = await get_premise_type(premise_id)
    if not premise_type:
        errors.append(f"Could not get premise_type for premise {premise_id}")
        return result

    # Determine win/loss
    was_win = is_win(cpa, spend)
    result["was_win"] = was_win

    try:
        # Global update (avatar_id = NULL)
        await upsert_premise_learning(
            premise_id=premise_id,
            premise_type=premise_type,
            geo=geo,
            avatar_id=None,
            was_win=was_win,
            spend=spend,
            revenue=revenue,
        )
        result["premise_updated"] = True

        # Per-avatar update (if avatar known)
        if avatar_id:
            await upsert_premise_learning(
                premise_id=premise_id,
                premise_type=premise_type,
                geo=geo,
                avatar_id=avatar_id,
                was_win=was_win,
                spend=spend,
                revenue=revenue,
            )

    except Exception as e:
        errors.append(f"Error updating premise_learnings: {str(e)}")

    return result


async def prepare_premise_updates(
    creative_id: str,
    cpa: float,
    spend: float,
    revenue: float,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> list[dict]:
    """
    Prepare premise learning updates for atomic RPC.

    Issue #732: Returns list of dicts ready for apply_learning_complete_atomic RPC.
    Does NOT execute the updates - caller passes to RPC for atomic execution.

    Args:
        creative_id: Creative UUID
        cpa: Cost per action
        spend: Total spend
        revenue: Total revenue
        geo: Optional geo context
        avatar_id: Optional avatar context

    Returns:
        List of update dicts, empty list if no premise to update
    """
    # Get hypothesis for creative
    hypothesis = await get_hypothesis_for_creative(creative_id)
    if not hypothesis:
        return []

    premise_id = hypothesis.get("premise_id")
    if not premise_id:
        # No premise for this hypothesis - this is normal
        return []

    # Get premise_type
    premise_type = await get_premise_type(premise_id)
    if not premise_type:
        return []

    # Determine win/loss
    was_win = is_win(cpa, spend)

    # Build updates list
    updates = []

    # Global update (avatar_id = NULL)
    updates.append(
        {
            "premise_id": premise_id,
            "premise_type": premise_type,
            "geo": geo,
            "avatar_id": None,
            "sample_size": 1,
            "win_count": 1 if was_win else 0,
            "loss_count": 0 if was_win else 1,
            "total_spend": spend,
            "total_revenue": revenue,
        }
    )

    # Per-avatar update (if avatar known)
    if avatar_id:
        updates.append(
            {
                "premise_id": premise_id,
                "premise_type": premise_type,
                "geo": geo,
                "avatar_id": avatar_id,
                "sample_size": 1,
                "win_count": 1 if was_win else 0,
                "loss_count": 0 if was_win else 1,
                "total_spend": spend,
                "total_revenue": revenue,
            }
        )

    return updates
