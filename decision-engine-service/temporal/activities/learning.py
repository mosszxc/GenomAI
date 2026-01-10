"""
Learning Activities

Activities for the Learning Loop:
- Process learning batch (wraps learning_loop.py)
- Update confidence versions
- Update fatigue state versions
- Check death conditions

Based on src/services/learning_loop.py
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from temporalio import activity

from temporal.config import settings


@dataclass
class ProcessLearningInput:
    """Input for process_learning activity"""

    batch_limit: int = 100


@dataclass
class ProcessLearningOutput:
    """Output from process_learning activity"""

    processed_count: int
    updated_ideas: list[str]
    new_deaths: list[dict]
    component_updates: int
    premise_updates: int
    fatigue_updates: int
    errors: list[str]


@activity.defn
async def process_learning_batch(input: ProcessLearningInput) -> ProcessLearningOutput:
    """
    Process a batch of unprocessed outcomes through the learning loop.

    This wraps the existing learning_loop.py logic.
    Idempotent - safe to retry.

    Args:
        input: batch_limit for number of outcomes to process

    Returns:
        ProcessLearningOutput with results
    """
    activity.logger.info(f"Processing learning batch (limit: {input.batch_limit})")

    # Import here to avoid circular imports
    from src.services.learning_loop import process_learning_batch

    try:
        result = await process_learning_batch(limit=input.batch_limit)

        activity.logger.info(
            f"Learning batch complete: "
            f"{result.processed_count} processed, "
            f"{len(result.new_deaths)} deaths, "
            f"{len(result.errors)} errors"
        )

        return ProcessLearningOutput(
            processed_count=result.processed_count,
            updated_ideas=result.updated_ideas,
            new_deaths=result.new_deaths,
            component_updates=result.component_updates,
            premise_updates=result.premise_updates,
            fatigue_updates=result.fatigue_updates,
            errors=result.errors,
        )

    except Exception as e:
        activity.logger.error(f"Learning batch error: {str(e)}")
        return ProcessLearningOutput(
            processed_count=0,
            updated_ideas=[],
            new_deaths=[],
            component_updates=0,
            premise_updates=0,
            fatigue_updates=0,
            errors=[str(e)],
        )


@dataclass
class GetUnprocessedOutcomesInput:
    """Input for get_unprocessed_outcomes activity"""

    limit: int = 100


@dataclass
class OutcomeInfo:
    """Info about an outcome to process"""

    id: str
    creative_id: str
    cpa: float
    spend: float
    environment_ctx: Optional[dict]
    window_end: str
    decision_id: Optional[str]


@dataclass
class GetUnprocessedOutcomesOutput:
    """Output from get_unprocessed_outcomes activity"""

    outcomes: list[OutcomeInfo]
    total: int


@activity.defn
async def get_unprocessed_outcomes(
    input: GetUnprocessedOutcomesInput,
) -> GetUnprocessedOutcomesOutput:
    """
    Get outcomes that haven't been processed by learning loop.

    Fetches from outcome_aggregates where learning_applied = false.

    Args:
        input: limit for batch size

    Returns:
        GetUnprocessedOutcomesOutput with outcome list
    """
    activity.logger.info(f"Fetching unprocessed outcomes (limit: {input.limit})")

    # Import here to avoid circular imports
    from src.services.learning_loop import fetch_unprocessed_outcomes

    try:
        outcomes = await fetch_unprocessed_outcomes(limit=input.limit)

        result = [
            OutcomeInfo(
                id=o["id"],
                creative_id=o.get("creative_id", ""),
                cpa=float(o.get("cpa", 0) or 0),
                spend=float(o.get("spend", 0) or 0),
                environment_ctx=o.get("environment_ctx"),
                window_end=o.get("window_end", ""),
                decision_id=o.get("decision_id"),
            )
            for o in outcomes
        ]

        activity.logger.info(f"Found {len(result)} unprocessed outcomes")

        return GetUnprocessedOutcomesOutput(outcomes=result, total=len(result))

    except Exception as e:
        activity.logger.error(f"Error fetching outcomes: {str(e)}")
        return GetUnprocessedOutcomesOutput(outcomes=[], total=0)


@dataclass
class ProcessSingleOutcomeInput:
    """Input for process_single_outcome activity"""

    outcome_id: str
    creative_id: str
    cpa: float
    spend: float
    environment_ctx: Optional[dict]
    window_end: str


@dataclass
class ProcessSingleOutcomeOutput:
    """Output from process_single_outcome activity"""

    success: bool
    idea_id: Optional[str] = None
    old_confidence: Optional[float] = None
    new_confidence: Optional[float] = None
    delta: Optional[float] = None
    death_state: Optional[str] = None
    error: Optional[str] = None


@activity.defn
async def process_single_outcome(
    input: ProcessSingleOutcomeInput,
) -> ProcessSingleOutcomeOutput:
    """
    Process a single outcome through the learning loop.

    More granular than batch processing - allows workflow to handle errors individually.

    Args:
        input: outcome details

    Returns:
        ProcessSingleOutcomeOutput with result
    """
    activity.logger.info(f"Processing outcome: {input.outcome_id}")

    # Import here to avoid circular imports
    from src.services.learning_loop import process_single_outcome

    outcome = {
        "id": input.outcome_id,
        "creative_id": input.creative_id,
        "cpa": input.cpa,
        "spend": input.spend,
        "environment_ctx": input.environment_ctx,
        "window_end": input.window_end,
    }

    try:
        result = await process_single_outcome(outcome)

        if "error" in result:
            activity.logger.warning(f"Outcome processing failed: {result['error']}")
            return ProcessSingleOutcomeOutput(success=False, error=result["error"])

        activity.logger.info(
            f"Outcome processed: idea={result.get('idea_id')}, "
            f"confidence delta={result.get('delta')}"
        )

        return ProcessSingleOutcomeOutput(
            success=True,
            idea_id=result.get("idea_id"),
            old_confidence=result.get("old_confidence"),
            new_confidence=result.get("new_confidence"),
            delta=result.get("delta"),
            death_state=result.get("death_state"),
        )

    except Exception as e:
        activity.logger.error(f"Outcome processing error: {str(e)}")
        return ProcessSingleOutcomeOutput(success=False, error=str(e))


@dataclass
class CheckDeathConditionsInput:
    """Input for check_death_conditions activity"""

    idea_id: str


@dataclass
class CheckDeathConditionsOutput:
    """Output from check_death_conditions activity"""

    should_die: bool
    death_state: Optional[str] = None  # soft_dead, hard_dead
    consecutive_failures: int = 0


@activity.defn
async def check_death_conditions(
    input: CheckDeathConditionsInput,
) -> CheckDeathConditionsOutput:
    """
    Check if an idea should be marked as dead.

    Based on consecutive failures threshold.

    Args:
        input: idea_id to check

    Returns:
        CheckDeathConditionsOutput with result
    """
    activity.logger.info(f"Checking death conditions for idea: {input.idea_id}")

    # Import here to avoid circular imports
    from src.services.learning_loop import (
        get_recent_outcomes_for_idea,
        check_death_condition,
    )

    try:
        outcomes = await get_recent_outcomes_for_idea(input.idea_id)
        death_state = check_death_condition(outcomes)

        # Count consecutive failures for reporting
        consecutive = 0
        for o in outcomes:
            cpa = o.get("cpa")
            if cpa is None:
                continue
            if float(cpa) >= 20.0:  # TARGET_CPA
                consecutive += 1
            else:
                break

        if death_state:
            activity.logger.info(
                f"Idea {input.idea_id} should die: {death_state} "
                f"({consecutive} consecutive failures)"
            )
        else:
            activity.logger.info(
                f"Idea {input.idea_id} is healthy ({consecutive} consecutive failures)"
            )

        return CheckDeathConditionsOutput(
            should_die=death_state is not None,
            death_state=death_state,
            consecutive_failures=consecutive,
        )

    except Exception as e:
        activity.logger.error(f"Error checking death conditions: {str(e)}")
        return CheckDeathConditionsOutput(should_die=False, consecutive_failures=0)


@dataclass
class EmitLearningEventInput:
    """Input for emit_learning_event activity"""

    event_type: str  # learning.applied, learning.death, etc.
    idea_id: str
    payload: dict


@activity.defn
async def emit_learning_event(input: EmitLearningEventInput) -> bool:
    """
    Emit learning-related event to event_log.

    Used for observability and audit trail.

    Args:
        input: event details

    Returns:
        True if successful
    """
    activity.logger.info(f"Emitting learning event: {input.event_type}")

    import httpx

    SCHEMA = "genomai"

    headers = {
        "apikey": settings.supabase.service_role_key,
        "Authorization": f"Bearer {settings.supabase.service_role_key}",
        "Accept-Profile": SCHEMA,
        "Content-Profile": SCHEMA,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    url = f"{settings.supabase.url}/rest/v1/event_log"

    payload = {
        "event_type": input.event_type,
        "entity_type": "idea",
        "entity_id": input.idea_id,
        "payload": input.payload,
        "occurred_at": datetime.now().isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        activity.logger.info(f"Learning event emitted: {input.event_type}")
        return True

    except Exception as e:
        activity.logger.error(f"Failed to emit learning event: {str(e)}")
        return False
