"""
Component Pair Winrate Feature

Computes winrate for pairs of hook_mechanism x angle_type combinations.
Hypothesis: Some component pairs work synergistically.

Issue: #304
"""

import os
from typing import Optional
from dataclasses import dataclass
import httpx

from src.utils.errors import SupabaseError


SCHEMA = "genomai"
FEATURE_NAME = "component_pair_winrate"
MIN_PAIR_SAMPLE_SIZE = 10
CPA_WIN_THRESHOLD = 5.0

# SQL definition for feature registration
SQL_DEFINITION = """
-- Component pair winrate: hook_mechanism x angle_type
WITH component_pairs AS (
    SELECT
        dc.id as decomposed_id,
        dc.idea_id,
        dc.payload->>'hook_mechanism' as hook,
        dc.payload->>'angle_type' as angle,
        oa.cpa,
        CASE WHEN oa.cpa < 5 THEN 1 ELSE 0 END as is_win
    FROM genomai.decomposed_creatives dc
    JOIN genomai.decisions d ON d.idea_id = dc.idea_id
    JOIN genomai.outcome_aggregates oa ON oa.decision_id = d.id
    WHERE dc.payload->>'hook_mechanism' IS NOT NULL
      AND dc.payload->>'angle_type' IS NOT NULL
      AND oa.cpa IS NOT NULL
)
SELECT
    hook || '_x_' || angle as pair_key,
    COUNT(*) as sample_size,
    SUM(is_win)::NUMERIC / NULLIF(COUNT(*), 0) as pair_winrate,
    AVG(cpa) as avg_cpa
FROM component_pairs
GROUP BY hook, angle
HAVING COUNT(*) >= 10;
"""


@dataclass
class PairStats:
    """Statistics for a component pair"""

    pair_key: str
    sample_size: int
    pair_winrate: float
    avg_cpa: float


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API"""
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


async def get_all_pair_stats() -> dict[str, PairStats]:
    """
    Compute winrate statistics for all component pairs.

    Returns:
        Dict mapping pair_key to PairStats
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Use RPC to execute complex SQL
    # First, get decomposed creatives with components
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?select=id,idea_id,payload"
            f"&idea_id=not.is.null"
            f"&limit=1000",
            headers=headers,
        )
        response.raise_for_status()
        decomposed = response.json()

    if not decomposed:
        return {}

    # Filter to those with hook_mechanism and angle_type
    valid_decomposed = []
    for dc in decomposed:
        payload = dc.get("payload", {})
        hook = payload.get("hook_mechanism")
        angle = payload.get("angle_type")
        if hook and angle:
            valid_decomposed.append(
                {
                    "id": dc["id"],
                    "idea_id": dc["idea_id"],
                    "hook": hook,
                    "angle": angle,
                }
            )

    if not valid_decomposed:
        return {}

    # Get decisions for these ideas
    idea_ids = list(set(dc["idea_id"] for dc in valid_decomposed))

    all_decisions = []
    for i in range(0, len(idea_ids), 50):
        batch_ids = idea_ids[i : i + 50]
        ids_param = ",".join(batch_ids)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{rest_url}/decisions?idea_id=in.({ids_param})&select=id,idea_id",
                headers=headers,
            )
            response.raise_for_status()
            all_decisions.extend(response.json())

    if not all_decisions:
        return {}

    # Map idea_id -> decision_id
    idea_to_decision = {d["idea_id"]: d["id"] for d in all_decisions}
    decision_ids = list(idea_to_decision.values())

    # Get outcome_aggregates with CPA
    all_outcomes = []
    for i in range(0, len(decision_ids), 50):
        batch_ids = decision_ids[i : i + 50]
        ids_param = ",".join(batch_ids)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{rest_url}/outcome_aggregates"
                f"?decision_id=in.({ids_param})"
                f"&cpa=not.is.null"
                f"&select=decision_id,cpa",
                headers=headers,
            )
            response.raise_for_status()
            all_outcomes.extend(response.json())

    if not all_outcomes:
        return {}

    # Map decision_id -> latest cpa (use avg if multiple)
    decision_to_cpa: dict[str, list[float]] = {}
    for outcome in all_outcomes:
        dec_id = outcome["decision_id"]
        cpa = float(outcome["cpa"])
        if dec_id not in decision_to_cpa:
            decision_to_cpa[dec_id] = []
        decision_to_cpa[dec_id].append(cpa)

    decision_to_avg_cpa = {
        dec_id: sum(cpas) / len(cpas) for dec_id, cpas in decision_to_cpa.items()
    }

    # Aggregate by pair
    pair_data: dict[str, dict] = {}
    for dc in valid_decomposed:
        idea_id = dc["idea_id"]
        if idea_id not in idea_to_decision:
            continue
        decision_id = idea_to_decision[idea_id]
        if decision_id not in decision_to_avg_cpa:
            continue

        pair_key = f"{dc['hook']}_x_{dc['angle']}"
        cpa = decision_to_avg_cpa[decision_id]
        is_win = 1 if cpa < CPA_WIN_THRESHOLD else 0

        if pair_key not in pair_data:
            pair_data[pair_key] = {
                "wins": 0,
                "count": 0,
                "cpa_sum": 0.0,
            }

        pair_data[pair_key]["wins"] += is_win
        pair_data[pair_key]["count"] += 1
        pair_data[pair_key]["cpa_sum"] += cpa

    # Convert to PairStats, filtering by min sample size
    result = {}
    for pair_key, data in pair_data.items():
        if data["count"] >= MIN_PAIR_SAMPLE_SIZE:
            result[pair_key] = PairStats(
                pair_key=pair_key,
                sample_size=data["count"],
                pair_winrate=data["wins"] / data["count"],
                avg_cpa=data["cpa_sum"] / data["count"],
            )

    return result


