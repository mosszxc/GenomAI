"""
Premise Selector Service

Selects premise for hypothesis generation using Thompson Sampling.
75% exploitation (best win_rate), 25% exploration (undersampled or new).

Issue: #168
Pattern: recommendation.py, exploration.py
"""

import os
import random
from src.core.http_client import get_http_client
from typing import Optional
from dataclasses import dataclass
from numpy.random import beta as beta_sample

from src.utils.errors import SupabaseError
from temporal.models.validators import (
    validate_uuid,
    validate_optional_uuid,
    validate_optional_safe_string,
)


SCHEMA = "genomai"

# Exploration budget
EXPLORATION_RATE = 0.25

# Minimum samples before we trust the data
MIN_SAMPLES_FOR_CONFIDENCE = 10

# Beta distribution priors (uninformative)
ALPHA_PRIOR = 1.0
BETA_PRIOR = 1.0

# Generation rate within exploration
GENERATION_RATE = 0.3  # 30% of exploration = generate new premise


@dataclass
class PremiseSelection:
    """Result of premise selection"""

    premise_id: Optional[str]
    premise_type: str
    name: str
    origin_story: Optional[str]
    mechanism_claim: Optional[str]
    is_new: bool  # True if LLM should generate new premise
    selection_reason: str  # exploitation, exploration, or generation


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


def should_explore() -> bool:
    """Returns True 25% of the time for exploration budget."""
    return random.random() < EXPLORATION_RATE


def should_generate() -> bool:
    """Returns True 30% of exploration time for generating new premises."""
    return random.random() < GENERATION_RATE


def thompson_sample(win_count: int, loss_count: int) -> float:
    """
    Sample from Beta distribution for Thompson Sampling.

    Beta(alpha + wins, beta + losses) where alpha=beta=1 (uninformative prior).
    """
    alpha = ALPHA_PRIOR + win_count
    beta = BETA_PRIOR + loss_count
    return float(beta_sample(alpha, beta))


async def get_active_premises(
    vertical: Optional[str] = None, geo: Optional[str] = None, limit: int = 50
) -> list[dict]:
    """
    Get all active premises, optionally filtered by vertical/geo.
    """
    # Validate inputs to prevent URL injection
    vertical = validate_optional_safe_string(vertical, "vertical")
    geo = validate_optional_safe_string(geo, "geo")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = ["status=eq.active"]
    if vertical:
        # Match vertical or NULL (universal)
        filters.append(f"or=(vertical.eq.{vertical},vertical.is.null)")
    if geo:
        filters.append(f"or=(geo.eq.{geo},geo.is.null)")

    filter_str = "&".join(filters)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/premises?{filter_str}"
        f"&select=id,premise_type,name,origin_story,mechanism_claim"
        f"&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_premise_learnings(
    premise_id: str, geo: Optional[str] = None, avatar_id: Optional[str] = None
) -> Optional[dict]:
    """
    Get learning stats for a specific premise in context.
    """
    # Validate inputs to prevent URL injection
    premise_id = validate_uuid(premise_id, "premise_id")
    geo = validate_optional_safe_string(geo, "geo")
    avatar_id = validate_optional_uuid(avatar_id, "avatar_id")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = [f"premise_id=eq.{premise_id}"]
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
    response = await client.get(f"{rest_url}/premise_learnings?{filter_str}", headers=headers)
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0]
    return None


async def get_top_premises(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Get top performing premises by win_rate from premise_learnings.
    """
    # Validate inputs to prevent URL injection
    geo = validate_optional_safe_string(geo, "geo")
    avatar_id = validate_optional_uuid(avatar_id, "avatar_id")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build filter
    filters = [f"sample_size=gte.{MIN_SAMPLES_FOR_CONFIDENCE}"]
    if geo:
        filters.append(f"or=(geo.eq.{geo},geo.is.null)")
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")

    filter_str = "&".join(filters)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/premise_learnings?{filter_str}"
        f"&select=premise_id,premise_type,win_rate,sample_size,win_count,loss_count"
        f"&order=win_rate.desc"
        f"&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_undersampled_premises(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    min_sample_threshold: int = MIN_SAMPLES_FOR_CONFIDENCE,
    limit: int = 10,
) -> list[dict]:
    """
    Get premises with low sample counts for exploration.

    Returns active premises that have fewer than min_sample_threshold samples.
    """
    # Validate inputs to prevent URL injection
    vertical = validate_optional_safe_string(vertical, "vertical")
    geo = validate_optional_safe_string(geo, "geo")

    # Get all active premises
    all_premises = await get_active_premises(vertical=vertical, geo=geo)

    # Get learnings for each and filter undersampled
    undersampled = []

    for premise in all_premises:
        learning = await get_premise_learnings(premise["id"], geo=geo, avatar_id=None)
        sample_size = learning.get("sample_size", 0) if learning else 0

        if sample_size < min_sample_threshold:
            undersampled.append(
                {
                    **premise,
                    "sample_size": sample_size,
                    "win_count": learning.get("win_count", 0) if learning else 0,
                    "loss_count": learning.get("loss_count", 0) if learning else 0,
                }
            )

    # Sort by sample_size ascending (least sampled first)
    undersampled.sort(key=lambda x: x["sample_size"])

    return undersampled[:limit]


async def select_best_premise(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Select the best premise by win_rate (exploitation).
    """
    # Note: geo and avatar_id are validated in get_top_premises and get_active_premises
    top_premises = await get_top_premises(vertical=vertical, geo=geo, avatar_id=avatar_id, limit=1)

    if not top_premises:
        # No premises with enough samples - fall back to any active premise
        active = await get_active_premises(vertical=vertical, geo=geo, limit=1)
        if active:
            return active[0]
        return None

    # Get full premise details - validate premise_id from DB result
    premise_id = validate_uuid(top_premises[0]["premise_id"], "premise_id")
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/premises?id=eq.{premise_id}"
        f"&select=id,premise_type,name,origin_story,mechanism_claim",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0]
    return None


