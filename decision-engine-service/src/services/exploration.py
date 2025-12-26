"""
Exploration Service

Implements Thompson Sampling for exploration vs exploitation.
25% of decisions should be exploration to avoid local optima.

Issue: #123
"""

import os
import random
import httpx
from typing import Optional
from dataclasses import dataclass
from numpy.random import beta as beta_sample

from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Exploration budget
EXPLORATION_RATE = 0.25

# Minimum samples before we trust the data
MIN_SAMPLES_FOR_CONFIDENCE = 30

# Beta distribution priors (uninformative)
ALPHA_PRIOR = 1.0
BETA_PRIOR = 1.0


@dataclass
class ExplorationOption:
    """Option for Thompson Sampling selection"""
    id: str
    option_type: str  # 'avatar', 'component', etc.
    value: str
    win_count: int
    loss_count: int
    sample_size: int
    geo: Optional[str] = None
    avatar_id: Optional[str] = None


@dataclass
class ExplorationDecision:
    """Result of exploration decision"""
    should_explore: bool
    selected_option: Optional[ExplorationOption]
    exploration_type: Optional[str]
    exploration_score: Optional[float]
    exploitation_score: Optional[float]


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


def should_explore() -> bool:
    """
    Determine if this decision should be exploration.

    Returns True 25% of the time for exploration budget.
    """
    return random.random() < EXPLORATION_RATE


def thompson_sample(win_count: int, loss_count: int) -> float:
    """
    Sample from Beta distribution for Thompson Sampling.

    Beta(alpha + wins, beta + losses) where alpha=beta=1 (uninformative prior).

    Key insight:
    - Few samples = wide distribution = high variance = might sample high value
    - Many samples = narrow distribution = samples close to true win rate
    """
    alpha = ALPHA_PRIOR + win_count
    beta = BETA_PRIOR + loss_count
    return float(beta_sample(alpha, beta))


def select_with_thompson_sampling(
    options: list[ExplorationOption]
) -> tuple[ExplorationOption, float, bool]:
    """
    Select option using Thompson Sampling.

    Returns:
        tuple: (selected_option, score, is_exploration)

    is_exploration = True if selected option has < MIN_SAMPLES_FOR_CONFIDENCE
    """
    if not options:
        raise ValueError("No options to select from")

    if len(options) == 1:
        opt = options[0]
        score = thompson_sample(opt.win_count, opt.loss_count)
        is_exploration = opt.sample_size < MIN_SAMPLES_FOR_CONFIDENCE
        return opt, score, is_exploration

    # Sample from each option's posterior
    scored_options = []
    for opt in options:
        score = thompson_sample(opt.win_count, opt.loss_count)
        scored_options.append((opt, score))

    # Sort by score descending
    scored_options.sort(key=lambda x: x[1], reverse=True)

    selected, selected_score = scored_options[0]

    # Is this exploration? Check if selected has few samples
    is_exploration = selected.sample_size < MIN_SAMPLES_FOR_CONFIDENCE

    return selected, selected_score, is_exploration


def get_exploration_type(option: ExplorationOption) -> str:
    """Determine exploration type based on option characteristics"""
    if option.sample_size == 0:
        return "new_component" if option.option_type == "component" else "new_avatar"
    elif option.sample_size < 10:
        return "new_component" if option.option_type == "component" else "new_avatar"
    elif option.sample_size < MIN_SAMPLES_FOR_CONFIDENCE:
        return "mutation"
    else:
        return "random"


async def get_component_options(
    component_type: str,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None
) -> list[ExplorationOption]:
    """
    Fetch component learning data for Thompson Sampling.

    Args:
        component_type: Type of component (e.g., 'hook_mechanism')
        geo: Optional geo filter
        avatar_id: Optional avatar filter (None = global learning)

    Returns:
        List of ExplorationOption with win/loss counts
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    filters = [f"component_type=eq.{component_type}"]
    if geo:
        filters.append(f"geo=eq.{geo}")
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/component_learnings?{filter_str}"
            f"&select=id,component_value,win_count,loss_count,sample_size,geo,avatar_id",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

    options = []
    for row in data:
        options.append(ExplorationOption(
            id=row['id'],
            option_type='component',
            value=row['component_value'],
            win_count=row.get('win_count') or 0,
            loss_count=row.get('loss_count') or 0,
            sample_size=row.get('sample_size') or 0,
            geo=row.get('geo'),
            avatar_id=row.get('avatar_id')
        ))

    return options


async def log_exploration(
    exploration_type: str,
    idea_id: Optional[str] = None,
    avatar_id: Optional[str] = None,
    component_type: Optional[str] = None,
    component_value: Optional[str] = None,
    geo: Optional[str] = None,
    exploration_score: Optional[float] = None,
    exploitation_score: Optional[float] = None,
    sample_size_at_decision: Optional[int] = None
) -> dict:
    """
    Log exploration decision to exploration_log table.

    Returns created record.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "exploration_type": exploration_type,
        "idea_id": idea_id,
        "avatar_id": avatar_id,
        "component_type": component_type,
        "component_value": component_value,
        "geo": geo,
        "exploration_score": exploration_score,
        "exploitation_score": exploitation_score,
        "sample_size_at_decision": sample_size_at_decision
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/exploration_log",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()[0] if response.json() else {}


