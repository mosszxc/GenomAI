"""
Recommendation Service

Generates recommendations for buyers: which components to use in creatives.
Uses Thompson Sampling for exploration/exploitation balance.

Includes Cross-Segment Transfer (Inspiration System):
- 10% of explorations try to transfer successful components from other segments

Issue: #124
"""

import os
import random
from src.core.http_client import get_http_client
from typing import Optional
from dataclasses import dataclass

from src.services.exploration import (
    should_explore,
    select_component_with_exploration,
    EXPLORATION_RATE,
    MIN_SAMPLES_FOR_CONFIDENCE,
)
from src.services.component_learning import TRACKABLE_COMPONENTS
from src.services.cross_transfer import find_transfer_candidates, execute_cross_transfer
from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Cross-segment transfer rate: 10% of explorations should try cross-transfer
CROSS_TRANSFER_RATE = 0.10

# Component descriptions for human-readable recommendations
COMPONENT_DESCRIPTIONS = {
    "angle_type": "angle",
    "hook_mechanism": "hook",
    "proof_type": "proof",
    "source_type": "source",
    "emotion_primary": "emotion",
    "message_structure": "structure",
    "opening_type": "opening",
    "promise_type": "promise",
    "core_belief": "belief",
    "context_frame": "context",
    "horizon": "horizon",
    "risk_level": "risk",
}


@dataclass
class RecommendedComponent:
    """Single component recommendation"""

    component_type: str
    component_value: str
    confidence: float
    sample_size: int
    is_exploration: bool


@dataclass
class Recommendation:
    """Full recommendation for a buyer"""

    id: Optional[str]
    buyer_id: Optional[str]
    avatar_id: Optional[str]
    geo: Optional[str]
    vertical: Optional[str]
    mode: str  # exploitation | exploration
    exploration_type: Optional[str]
    components: list[RecommendedComponent]
    description: str
    avg_confidence: float
    status: str = "pending"


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


def generate_description(
    components: list[RecommendedComponent], mode: str, avatar_name: Optional[str] = None
) -> str:
    """
    Generate human-readable description for buyer.

    Example:
    "Make creative with: confession hook (85%), pain angle (72%), testimonial proof (65%)"
    """
    parts = []

    for comp in components[:5]:  # Top 5 components
        readable_type = COMPONENT_DESCRIPTIONS.get(comp.component_type, comp.component_type)
        confidence_pct = int(comp.confidence * 100)
        parts.append(f"{comp.component_value} {readable_type} ({confidence_pct}%)")

    components_text = ", ".join(parts)

    if mode == "exploration":
        prefix = "Try new approach"
    else:
        prefix = "Use proven components"

    if avatar_name:
        return f"{prefix} for {avatar_name}: {components_text}"
    return f"{prefix}: {components_text}"


