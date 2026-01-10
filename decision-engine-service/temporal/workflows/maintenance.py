"""
Maintenance Workflow

Periodic maintenance tasks for GenomAI.
Replaces n8n workflow H1uuOanSy627H4kg (Pipeline Health Monitor).

Tasks:
- Reset stale buyer states (awaiting_* for > 6 hours)
- Clean up expired recommendations
- Verify data integrity

Schedule: Every 6 hours
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.maintenance import (
        reset_stale_buyer_states,
        expire_old_recommendations,
        check_data_integrity,
        emit_maintenance_event,
    )


@dataclass
class MaintenanceInput:
    """Input for maintenance workflow"""

    # Buyer state timeout in hours
    buyer_state_timeout_hours: int = 6
    # Recommendation expiry in days
    recommendation_expiry_days: int = 7
    # Run data integrity checks
    run_integrity_checks: bool = True


@dataclass
class MaintenanceResult:
    """Result of maintenance workflow"""

    stale_buyers_reset: int
    recommendations_expired: int
    integrity_issues: List[str]
    completed_at: str


@workflow.defn
class MaintenanceWorkflow:
    """
    Workflow for periodic maintenance tasks.

    Flow:
    1. Reset stale buyer states (stuck in awaiting_* for > 6 hours)
    2. Expire old recommendations
    3. Run data integrity checks
    4. Emit maintenance event
    """

    @workflow.run
    async def run(self, input: MaintenanceInput) -> MaintenanceResult:
        workflow.logger.info("Starting maintenance workflow")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
        )

        result = MaintenanceResult(
            stale_buyers_reset=0,
            recommendations_expired=0,
            integrity_issues=[],
            completed_at="",
        )

        # Step 1: Reset stale buyer states
        try:
            reset_count = await workflow.execute_activity(
                reset_stale_buyer_states,
                input.buyer_state_timeout_hours,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            result.stale_buyers_reset = reset_count
            workflow.logger.info(f"Reset {reset_count} stale buyer states")
        except Exception as e:
            workflow.logger.error(f"Failed to reset buyer states: {e}")
            result.integrity_issues.append(f"Buyer state reset failed: {e}")

        # Step 2: Expire old recommendations
        try:
            expired_count = await workflow.execute_activity(
                expire_old_recommendations,
                input.recommendation_expiry_days,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            result.recommendations_expired = expired_count
            workflow.logger.info(f"Expired {expired_count} old recommendations")
        except Exception as e:
            workflow.logger.error(f"Failed to expire recommendations: {e}")
            result.integrity_issues.append(f"Recommendation expiry failed: {e}")

        # Step 3: Data integrity checks (optional)
        if input.run_integrity_checks:
            try:
                issues = await workflow.execute_activity(
                    check_data_integrity,
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy,
                )
                result.integrity_issues.extend(issues)
                if issues:
                    workflow.logger.warning(f"Found {len(issues)} integrity issues")
                else:
                    workflow.logger.info("Data integrity check passed")
            except Exception as e:
                workflow.logger.error(f"Integrity check failed: {e}")
                result.integrity_issues.append(f"Integrity check error: {e}")

        # Step 4: Emit maintenance event
        result.completed_at = workflow.now().isoformat()

        await workflow.execute_activity(
            emit_maintenance_event,
            args=[
                result.stale_buyers_reset,
                result.recommendations_expired,
                len(result.integrity_issues),
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        workflow.logger.info(
            f"Maintenance complete: reset={result.stale_buyers_reset}, "
            f"expired={result.recommendations_expired}, issues={len(result.integrity_issues)}"
        )

        return result
