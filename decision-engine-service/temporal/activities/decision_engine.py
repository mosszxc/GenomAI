"""
Decision Engine Activity

Temporal activity that wraps the existing Decision Engine service.
Executes the 4-check wall inline without HTTP overhead.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from temporalio import activity

from temporal.models.decision import DecisionResult, DecisionTrace, CheckResult


@activity.defn
async def make_decision(
    idea_id: str,
    idea: Optional[Dict[str, Any]] = None,
    system_state: Optional[Dict[str, Any]] = None,
    fatigue_state: Optional[Dict[str, Any]] = None,
    death_memory_data: Optional[Dict[str, Any]] = None,
) -> DecisionResult:
    """
    Execute Decision Engine for an idea.

    Wraps existing src/services/decision_engine.make_decision() logic.
    Executes 4 checks in order:
    1. schema_validity - REJECT if invalid
    2. death_memory - REJECT if dead
    3. fatigue_constraint - REJECT if fatigued
    4. risk_budget - DEFER if exceeded

    All pass = APPROVE

    Args:
        idea_id: Idea UUID
        idea: Optional pre-loaded idea (will load from DB if not provided)
        system_state: Optional system state (will load from DB if not provided)
        fatigue_state: Optional fatigue state
        death_memory_data: Optional death memory data

    Returns:
        DecisionResult with decision details and trace
    """
    # Import existing decision engine logic
    from src.services.decision_engine import make_decision as de_make_decision

    # Build input for existing service
    input_data = {
        "idea_id": idea_id,
        "idea": idea,
        "system_state": system_state,
        "fatigue_state": fatigue_state,
        "death_memory": death_memory_data,
    }

    # Execute decision engine
    start_time = datetime.utcnow()
    result = await de_make_decision(input_data)
    execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Convert to Temporal models
    decision_data = result["decision"]
    trace_data = result["decision_trace"]

    # Build check results
    check_results = [
        CheckResult(
            check_name=check["check_name"],
            order=check["order"],
            passed=check["result"] == "PASSED",
            details=check.get("details"),
        )
        for check in trace_data["checks"]
    ]

    # Build trace
    trace = DecisionTrace(
        id=trace_data["id"],
        decision_id=decision_data["decision_id"],
        checks=check_results,
        execution_time_ms=execution_time,
        created_at=datetime.fromisoformat(trace_data["created_at"]),
    )

    # Build result
    return DecisionResult(
        decision_id=decision_data["decision_id"],
        idea_id=decision_data["idea_id"],
        decision_type=decision_data["decision_type"].upper(),
        decision_reason=decision_data["decision_reason"],
        passed_checks=decision_data["passed_checks"],
        failed_checks=decision_data["failed_checks"],
        trace=trace,
        timestamp=datetime.fromisoformat(decision_data["timestamp"]),
    )