async def select_exploration_premise(
    vertical: Optional[str] = None, geo: Optional[str] = None
) -> Optional[dict]:
    """
    Select premise for exploration using Thompson Sampling.

    Returns undersampled premise or None (signal for generation).
    """
    # Note: vertical and geo are validated in get_undersampled_premises
    undersampled = await get_undersampled_premises(vertical=vertical, geo=geo)

    if not undersampled:
        return None  # Signal: should generate new premise

    # Thompson Sampling among undersampled
    scored = []
    for premise in undersampled:
        score = thompson_sample(premise.get("win_count", 0), premise.get("loss_count", 0))
        scored.append((score, premise))

    # Select highest Thompson score
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


async def select_premise_for_hypothesis(
    idea_id: str,
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
    force_exploration: bool = False,
) -> PremiseSelection:
    """
    Main entry point: Select or generate premise for hypothesis.

    Flow:
    1. 75% exploitation: Use best performing premise
    2. 25% exploration:
       a. 70% of exploration: Use undersampled premise (Thompson Sampling)
       b. 30% of exploration: Signal for LLM generation (is_new=True)

    Args:
        idea_id: The idea for which hypothesis is being generated
        avatar_id: Optional avatar context
        geo: Optional geo context
        vertical: Optional vertical filter
        force_exploration: Force exploration mode (for testing)

    Returns:
        PremiseSelection with premise details or is_new=True for generation
    """
    # Validate inputs upfront to prevent URL injection
    # Note: idea_id is not used in URL queries here, but validate for consistency
    _ = validate_uuid(idea_id, "idea_id")
    avatar_id = validate_optional_uuid(avatar_id, "avatar_id")
    geo = validate_optional_safe_string(geo, "geo")
    vertical = validate_optional_safe_string(vertical, "vertical")

    explore = force_exploration or should_explore()

    if explore:
        # Exploration mode
        if should_generate():
            # Signal for LLM generation
            return PremiseSelection(
                premise_id=None,
                premise_type="method",  # Default type for generation
                name="",
                origin_story=None,
                mechanism_claim=None,
                is_new=True,
                selection_reason="generation",
            )
        else:
            # Thompson Sampling among undersampled
            premise = await select_exploration_premise(vertical=vertical, geo=geo)

            if premise is None:
                # No undersampled premises - trigger generation
                return PremiseSelection(
                    premise_id=None,
                    premise_type="method",
                    name="",
                    origin_story=None,
                    mechanism_claim=None,
                    is_new=True,
                    selection_reason="generation",
                )

            return PremiseSelection(
                premise_id=premise["id"],
                premise_type=premise["premise_type"],
                name=premise["name"],
                origin_story=premise.get("origin_story"),
                mechanism_claim=premise.get("mechanism_claim"),
                is_new=False,
                selection_reason="exploration",
            )
    else:
        # Exploitation mode
        premise = await select_best_premise(vertical=vertical, geo=geo, avatar_id=avatar_id)

        if premise is None:
            # No premises at all - trigger generation
            return PremiseSelection(
                premise_id=None,
                premise_type="method",
                name="",
                origin_story=None,
                mechanism_claim=None,
                is_new=True,
                selection_reason="generation",
            )

        return PremiseSelection(
            premise_id=premise["id"],
            premise_type=premise["premise_type"],
            name=premise["name"],
            origin_story=premise.get("origin_story"),
            mechanism_claim=premise.get("mechanism_claim"),
            is_new=False,
            selection_reason="exploitation",
        )
