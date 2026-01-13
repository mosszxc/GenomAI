"""
Learning Loop Service

Processes outcome_aggregates and applies learning to ideas:
- Updates confidence_weight with time decay and environment weighting
- Updates fatigue_level
- Checks and applies death conditions
- Marks outcomes as processed (learning_applied=true)

Based on LEARNING_MEMORY_POLICY.md and ARCHITECTURE_LOCK.md
"""

from __future__ import annotations

import logging
import os
from src.core.http_client import get_http_client
from datetime import datetime
from typing import Any, Optional, cast
from dataclasses import dataclass, field

from src.utils.errors import SupabaseError
from src.utils.time_decay import time_decay, days_since
from src.utils.environment import apply_environment_weight
from src.services.component_learning import process_component_learnings
from src.services.premise_learning import process_premise_learning
from src.services.features.component_pair_winrate import compute_and_store_for_idea


logger = logging.getLogger(__name__)

SCHEMA = "genomai"

# Learning configuration
TARGET_CPA = 20.0  # CPA threshold for good/bad outcome
CONFIDENCE_DELTA_GOOD = 0.1  # Delta for good outcome (CPA < target)
CONFIDENCE_DELTA_BAD = -0.15  # Delta for bad outcome (CPA >= target)
CONSECUTIVE_FAILURES_SOFT_DEAD = 3
CONSECUTIVE_FAILURES_HARD_DEAD = 5
MAX_FATIGUE = 1000.0  # Issue #566: Maximum fatigue value before overflow warning


@dataclass
class LearningResult:
    """Result of learning loop batch processing"""

    processed_count: int = 0
    skipped_count: int = 0  # Issue #473: idempotency - already processed outcomes
    updated_ideas: list[str] = field(default_factory=list)
    new_deaths: list[dict[Any, Any]] = field(default_factory=list)
    component_updates: int = 0
    premise_updates: int = 0
    fatigue_updates: int = 0  # Issue #237: track fatigue versioning
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "updated_ideas": self.updated_ideas,
            "new_deaths": self.new_deaths,
            "component_updates": self.component_updates,
            "premise_updates": self.premise_updates,
            "fatigue_updates": self.fatigue_updates,
            "errors": self.errors,
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
        "Content-Type": "application/json",
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

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/outcome_aggregates"
        f"?learning_applied=eq.false"
        f"&origin_type=eq.system"
        f"&cpa=not.is.null"
        f"&select=id,creative_id,cpa,spend,environment_ctx,window_end,decision_id"
        f"&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return cast(list[Any], response.json())