async def record_exploration_outcome(
    exploration_id: str,
    was_successful: bool,
    cpa: Optional[float] = None,
    spend: Optional[float] = None,
    revenue: Optional[float] = None
) -> dict:
    """
    Record outcome for an exploration decision.

    Args:
        exploration_id: ID of exploration_log record
        was_successful: Whether exploration led to good outcome
        cpa: Cost per acquisition (if available)
        spend: Total spend (if available)
        revenue: Total revenue (if available)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "was_successful": was_successful,
        "outcome_cpa": cpa,
        "outcome_spend": spend,
        "outcome_revenue": revenue,
        "outcome_recorded_at": "now()"
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/exploration_log?id=eq.{exploration_id}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()[0] if response.json() else {}


async def select_component_with_exploration(
    component_type: str,
    available_values: list[str],
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None
) -> ExplorationDecision:
    """
    Select a component value using exploration/exploitation strategy.

    This is the main entry point for recommendation with exploration.

    Args:
        component_type: Type of component to select
        available_values: List of possible component values
        geo: Geographic context
        avatar_id: Avatar context (None = global)

    Returns:
        ExplorationDecision with selected option and metadata
    """
    # Get existing learning data
    known_options = await get_component_options(component_type, geo, avatar_id)
    known_values = {opt.value for opt in known_options}

    # Create options for unknown values (no data = maximum uncertainty)
    all_options = list(known_options)
    for value in available_values:
        if value not in known_values:
            all_options.append(ExplorationOption(
                id=f"new_{value}",
                option_type='component',
                value=value,
                win_count=0,
                loss_count=0,
                sample_size=0,
                geo=geo,
                avatar_id=avatar_id
            ))

    if not all_options:
        return ExplorationDecision(
            should_explore=False,
            selected_option=None,
            exploration_type=None,
            exploration_score=None,
            exploitation_score=None
        )

    # Find best known option (highest win rate with sufficient samples)
    confident_options = [o for o in all_options if o.sample_size >= MIN_SAMPLES_FOR_CONFIDENCE]
    exploitation_score = None
    if confident_options:
        best_known = max(confident_options,
                         key=lambda o: o.win_count / max(o.sample_size, 1))
        exploitation_score = best_known.win_count / max(best_known.sample_size, 1)

    # Thompson Sampling selection
    selected, exploration_score, is_exploration = select_with_thompson_sampling(all_options)

    exploration_type = get_exploration_type(selected) if is_exploration else None

    return ExplorationDecision(
        should_explore=is_exploration,
        selected_option=selected,
        exploration_type=exploration_type,
        exploration_score=exploration_score,
        exploitation_score=exploitation_score
    )


async def get_exploration_stats() -> dict:
    """
    Get exploration statistics for monitoring.

    Returns:
        dict with exploration rates, success rates, etc.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # Total explorations
        response = await client.get(
            f"{rest_url}/exploration_log?select=id",
            headers={**headers, "Prefer": "count=exact"}
        )
        total = int(response.headers.get('content-range', '*/0').split('/')[-1])

        # Successful explorations
        response = await client.get(
            f"{rest_url}/exploration_log?was_successful=eq.true&select=id",
            headers={**headers, "Prefer": "count=exact"}
        )
        successful = int(response.headers.get('content-range', '*/0').split('/')[-1])

        # By type
        response = await client.get(
            f"{rest_url}/exploration_log"
            f"?select=exploration_type"
            f"&limit=1000",
            headers=headers
        )
        data = response.json()
        by_type = {}
        for row in data:
            t = row['exploration_type']
            by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_explorations": total,
        "successful_explorations": successful,
        "success_rate": successful / max(total, 1),
        "by_type": by_type,
        "target_exploration_rate": EXPLORATION_RATE,
        "min_samples_for_confidence": MIN_SAMPLES_FOR_CONFIDENCE
    }
