"""
Learning Loop Service

Processes outcome_aggregates and applies learning to ideas:
- Updates confidence_weight with time decay and environment weighting
- Updates fatigue_level
- Checks and applies death conditions
- Marks outcomes as processed (learning_applied=true)

Based on LEARNING_MEMORY_POLICY.md and ARCHITECTURE_LOCK.md
"""

import os
import httpx
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.utils.errors import SupabaseError
from src.utils.time_decay import time_decay, days_since
from src.utils.environment import apply_environment_weight, is_environment_degraded
from src.services.component_learning import process_component_learnings


SCHEMA = "genomai"

# Learning configuration
TARGET_CPA = 20.0  # CPA threshold for good/bad outcome
CONFIDENCE_DELTA_GOOD = 0.1  # Delta for good outcome (CPA < target)
CONFIDENCE_DELTA_BAD = -0.15  # Delta for bad outcome (CPA >= target)
CONSECUTIVE_FAILURES_SOFT_DEAD = 3
CONSECUTIVE_FAILURES_HARD_DEAD = 5


@dataclass
class LearningResult:
    """Result of learning loop batch processing"""
    processed_count: int = 0
    updated_ideas: list = None
    new_deaths: list = None
    component_updates: int = 0
    errors: list = None

    def __post_init__(self):
        self.updated_ideas = self.updated_ideas or []
        self.new_deaths = self.new_deaths or []
        self.errors = self.errors or []

    def to_dict(self) -> dict:
        return {
            "processed_count": self.processed_count,
            "updated_ideas": self.updated_ideas,
            "new_deaths": self.new_deaths,
            "component_updates": self.component_updates,
            "errors": self.errors
        }


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


async def fetch_unprocessed_outcomes(limit: int = 100) -> list:
    """
    Fetch outcomes that haven't been processed by learning loop.

    Returns outcomes with:
    - learning_applied = false
    - origin_type = 'system'
    - Has valid cpa value
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/outcome_aggregates"
            f"?learning_applied=eq.false"
            f"&origin_type=eq.system"
            f"&cpa=not.is.null"
            f"&select=id,creative_id,cpa,spend,environment_ctx,window_end,decision_id"
            f"&limit={limit}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


async def resolve_idea_for_outcome(outcome: dict) -> Optional[str]:
    """
    Resolve idea_id for an outcome via decomposed_creatives.

    Path: outcome.creative_id -> decomposed_creatives.creative_id -> idea_id
    """
    creative_id = outcome.get('creative_id')
    if not creative_id:
        return None

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # First try direct idea_id column
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?creative_id=eq.{creative_id}"
            f"&select=idea_id",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and data[0].get('idea_id'):
            return data[0]['idea_id']

        # Fallback: extract from payload
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?creative_id=eq.{creative_id}"
            f"&select=payload",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and data[0].get('payload'):
            payload = data[0]['payload']
            if isinstance(payload, dict):
                return payload.get('idea_id')

        return None


async def get_current_confidence(idea_id: str) -> tuple[float, int]:
    """
    Get current confidence value and version for an idea.

    Returns (confidence_value, version) or (0.0, 0) if no history
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/idea_confidence_versions"
            f"?idea_id=eq.{idea_id}"
            f"&select=confidence_value,version"
            f"&order=version.desc"
            f"&limit=1",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data:
            return float(data[0]['confidence_value']), int(data[0]['version'])

        return 0.0, 0


async def get_recent_outcomes_for_idea(idea_id: str, limit: int = 10) -> list:
    """Get recent outcomes for idea to check death conditions"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # Get outcomes via decomposed_creatives
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?idea_id=eq.{idea_id}"
            f"&select=creative_id",
            headers=headers
        )
        response.raise_for_status()
        creatives = response.json()

        if not creatives:
            return []

        creative_ids = [c['creative_id'] for c in creatives if c.get('creative_id')]
        if not creative_ids:
            return []

        # Fetch outcomes for these creatives
        creative_filter = ",".join(creative_ids)
        response = await client.get(
            f"{rest_url}/outcome_aggregates"
            f"?creative_id=in.({creative_filter})"
            f"&origin_type=eq.system"
            f"&select=id,cpa,window_end"
            f"&order=window_end.desc"
            f"&limit={limit}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


def calculate_confidence_delta(
    cpa: float,
    outcome_date: str,
    env_ctx: Optional[dict]
) -> float:
    """
    Calculate confidence delta based on CPA, time decay, and environment.

    Args:
        cpa: CPA value from outcome
        outcome_date: Window end date (ISO string)
        env_ctx: Environment context

    Returns:
        Weighted confidence delta
    """
    # Base delta based on CPA threshold
    if cpa < TARGET_CPA:
        base_delta = CONFIDENCE_DELTA_GOOD
    else:
        base_delta = CONFIDENCE_DELTA_BAD

    # Apply time decay
    days = days_since(outcome_date)
    decay_factor = time_decay(days)
    decayed_delta = base_delta * decay_factor

    # Apply environment weighting
    weighted_delta = apply_environment_weight(decayed_delta, env_ctx)

    return weighted_delta


def check_death_condition(outcomes: list, was_resurrected: bool = False) -> Optional[str]:
    """
    Check if idea should die based on consecutive failures.

    Args:
        outcomes: Recent outcomes sorted by date desc
        was_resurrected: Whether idea was previously resurrected

    Returns:
        'soft_dead', 'hard_dead', or None
    """
    if not outcomes:
        return None

    # Count consecutive failures from most recent
    consecutive_failures = 0
    for outcome in outcomes:
        cpa = outcome.get('cpa')
        if cpa is None:
            continue
        if float(cpa) >= TARGET_CPA:
            consecutive_failures += 1
        else:
            break  # Success breaks the streak

    if was_resurrected and consecutive_failures >= CONSECUTIVE_FAILURES_HARD_DEAD:
        return 'hard_dead'
    elif consecutive_failures >= CONSECUTIVE_FAILURES_SOFT_DEAD:
        return 'soft_dead'

    return None


async def insert_confidence_version(
    idea_id: str,
    confidence_value: float,
    version: int,
    outcome_id: str,
    change_reason: str = "learning_applied"
) -> dict:
    """Insert new confidence version"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/idea_confidence_versions",
            headers=headers,
            json={
                "idea_id": idea_id,
                "confidence_value": confidence_value,
                "version": version,
                "source_outcome_id": outcome_id,
                "change_reason": change_reason
            }
        )
        response.raise_for_status()
        return response.json()[0]