async def resolve_idea_for_outcome(outcome: dict) -> Optional[str]:
    """
    Resolve idea_id for an outcome via decomposed_creatives.

    Path: outcome.creative_id -> decomposed_creatives.creative_id -> idea_id
    """
    creative_id = outcome.get("creative_id")
    if not creative_id:
        return None

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # First try direct idea_id column
    response = await client.get(
        f"{rest_url}/decomposed_creatives?creative_id=eq.{creative_id}&select=idea_id",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data and data[0].get("idea_id"):
        return cast(str, data[0]["idea_id"])

    # Fallback: extract from payload
    response = await client.get(
        f"{rest_url}/decomposed_creatives?creative_id=eq.{creative_id}&select=payload",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data and data[0].get("payload"):
        payload = data[0]["payload"]
        if isinstance(payload, dict):
            return cast(Optional[str], payload.get("idea_id"))

    return None


async def get_current_confidence(idea_id: str) -> tuple[float, int]:
    """
    Get current confidence value and version for an idea.

    Returns (confidence_value, version) or (0.0, 0) if no history
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/idea_confidence_versions"
        f"?idea_id=eq.{idea_id}"
        f"&select=confidence_value,version"
        f"&order=version.desc"
        f"&limit=1",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        raw_confidence = float(data[0]["confidence_value"])
        # Issue #566: Validate confidence from DB is in valid range
        confidence = max(0.0, min(1.0, raw_confidence))
        return confidence, int(data[0]["version"])

    return 0.0, 0


async def get_current_fatigue(idea_id: str) -> tuple[float, int]:
    """
    Get current fatigue value and version for an idea.

    MVP: fatigue_value = exposure count (number of outcomes processed)
    Returns (fatigue_value, version) or (0.0, 0) if no history
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/fatigue_state_versions"
        f"?idea_id=eq.{idea_id}"
        f"&select=fatigue_value,version"
        f"&order=version.desc"
        f"&limit=1",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        raw_fatigue = float(data[0]["fatigue_value"])
        # Issue #566: Validate fatigue from DB is non-negative
        fatigue = max(0.0, raw_fatigue)
        return fatigue, int(data[0]["version"])

    return 0.0, 0


async def get_recent_outcomes_for_idea(idea_id: str, limit: int = 10) -> list:
    """Get recent outcomes for idea to check death conditions"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Get outcomes via decomposed_creatives
    response = await client.get(
        f"{rest_url}/decomposed_creatives?idea_id=eq.{idea_id}&select=creative_id",
        headers=headers,
    )
    response.raise_for_status()
    creatives = response.json()

    if not creatives:
        return []

    creative_ids = [c["creative_id"] for c in creatives if c.get("creative_id")]
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
        headers=headers,
    )
    response.raise_for_status()
    return cast(list[Any], response.json())


def calculate_confidence_delta(cpa: float, outcome_date: str, env_ctx: Optional[dict]) -> float:
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
        cpa = outcome.get("cpa")
        if cpa is None:
            continue
        if float(cpa) >= TARGET_CPA:
            consecutive_failures += 1
        else:
            break  # Success breaks the streak

    if was_resurrected and consecutive_failures >= CONSECUTIVE_FAILURES_HARD_DEAD:
        return "hard_dead"
    elif consecutive_failures >= CONSECUTIVE_FAILURES_SOFT_DEAD:
        return "soft_dead"

    return None


async def insert_confidence_version(
    idea_id: str,
    confidence_value: float,
    version: int,
    outcome_id: str,
    change_reason: str = "learning_applied",
) -> dict:
    """Insert new confidence version"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/idea_confidence_versions",
        headers=headers,
        json={
            "idea_id": idea_id,
            "confidence_value": confidence_value,
            "version": version,
            "source_outcome_id": outcome_id,
            "change_reason": change_reason,
        },
    )
    response.raise_for_status()
    return cast(dict[Any, Any], response.json()[0])


async def insert_fatigue_version(
    idea_id: str, fatigue_value: float, version: int, outcome_id: str
) -> dict:
    """
    Insert new fatigue version.

    MVP: fatigue_value = exposure count (incremented by 1 for each outcome)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/fatigue_state_versions",
        headers=headers,
        json={
            "idea_id": idea_id,
            "fatigue_value": fatigue_value,
            "version": version,
            "source_outcome_id": outcome_id,
        },
    )
    response.raise_for_status()
    return cast(dict[Any, Any], response.json()[0])


async def update_idea_death_state(idea_id: str, death_state: str) -> dict:
    """Update idea death state"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/ideas?id=eq.{idea_id}",
        headers=headers,
        json={"death_state": death_state},
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else {}


async def mark_outcome_processed(outcome_id: str) -> None:
    """Mark outcome as processed by learning loop"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/outcome_aggregates?id=eq.{outcome_id}",
        headers=headers,
        json={"learning_applied": True},
    )
    response.raise_for_status()


async def is_outcome_already_processed(outcome_id: str) -> bool:
    """
    Check if outcome was already processed by learning loop.

    Idempotency check: looks for existing confidence_version with this source_outcome_id.
    This prevents duplicate processing on Temporal activity retries.

    Issue #473: Learning Loop idempotency fix.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/idea_confidence_versions?source_outcome_id=eq.{outcome_id}&select=id&limit=1",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return len(data) > 0


async def emit_learning_event(
    idea_id: str,
    outcome_id: str,
    old_confidence: float,
    new_confidence: float,
    delta: float,
    death_state: Optional[str] = None,
) -> None:
    """Emit learning.applied event to event_log"""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "outcome_id": outcome_id,
        "old_confidence": old_confidence,
        "new_confidence": new_confidence,
        "delta": delta,
    }
    if death_state:
        payload["death_state"] = death_state

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/event_log",
        headers=headers,
        json={
            "event_type": "learning.applied",
            "entity_type": "idea",
            "entity_id": idea_id,
            "payload": payload,
        },
    )
    response.raise_for_status()


