"""
Maintenance Workflow

Periodic maintenance tasks for GenomAI.
Replaces n8n workflow H1uuOanSy627H4kg (Pipeline Health Monitor).

Tasks:
- Reset stale buyer states (awaiting_* for > 6 hours)
- Clean up expired recommendations
- Verify data integrity
- Staleness detection (Inspiration System)

Schedule: Every 6 hours
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.maintenance import (
        reset_stale_buyer_states,
        expire_old_recommendations,
        mark_stuck_transcriptions_failed,
        archive_failed_creatives,
        check_data_integrity,
        emit_maintenance_event,
        check_staleness,
    )


@dataclass
class MaintenanceInput:
    """Input for maintenance workflow"""

    # Buyer state timeout in hours
    buyer_state_timeout_hours: int = 6
    # Recommendation expiry in days
    recommendation_expiry_days: int = 7
    # Stuck transcription timeout in minutes
    stuck_transcription_timeout_minutes: int = 10
    # Failed creative retention before archival in days
    failed_creative_retention_days: int = 7
    # Run data integrity checks
    run_integrity_checks: bool = True
    # Run staleness detection (Inspiration System)
    run_staleness_check: bool = True


@dataclass
class MaintenanceResult:
    """Result of maintenance workflow"""

    stale_buyers_reset: int
    recommendations_expired: int
    stuck_transcriptions_failed: int
    failed_creatives_archived: int
    integrity_issues: List[str]
    completed_at: str
    # Staleness detection results
    staleness_score: Optional[float] = None
    is_stale: Optional[bool] = None
    staleness_action: Optional[str] = None


@workflow.defn
class MaintenanceWorkflow:
    """
    Workflow for periodic maintenance tasks.

    Flow:
    1. Reset stale buyer states (stuck in awaiting_* for > 6 hours)
    2. Expire old recommendations
    3. Mark stuck transcriptions as failed
    4. Archive old failed creatives
    5. Run data integrity checks
    6. Check system staleness (Inspiration System)
    7. Emit maintenance event
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
            stuck_transcriptions_failed=0,
            failed_creatives_archived=0,
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

        # Step 3: Mark stuck transcriptions as failed
        try:
            stuck_count = await workflow.execute_activity(
                mark_stuck_transcriptions_failed,
                input.stuck_transcription_timeout_minutes,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            result.stuck_transcriptions_failed = stuck_count
            if stuck_count > 0:
                workflow.logger.warning(f"Marked {stuck_count} stuck transcriptions as failed")
            else:
                workflow.logger.info("No stuck transcriptions found")
        except Exception as e:
            workflow.logger.error(f"Failed to mark stuck transcriptions: {e}")
            result.integrity_issues.append(f"Stuck transcription check failed: {e}")

        # Step 4: Archive old failed creatives
        try:
            archived_count = await workflow.execute_activity(
                archive_failed_creatives,
                input.failed_creative_retention_days,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy,
            )
            result.failed_creatives_archived = archived_count
            if archived_count > 0:
                workflow.logger.info(f"Archived {archived_count} failed creatives")
            else:
                workflow.logger.info("No old failed creatives to archive")
        except Exception as e:
            workflow.logger.error(f"Failed to archive failed creatives: {e}")
            result.integrity_issues.append(f"Failed creative archival failed: {e}")

        # Step 5: Data integrity checks (optional)
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

        # Step 6: Staleness detection (Inspiration System)
        if input.run_staleness_check:
            try:
                staleness_result = await workflow.execute_activity(
                    check_staleness,
                    args=[None, None],  # Global check (no avatar/geo filter)
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy,
                )
                result.staleness_score = staleness_result.get("metrics", {}).get(
                    "staleness_score"
                )
                result.is_stale = staleness_result.get("is_stale", False)
                result.staleness_action = staleness_result.get("recommended_action")

                if result.is_stale:
                    workflow.logger.warning(
                        f"System is STALE! Score: {result.staleness_score:.2f}, "
                        f"action: {result.staleness_action}"
                    )
                else:
                    workflow.logger.info(
                        f"System healthy. Staleness score: {result.staleness_score:.2f}"
                    )
            except Exception as e:
                workflow.logger.error(f"Staleness check failed: {e}")
                result.integrity_issues.append(f"Staleness check error: {e}")

        # Step 7: Emit maintenance event
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
            f"expired={result.recommendations_expired}, stuck={result.stuck_transcriptions_failed}, "
            f"archived={result.failed_creatives_archived}, "
            f"issues={len(result.integrity_issues)}, stale={result.is_stale}"
        )

        return result
