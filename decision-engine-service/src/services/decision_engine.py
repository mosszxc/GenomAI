"""
Decision Engine — Core decision logic
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from src.services.supabase import (
    load_idea,
    load_system_state,
    save_decision_with_trace,
    get_existing_decision,
    get_decision_trace,
)
from src.checks import schema_validity, death_memory, fatigue_constraint, risk_budget
from src.utils.errors import IdeaNotFoundError

# Current decision epoch (MVP: fixed at 1)
CURRENT_DECISION_EPOCH = 1

# Decision modes
MODE_STRICT = "strict"
MODE_ADVISORY = "advisory"

# Checks that generate warnings in advisory mode (instead of reject)
ADVISORY_WARNING_CHECKS = {"death_memory", "fatigue_constraint"}


def _format_existing_decision(
    existing_decision: dict, existing_trace: dict | None, idea: dict
) -> dict:
    """
    Format existing decision into the same response structure as new decisions.

    Args:
        existing_decision: Existing decision from database
        existing_trace: Existing decision trace (may be None)
        idea: The idea object

    Returns:
        dict: Formatted decision response matching new decision structure
    """
    decision_id = existing_decision["id"]
    decision_type = existing_decision["decision"]
    timestamp = existing_decision.get("created_at", "")

    # Parse trace to extract check results
    passed_checks = []
    failed_checks = []
    failed_check = None

    if existing_trace and existing_trace.get("checks"):
        checks = existing_trace["checks"]
        for check in checks:
            if check.get("result") == "PASSED":
                passed_checks.append(check.get("check_name", ""))
            else:
                failed_checks.append(check.get("check_name", ""))
                if not failed_check:
                    failed_check = check.get("check_name")

    # Determine decision reason
    if decision_type == "approve":
        decision_reason = "all_checks_passed"
    else:
        decision_reason = failed_check or "unknown"

    return {
        "decision": {
            "decision_id": decision_id,
            "idea_id": idea["id"],
            "decision_type": decision_type,
            "decision_reason": decision_reason,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "failed_check": failed_check,
            "dominant_constraint": failed_check,
            "cluster_at_decision": idea.get("active_cluster_id"),
            "horizon": idea.get("horizon"),
            "system_state": "exploit",
            "policy_version": "v1.0",
            "timestamp": timestamp,
            "idempotent": True,  # Flag indicating this is a cached result
        },
        "decision_trace": existing_trace
        or {
            "id": None,
            "decision_id": decision_id,
            "checks": [],
            "result": decision_type,
            "created_at": timestamp,
        },
    }


def _create_warning(check_result: dict, severity: str = "medium") -> dict:
    """
    Create warning object from failed check result.

    Args:
        check_result: Failed check result
        severity: Warning severity (low, medium, high)

    Returns:
        dict: Warning object
    """
    check_name = check_result["name"]
    details = check_result.get("details", {})

    # Generate human-readable message based on check type
    if check_name == "death_memory":
        death_state = details.get("death_state", "unknown")
        message = f"Idea marked as dead (state: {death_state})"
    elif check_name == "fatigue_constraint":
        message = "High fatigue detected for this angle"
    else:
        message = f"Check {check_name} failed"

    return {
        "check": check_name,
        "message": message,
        "severity": severity,
        "details": details,
    }


async def make_decision(input_data: dict) -> dict:
    """
    Make decision for an idea

    Args:
        input_data: Input data with idea_id, idea, system_state, fatigue_state, death_memory, mode

    Returns:
        dict: Decision result with decision and decision_trace

    Raises:
        IdeaNotFoundError: If idea not found
    """
    idea_id = input_data.get("idea_id")
    idea = input_data.get("idea")
    system_state = input_data.get("system_state")
    fatigue_state = input_data.get("fatigue_state")
    death_memory_data = input_data.get("death_memory")
    mode = input_data.get("mode", MODE_STRICT)

    # Load idea if not provided
    if not idea and idea_id:
        idea = await load_idea(idea_id)
        if not idea:
            raise IdeaNotFoundError(idea_id)

    if not idea:
        raise IdeaNotFoundError("No idea provided")

    # IDEMPOTENCY GUARD: Check if decision already exists for this idea+epoch
    # Note: In advisory mode, we still check idempotency but only for the same mode
    existing_decision = await get_existing_decision(idea["id"], CURRENT_DECISION_EPOCH)
    if existing_decision:
        # Return existing decision instead of creating duplicate
        existing_trace = await get_decision_trace(existing_decision["id"])
        return _format_existing_decision(existing_decision, existing_trace, idea)

    # Load system state if not provided
    if not system_state:
        system_state = await load_system_state()

    # Execute checks in fixed order
    check_results: list[dict] = []
    warnings: list[dict] = []
    is_advisory = mode == MODE_ADVISORY

    # CHECK 1: Schema Validity (always blocking)
    schema_check = schema_validity(idea)
    check_results.append(schema_check)
    if schema_check["result"] == "FAILED":
        return await _create_decision(idea, "reject", check_results, "schema_invalid", warnings)

    # CHECK 2: Death Memory
    death_check = death_memory(idea, death_memory_data)
    check_results.append(death_check)
    if death_check["result"] == "FAILED":
        if is_advisory:
            # In advisory mode, convert to warning
            warnings.append(_create_warning(death_check, severity="high"))
        else:
            return await _create_decision(idea, "reject", check_results, "idea_dead", warnings)

    # CHECK 3: Fatigue Constraint (MVP: заглушка)
    fatigue_check = fatigue_constraint(idea, fatigue_state)
    check_results.append(fatigue_check)
    if fatigue_check["result"] == "FAILED":
        if is_advisory:
            # In advisory mode, convert to warning
            warnings.append(_create_warning(fatigue_check, severity="medium"))
        else:
            return await _create_decision(
                idea, "reject", check_results, "fatigue_constraint", warnings
            )

    # CHECK 4: Risk Budget (always blocking)
    risk_check = risk_budget(idea, system_state)
    check_results.append(risk_check)
    if risk_check["result"] == "FAILED":
        return await _create_decision(
            idea, "defer", check_results, "risk_budget_exceeded", warnings
        )

    # All checks passed or only warnings in advisory mode
    if warnings:
        return await _create_decision(idea, "approve_with_warnings", check_results, None, warnings)

    return await _create_decision(idea, "approve", check_results, None, warnings)


async def _create_decision(
    idea: dict,
    decision_type: str,
    check_results: list,
    failed_check: str | None,
    warnings: list | None = None,
) -> dict:
    """
    Create Decision and Decision Trace

    Args:
        idea: Idea object
        decision_type: Decision type (approve, reject, defer, approve_with_warnings)
        check_results: List of check results
        failed_check: Name of failed check (if any)
        warnings: List of warnings (for advisory mode)

    Returns:
        dict: Decision result with decision and decision_trace
    """
    decision_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    warnings = warnings or []

    # Create Decision
    decision = {
        "id": decision_id,
        "idea_id": idea["id"],
        "decision": decision_type,
        "decision_epoch": CURRENT_DECISION_EPOCH,
        "created_at": timestamp,
    }

    # Create Decision Trace
    decision_trace = {
        "id": str(uuid.uuid4()),
        "decision_id": decision_id,
        "checks": [
            {
                "check_name": check["name"],
                "order": index + 1,
                "result": check["result"],
                "details": check.get("details", {}),
            }
            for index, check in enumerate(check_results)
        ],
        "result": decision_type,
        "created_at": timestamp,
    }

    # Include warnings in trace if present
    if warnings:
        decision_trace["warnings"] = warnings

    # Save to Supabase atomically (both or none via RPC transaction)
    await save_decision_with_trace(decision, decision_trace)

    # Determine decision reason
    if decision_type == "approve_with_warnings":
        decision_reason = "approved_with_warnings"
    elif failed_check:
        decision_reason = failed_check
    else:
        decision_reason = "all_checks_passed"

    # Return response
    response: dict[str, Any] = {
        "decision": {
            "decision_id": decision_id,
            "idea_id": idea["id"],
            "decision_type": decision_type,
            "decision_reason": decision_reason,
            "passed_checks": [c["name"] for c in check_results if c["result"] == "PASSED"],
            "failed_checks": [c["name"] for c in check_results if c["result"] == "FAILED"],
            "failed_check": failed_check,
            "dominant_constraint": failed_check,
            "cluster_at_decision": idea.get("active_cluster_id"),
            "horizon": idea.get("horizon"),
            "system_state": "exploit",  # MVP: фиксированное значение
            "policy_version": "v1.0",
            "timestamp": timestamp,
        },
        "decision_trace": {
            "id": decision_trace["id"],
            "decision_id": decision_id,
            "checks": decision_trace["checks"],
            "result": decision_type,
            "created_at": timestamp,
        },
    }

    # Add warnings to response if present
    if warnings:
        response["warnings"] = warnings

    return response