async def update_idea_death_state(idea_id: str, death_state: str) -> dict:
    """Update idea death state"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/ideas?id=eq.{idea_id}",
            headers=headers,
            json={"death_state": death_state}
        )
        response.raise_for_status()
        return response.json()[0] if response.json() else {}


async def mark_outcome_processed(outcome_id: str) -> None:
    """Mark outcome as processed by learning loop"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/outcome_aggregates?id=eq.{outcome_id}",
            headers=headers,
            json={"learning_applied": True}
        )
        response.raise_for_status()


async def emit_learning_event(
    idea_id: str,
    outcome_id: str,
    old_confidence: float,
    new_confidence: float,
    delta: float,
    death_state: Optional[str] = None
) -> None:
    """Emit learning.applied event to event_log"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "outcome_id": outcome_id,
        "old_confidence": old_confidence,
        "new_confidence": new_confidence,
        "delta": delta
    }
    if death_state:
        payload["death_state"] = death_state

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/event_log",
            headers=headers,
            json={
                "event_type": "learning.applied",
                "entity_type": "idea",
                "entity_id": idea_id,
                "payload": payload
            }
        )
        response.raise_for_status()


async def process_single_outcome(outcome: dict) -> dict:
    """
    Process a single outcome and apply learning.

    Returns dict with result info or error
    """
    outcome_id = outcome['id']
    creative_id = outcome.get('creative_id')
    cpa = float(outcome['cpa'])
    spend = float(outcome.get('spend') or 0)
    env_ctx = outcome.get('environment_ctx')
    window_end = outcome.get('window_end', datetime.now().isoformat())

    # Resolve idea
    idea_id = await resolve_idea_for_outcome(outcome)
    if not idea_id:
        return {"error": f"Could not resolve idea for outcome {outcome_id}"}

    # Get current confidence
    current_confidence, current_version = await get_current_confidence(idea_id)

    # Calculate delta
    delta = calculate_confidence_delta(cpa, window_end, env_ctx)
    new_confidence = current_confidence + delta
    new_version = current_version + 1

    # Insert new confidence version
    await insert_confidence_version(
        idea_id=idea_id,
        confidence_value=new_confidence,
        version=new_version,
        outcome_id=outcome_id
    )

    # Check death conditions
    recent_outcomes = await get_recent_outcomes_for_idea(idea_id)
    death_state = check_death_condition(recent_outcomes)

    if death_state:
        await update_idea_death_state(idea_id, death_state)

    # Mark outcome as processed
    await mark_outcome_processed(outcome_id)

    # Emit event
    await emit_learning_event(
        idea_id=idea_id,
        outcome_id=outcome_id,
        old_confidence=current_confidence,
        new_confidence=new_confidence,
        delta=delta,
        death_state=death_state
    )

    # Process component learnings (issue #122)
    component_result = None
    if creative_id:
        try:
            component_result = await process_component_learnings(
                creative_id=creative_id,
                cpa=cpa,
                spend=spend,
                revenue=0  # Revenue not tracked in outcome_aggregates yet
            )
        except Exception as e:
            component_result = {"error": str(e)}

    return {
        "idea_id": idea_id,
        "outcome_id": outcome_id,
        "old_confidence": current_confidence,
        "new_confidence": new_confidence,
        "delta": delta,
        "death_state": death_state,
        "component_learning": component_result
    }


async def process_learning_batch(limit: int = 100) -> LearningResult:
    """
    Process a batch of unprocessed outcomes.

    Main entry point for Learning Loop.
    Called by /learning/process endpoint.
    """
    result = LearningResult()

    try:
        outcomes = await fetch_unprocessed_outcomes(limit)

        for outcome in outcomes:
            try:
                learn_result = await process_single_outcome(outcome)

                if "error" in learn_result:
                    result.errors.append(learn_result["error"])
                else:
                    result.processed_count += 1
                    result.updated_ideas.append(learn_result["idea_id"])

                    if learn_result.get("death_state"):
                        result.new_deaths.append({
                            "idea_id": learn_result["idea_id"],
                            "death_state": learn_result["death_state"]
                        })

                    # Track component learning updates
                    comp_result = learn_result.get("component_learning")
                    if comp_result and "components_updated" in comp_result:
                        result.component_updates += comp_result["components_updated"]

            except Exception as e:
                result.errors.append(f"Error processing outcome {outcome['id']}: {str(e)}")

    except Exception as e:
        result.errors.append(f"Failed to fetch outcomes: {str(e)}")

    return result