async def get_pair_stats(pair_key: str) -> Optional[PairStats]:
    """
    Get statistics for a specific component pair.

    Args:
        pair_key: Pair key in format "hook_x_angle"

    Returns:
        PairStats or None if not enough samples
    """
    all_stats = await get_all_pair_stats()
    return all_stats.get(pair_key)


async def compute_pair_winrate_for_idea(idea_id: str) -> Optional[float]:
    """
    Compute pair winrate feature value for an idea.

    Args:
        idea_id: UUID of the idea

    Returns:
        Pair winrate (0.0-1.0) or None if not computable
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Get decomposed creative for this idea
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?idea_id=eq.{idea_id}"
            f"&select=payload"
            f"&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        decomposed = response.json()

    if not decomposed:
        return None

    payload = decomposed[0].get("payload", {})
    hook = payload.get("hook_mechanism")
    angle = payload.get("angle_type")

    if not hook or not angle:
        return None

    pair_key = f"{hook}_x_{angle}"
    stats = await get_pair_stats(pair_key)

    if stats:
        return stats.pair_winrate
    return None


async def compute_and_store_for_idea(idea_id: str) -> Optional[dict]:
    """
    Compute pair winrate for idea and store in derived_feature_values.

    Args:
        idea_id: UUID of the idea

    Returns:
        Stored record or None if not computable
    """
    value = await compute_pair_winrate_for_idea(idea_id)
    if value is None:
        return None

    from src.services.feature_registry import store_feature_value

    return await store_feature_value(
        feature_name=FEATURE_NAME,
        entity_type="idea",
        entity_id=idea_id,
        value=value,
    )


async def register_feature() -> dict:
    """
    Register component_pair_winrate feature in shadow mode.

    Returns:
        Created feature record
    """
    from src.services.feature_registry import add_feature, get_feature

    # Check if already registered
    existing = await get_feature(FEATURE_NAME)
    if existing:
        return existing

    return await add_feature(
        name=FEATURE_NAME,
        sql_definition=SQL_DEFINITION,
        description="Winrate for hook_mechanism x angle_type pairs. "
        "Hypothesis: some component combinations work synergistically.",
    )