async def apply_learning_atomic_rpc(
    idea_id: str,
    outcome_id: str,
    new_confidence: float,
    confidence_version: int,
    old_confidence: float,
    delta: float,
    new_fatigue: float,
    fatigue_version: int,
    death_state: Optional[str] = None,
) -> dict:
    """
    Apply learning outcome atomically using RPC.

    Issue #576: All 5 learning operations in single transaction:
    1. INSERT idea_confidence_versions
    2. INSERT fatigue_state_versions
    3. UPDATE ideas.death_state (if applicable)
    4. UPDATE outcome_aggregates.learning_applied
    5. INSERT event_log

    Args:
        idea_id: Idea UUID
        outcome_id: Outcome UUID being processed
        new_confidence: New confidence value
        confidence_version: New version number
        old_confidence: Previous confidence value
        delta: Confidence change
        new_fatigue: New fatigue value
        fatigue_version: New fatigue version number
        death_state: Optional death state to set

    Returns:
        RPC result dict

    Raises:
        SupabaseError: If RPC call fails
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rpc_url = f"{supabase_url}/rest/v1/rpc/apply_learning_atomic"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "p_idea_id": idea_id,
        "p_outcome_id": outcome_id,
        "p_new_confidence": float(new_confidence),
        "p_confidence_version": confidence_version,
        "p_old_confidence": float(old_confidence),
        "p_delta": float(delta),
        "p_new_fatigue": float(new_fatigue),
        "p_fatigue_version": fatigue_version,
        "p_death_state": death_state,
    }

    client = get_http_client()
    response = await client.post(rpc_url, headers=headers, json=payload)
    response.raise_for_status()
    return cast(dict[Any, Any], response.json())


async def process_single_outcome(outcome: dict) -> dict:
    """
    Process a single outcome and apply learning.

    Idempotent - safe to retry. If outcome was already processed,
    returns early with skipped=True.

    Issue #473: Learning Loop idempotency fix.
    Issue #576: Uses atomic RPC for all learning operations.

    Returns dict with result info or error
    """
    outcome_id = outcome["id"]
    creative_id = outcome.get("creative_id")
    cpa = float(outcome["cpa"])
    spend = float(outcome.get("spend") or 0)
    env_ctx = outcome.get("environment_ctx")
    window_end = outcome.get("window_end", datetime.now().isoformat())

    # Idempotency check: skip if already processed (issue #473)
    if await is_outcome_already_processed(outcome_id):
        # Mark as processed in case learning_applied flag wasn't set
        await mark_outcome_processed(outcome_id)
        return {
            "skipped": True,
            "reason": "already_processed",
            "outcome_id": outcome_id,
        }

    # Resolve idea
    idea_id = await resolve_idea_for_outcome(outcome)
    if not idea_id:
        return {"error": f"Could not resolve idea for outcome {outcome_id}"}

    # Get current confidence
    current_confidence, current_version = await get_current_confidence(idea_id)

    # Calculate delta
    delta = calculate_confidence_delta(cpa, window_end, env_ctx)
    new_confidence = current_confidence + delta
    # Clamp confidence to valid range [0.0, 1.0]
    new_confidence = max(0.0, min(1.0, new_confidence))
    new_version = current_version + 1

    # Get current fatigue (issue #237)
    # MVP: fatigue_value = exposure count (incremented by 1 for each outcome)
    current_fatigue, fatigue_version = await get_current_fatigue(idea_id)
    new_fatigue = current_fatigue + 1.0  # Simple exposure count
    # Issue #566: Validate fatigue is non-negative and warn on overflow
    new_fatigue = max(0.0, new_fatigue)
    if new_fatigue > MAX_FATIGUE:
        logger.warning(f"Fatigue overflow for idea {idea_id}: {new_fatigue}")
    new_fatigue_version = fatigue_version + 1

    # Check death conditions
    recent_outcomes = await get_recent_outcomes_for_idea(idea_id)
    death_state = check_death_condition(recent_outcomes)

    # Issue #576: Apply all learning operations atomically via RPC
    # This ensures: confidence + fatigue + death_state + mark_processed + event
    # are all committed together or rolled back together
    await apply_learning_atomic_rpc(
        idea_id=idea_id,
        outcome_id=outcome_id,
        new_confidence=new_confidence,
        confidence_version=new_version,
        old_confidence=current_confidence,
        delta=delta,
        new_fatigue=new_fatigue,
        fatigue_version=new_fatigue_version,
        death_state=death_state,
    )

    # Process component learnings (issue #122)
    component_result = None
    if creative_id:
        try:
            component_result = await process_component_learnings(
                creative_id=creative_id,
                cpa=cpa,
                spend=spend,
                revenue=0,  # Revenue not tracked in outcome_aggregates yet
            )
        except Exception as e:
            component_result = {"error": str(e)}

    # Process premise learnings (issue #167)
    premise_result = None
    if creative_id:
        try:
            premise_result = await process_premise_learning(
                creative_id=creative_id, cpa=cpa, spend=spend, revenue=0
            )
        except Exception as e:
            premise_result = {"error": str(e)}

    # Compute component pair winrate feature (issue #304)
    pair_winrate_result = None
    try:
        pair_winrate_result = await compute_and_store_for_idea(idea_id)
    except Exception as e:
        pair_winrate_result = {"error": str(e)}

    return {
        "idea_id": idea_id,
        "outcome_id": outcome_id,
        "old_confidence": current_confidence,
        "new_confidence": new_confidence,
        "delta": delta,
        "old_fatigue": current_fatigue,
        "new_fatigue": new_fatigue,
        "death_state": death_state,
        "component_learning": component_result,
        "premise_learning": premise_result,
        "pair_winrate": pair_winrate_result,  # Issue #304
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
                elif learn_result.get("skipped"):
                    # Already processed - idempotency check (issue #473)
                    result.skipped_count += 1
                else:
                    result.processed_count += 1
                    result.updated_ideas.append(learn_result["idea_id"])

                    if learn_result.get("death_state"):
                        result.new_deaths.append(
                            {
                                "idea_id": learn_result["idea_id"],
                                "death_state": learn_result["death_state"],
                            }
                        )

                    # Track component learning updates
                    comp_result = learn_result.get("component_learning")
                    if comp_result:
                        if "error" in comp_result:
                            result.errors.append(
                                f"Component learning error: {comp_result['error']}"
                            )
                        elif "errors" in comp_result and comp_result["errors"]:
                            result.errors.extend(comp_result["errors"])
                        if "components_updated" in comp_result:
                            result.component_updates += comp_result["components_updated"]

                    # Track premise learning updates (issue #167)
                    prem_result = learn_result.get("premise_learning")
                    if prem_result:
                        if "error" in prem_result:
                            result.errors.append(f"Premise learning error: {prem_result['error']}")
                        elif "errors" in prem_result and prem_result["errors"]:
                            result.errors.extend(prem_result["errors"])
                        if prem_result.get("premise_updated"):
                            result.premise_updates += 1

                    # Track fatigue versioning updates (issue #237)
                    if learn_result.get("new_fatigue") is not None:
                        result.fatigue_updates += 1

            except Exception as e:
                result.errors.append(f"Error processing outcome {outcome['id']}: {str(e)}")

    except Exception as e:
        result.errors.append(f"Failed to fetch outcomes: {str(e)}")

    return result