async def get_avatar_name(avatar_id: str) -> Optional[str]:
    """Get avatar name by ID"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/avatars?id=eq.{avatar_id}&select=name", headers=headers
    )
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0].get("name")
    return None


async def get_top_components(
    component_type: str,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """
    Get top performing components by win_rate.

    Returns components with sufficient samples, sorted by win_rate DESC.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = [
        f"component_type=eq.{component_type}",
        f"sample_size=gte.{MIN_SAMPLES_FOR_CONFIDENCE}",
    ]
    if geo:
        filters.append(f"geo=eq.{geo}")
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")

    filter_str = "&".join(filters)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings?{filter_str}"
        f"&select=component_value,win_rate,sample_size"
        f"&order=win_rate.desc"
        f"&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_all_component_values(component_type: str) -> list[str]:
    """
    Get all known values for a component type from component_learnings.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?component_type=eq.{component_type}"
        f"&select=component_value"
        f"&limit=100",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    values = set()
    for row in data:
        if row.get("component_value"):
            values.add(row["component_value"])
    return list(values)


async def generate_exploitation_recommendation(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> list[RecommendedComponent]:
    """
    Generate exploitation recommendation: use best known components.

    For each component type, get the best performing value.
    """
    components = []

    for component_type in TRACKABLE_COMPONENTS[:6]:  # Top 6 most important
        # Try avatar-specific first, fall back to global
        top = await get_top_components(component_type, geo, avatar_id, limit=1)

        if not top and avatar_id:
            # Fall back to global
            top = await get_top_components(component_type, geo, None, limit=1)

        if top:
            best = top[0]
            components.append(
                RecommendedComponent(
                    component_type=component_type,
                    component_value=best["component_value"],
                    confidence=float(best.get("win_rate") or 0),
                    sample_size=best.get("sample_size") or 0,
                    is_exploration=False,
                )
            )

    return components


async def generate_cross_transfer_recommendation(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> tuple[list[RecommendedComponent], bool]:
    """
    Try to generate recommendation using cross-segment transfer.

    Finds successful components from OTHER segments and injects them.

    Returns: (components, success)
    """
    try:
        # Find transfer candidates
        candidates = await find_transfer_candidates(
            target_avatar_id=avatar_id,
            target_geo=geo,
            limit=6,  # Top 6 components
        )

        if not candidates:
            return [], False

        components = []
        for candidate in candidates:
            # Inject into target segment
            await execute_cross_transfer(candidate)

            components.append(
                RecommendedComponent(
                    component_type=candidate.component_type,
                    component_value=candidate.component_value,
                    confidence=candidate.transfer_confidence,
                    sample_size=0,  # Newly injected
                    is_exploration=True,
                )
            )

        return components, True
    except Exception:
        # On error, return empty to fallback to regular exploration
        return [], False


async def generate_exploration_recommendation(
    avatar_id: Optional[str] = None, geo: Optional[str] = None
) -> tuple[list[RecommendedComponent], str]:
    """
    Generate exploration recommendation using Thompson Sampling.

    10% of explorations try cross-segment transfer first.

    Returns: (components, exploration_type)
    """
    # Try cross-segment transfer first (10% of explorations)
    if random.random() < CROSS_TRANSFER_RATE:
        transfer_components, success = await generate_cross_transfer_recommendation(avatar_id, geo)
        if success and transfer_components:
            return transfer_components, "cross_transfer"

    # Regular Thompson Sampling exploration
    components = []
    exploration_types = []

    for component_type in TRACKABLE_COMPONENTS[:6]:
        # Get all known values for this component
        available_values = await get_all_component_values(component_type)

        if not available_values:
            continue

        # Use Thompson Sampling to select
        decision = await select_component_with_exploration(
            component_type=component_type,
            available_values=available_values,
            geo=geo,
            avatar_id=avatar_id,
        )

        if decision.selected_option:
            opt = decision.selected_option
            components.append(
                RecommendedComponent(
                    component_type=component_type,
                    component_value=opt.value,
                    confidence=decision.exploration_score or 0.5,
                    sample_size=opt.sample_size,
                    is_exploration=decision.should_explore,
                )
            )

            if decision.exploration_type:
                exploration_types.append(decision.exploration_type)

    # Determine overall exploration type
    if "new_component" in exploration_types:
        exploration_type = "new_component"
    elif "new_avatar" in exploration_types:
        exploration_type = "new_avatar"
    elif "mutation" in exploration_types:
        exploration_type = "mutation"
    else:
        exploration_type = "random"

    return components, exploration_type


async def save_recommendation(recommendation: Recommendation) -> str:
    """
    Save recommendation to database.

    Returns: recommendation ID
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Build recommended_components JSON
    recommended_components = {}
    confidence_scores = {}
    for comp in recommendation.components:
        recommended_components[comp.component_type] = comp.component_value
        confidence_scores[comp.component_type] = comp.confidence

    payload = {
        "buyer_id": recommendation.buyer_id,
        "avatar_id": recommendation.avatar_id,
        "geo": recommendation.geo,
        "vertical": recommendation.vertical,
        "recommended_components": recommended_components,
        "mode": recommendation.mode,
        "exploration_type": recommendation.exploration_type,
        "description": recommendation.description,
        "confidence_scores": confidence_scores,
        "avg_confidence": recommendation.avg_confidence,
        "status": recommendation.status,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    client = get_http_client()
    response = await client.post(f"{rest_url}/recommendations", headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0]["id"]
    raise SupabaseError("Failed to save recommendation")


async def generate_recommendation(
    buyer_id: Optional[str] = None,
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
    force_exploration: bool = False,
) -> Recommendation:
    """
    Main entry point: generate recommendation for buyer.

    75% exploitation (proven components), 25% exploration (Thompson Sampling).

    Args:
        buyer_id: Optional buyer ID
        avatar_id: Optional target avatar
        geo: Geographic context
        vertical: Vertical context
        force_exploration: Force exploration mode

    Returns:
        Recommendation with components and description
    """
    # Decide mode
    if force_exploration or should_explore():
        mode = "exploration"
        components, exploration_type = await generate_exploration_recommendation(avatar_id, geo)
    else:
        mode = "exploitation"
        components = await generate_exploitation_recommendation(avatar_id, geo)
        exploration_type = None

        # Fallback to exploration if exploitation has no data
        # This happens when all components have win_rate=0 or insufficient samples
        if not components:
            mode = "exploration"
            exploration_type = "no_exploitation_data"
            components, _ = await generate_exploration_recommendation(avatar_id, geo)

    # Calculate average confidence
    if components:
        avg_confidence = sum(c.confidence for c in components) / len(components)
    else:
        avg_confidence = 0.0

    # Get avatar name for description
    avatar_name = None
    if avatar_id:
        avatar_name = await get_avatar_name(avatar_id)

    # Generate description
    description = generate_description(components, mode, avatar_name)

    recommendation = Recommendation(
        id=None,
        buyer_id=buyer_id,
        avatar_id=avatar_id,
        geo=geo,
        vertical=vertical,
        mode=mode,
        exploration_type=exploration_type,
        components=components,
        description=description,
        avg_confidence=avg_confidence,
        status="pending",
    )

    # Save to database
    rec_id = await save_recommendation(recommendation)
    recommendation.id = rec_id

    return recommendation


async def mark_recommendation_executed(recommendation_id: str, creative_id: str) -> dict:
    """
    Mark recommendation as executed when buyer creates creative.

    Args:
        recommendation_id: ID of recommendation
        creative_id: ID of created creative
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/recommendations?id=eq.{recommendation_id}",
        headers=headers,
        json={
            "status": "executed",
            "creative_id": creative_id,
            "executed_at": "now()",
        },
    )
    response.raise_for_status()
    return response.json()[0] if response.json() else {}


async def record_recommendation_outcome(
    recommendation_id: str,
    was_successful: bool,
    cpa: Optional[float] = None,
    spend: Optional[float] = None,
    revenue: Optional[float] = None,
) -> dict:
    """
    Record outcome for a recommendation.

    Called after learning processes the creative's outcome.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "was_successful": was_successful,
        "outcome_cpa": cpa,
        "outcome_spend": spend,
        "outcome_revenue": revenue,
        "outcome_recorded_at": "now()",
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/recommendations?id=eq.{recommendation_id}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return response.json()[0] if response.json() else {}


async def get_recommendation(recommendation_id: str) -> Optional[dict]:
    """Get recommendation by ID"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/recommendations?id=eq.{recommendation_id}", headers=headers
    )
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0]
    return None


async def get_pending_recommendations(buyer_id: Optional[str] = None) -> list[dict]:
    """Get pending recommendations, optionally filtered by buyer"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = ["status=eq.pending"]
    if buyer_id:
        filters.append(f"buyer_id=eq.{buyer_id}")

    filter_str = "&".join(filters)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/recommendations?{filter_str}&order=created_at.desc&limit=10",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_recommendation_stats() -> dict:
    """
    Get recommendation statistics for monitoring.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Total recommendations
    response = await client.get(
        f"{rest_url}/recommendations?select=id",
        headers={**headers, "Prefer": "count=exact"},
    )
    total = int(response.headers.get("content-range", "*/0").split("/")[-1])

    # By mode
    response = await client.get(
        f"{rest_url}/recommendations?select=mode&limit=1000", headers=headers
    )
    data = response.json()
    by_mode = {"exploitation": 0, "exploration": 0}
    for row in data:
        mode = row.get("mode")
        if mode in by_mode:
            by_mode[mode] += 1

    # Success rate
    response = await client.get(
        f"{rest_url}/recommendations?was_successful=eq.true&select=id",
        headers={**headers, "Prefer": "count=exact"},
    )
    successful = int(response.headers.get("content-range", "*/0").split("/")[-1])

    response = await client.get(
        f"{rest_url}/recommendations?was_successful=is.not.null&select=id",
        headers={**headers, "Prefer": "count=exact"},
    )
    with_outcome = int(response.headers.get("content-range", "*/0").split("/")[-1])

    return {
        "total_recommendations": total,
        "by_mode": by_mode,
        "exploration_rate": by_mode["exploration"] / max(total, 1),
        "target_exploration_rate": EXPLORATION_RATE,
        "with_outcome": with_outcome,
        "successful": successful,
        "success_rate": successful / max(with_outcome, 1),
    }
