"""
Maintenance Workflow

Periodic maintenance tasks for GenomAI.
Replaces n8n workflow H1uuOanSy627H4kg (Pipeline Health Monitor).

Tasks:
- Reset stale buyer states (awaiting_* for > 6 hours)
- Clean up expired recommendations
- Verify data integrity
- Staleness detection (Inspiration System)
- Data cleanup (Hygiene Agent)

Schedule: Every 6 hours
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict

from temporalio import workflow
from temporalio.common import RetryPolicy, WorkflowIDReusePolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.maintenance import (
        reset_stale_buyer_states,
        expire_old_recommendations,
        mark_stuck_transcriptions_failed,
        archive_failed_creatives,
        check_data_integrity,
        cleanup_orphaned_hypotheses,
        emit_maintenance_event,
        check_staleness,
        release_orphaned_agent_tasks,
        find_stuck_creatives,
    )
    from temporal.activities.hygiene_cleanup import (
        run_all_cleanup,
        retry_failed_hypotheses,
        cleanup_exhausted_hypotheses,
    )
    from temporal.workflows.creative_pipeline import CreativePipelineWorkflow
    from temporal.models.creative import CreativeInput


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
    # Run data cleanup (Hygiene Agent)
    run_cleanup: bool = True
    # Cleanup retention periods
    import_queue_retention_days: int = 7
    knowledge_retention_days: int = 30
    buyer_states_retention_days: int = 30
    staleness_archive_days: int = 90
    # Retry failed hypotheses (Issue #313)
    run_hypothesis_retry: bool = True
    # Max retry attempts for hypotheses
    hypothesis_max_retries: int = 3
    # Agent task orphan detection (Multi-Agent Phase 2, Issue #350)
    run_orphan_detection: bool = True
    # Timeout for agent heartbeats in minutes
    agent_heartbeat_timeout_minutes: int = 10
    # Stuck creatives recovery (Issue #398)
    run_stuck_recovery: bool = True
    # Timeout before considering transcription stuck (minutes)
    stuck_transcription_timeout_minutes: int = 5
    # Timeout before considering decomposition stuck (minutes)
    stuck_decomposition_timeout_minutes: int = 30
    # Orphaned hypotheses cleanup (Issue #475)
    run_orphan_hypothesis_cleanup: bool = True


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
    # Cleanup stats (Hygiene Agent)
    cleanup_stats: Optional[Dict[str, int]] = None
    # Hypothesis retry results (Issue #313)
    hypotheses_retried: int = 0
    hypotheses_retry_succeeded: int = 0
    hypotheses_abandoned: int = 0
    # Agent task orphan detection (Multi-Agent Phase 2, Issue #350)
    orphaned_tasks_released: int = 0
    # Stuck creatives recovery (Issue #398)
    stuck_creatives_recovered: int = 0
    stuck_creatives_failed: int = 0
    # Orphaned hypotheses cleanup (Issue #475)
    orphaned_hypotheses_deleted: int = 0


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
    7. Data cleanup (Hygiene Agent)
    8. Emit maintenance event
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
                workflow.logger.warning(
                    f"Marked {stuck_count} stuck transcriptions as failed"
                )
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

        # Step 5b: Cleanup orphaned hypotheses (Issue #475)
        if input.run_orphan_hypothesis_cleanup:
            try:
                deleted_count = await workflow.execute_activity(
                    cleanup_orphaned_hypotheses,
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy,
                )
                result.orphaned_hypotheses_deleted = deleted_count
                if deleted_count > 0:
                    workflow.logger.info(f"Deleted {deleted_count} orphaned hypotheses")
            except Exception as e:
                workflow.logger.error(f"Orphan hypothesis cleanup failed: {e}")
                result.integrity_issues.append(f"Orphan hypothesis cleanup error: {e}")

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

        # Step 7: Data cleanup (Hygiene Agent)
        if input.run_cleanup:
            try:
                cleanup_stats = await workflow.execute_activity(
                    run_all_cleanup,
                    args=[
                        input.import_queue_retention_days,
                        input.knowledge_retention_days,
                        input.buyer_states_retention_days,
                        input.staleness_archive_days,
                    ],
                    start_to_close_timeout=timedelta(seconds=180),
                    retry_policy=retry_policy,
                )
                result.cleanup_stats = cleanup_stats
                total_cleaned = sum(cleanup_stats.values())
                if total_cleaned > 0:
                    workflow.logger.info(
                        f"Cleaned {total_cleaned} records: {cleanup_stats}"
                    )
                else:
                    workflow.logger.info("No records to clean")
            except Exception as e:
                workflow.logger.error(f"Cleanup failed: {e}")
                result.integrity_issues.append(f"Cleanup error: {e}")

        # Step 8: Retry failed hypotheses (Issue #313)
        if input.run_hypothesis_retry:
            try:
                retry_stats = await workflow.execute_activity(
                    retry_failed_hypotheses,
                    input.hypothesis_max_retries,
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy,
                )
                result.hypotheses_retried = retry_stats.get("retried", 0)
                result.hypotheses_retry_succeeded = retry_stats.get("succeeded", 0)

                if result.hypotheses_retried > 0:
                    workflow.logger.info(
                        f"Hypothesis retry: {result.hypotheses_retry_succeeded}/{result.hypotheses_retried} succeeded"
                    )
            except Exception as e:
                workflow.logger.error(f"Hypothesis retry failed: {e}")
                result.integrity_issues.append(f"Hypothesis retry error: {e}")

            # Cleanup exhausted hypotheses
            try:
                abandoned_count = await workflow.execute_activity(
                    cleanup_exhausted_hypotheses,
                    7,  # retention_days
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
                result.hypotheses_abandoned = abandoned_count
                if abandoned_count > 0:
                    workflow.logger.info(
                        f"Marked {abandoned_count} exhausted hypotheses as abandoned"
                    )
            except Exception as e:
                workflow.logger.error(f"Hypothesis cleanup failed: {e}")
                result.integrity_issues.append(f"Hypothesis cleanup error: {e}")

        # Step 9: Agent task orphan detection (Multi-Agent Phase 2, Issue #350)
        if input.run_orphan_detection:
            try:
                released_count = await workflow.execute_activity(
                    release_orphaned_agent_tasks,
                    input.agent_heartbeat_timeout_minutes,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
                result.orphaned_tasks_released = released_count
                if released_count > 0:
                    workflow.logger.warning(
                        f"Released {released_count} orphaned agent tasks"
                    )
            except Exception as e:
                workflow.logger.error(f"Orphan detection failed: {e}")
                result.integrity_issues.append(f"Orphan detection error: {e}")

        # Step 10: Recover stuck creatives (Issue #398)
        if input.run_stuck_recovery:
            try:
                stuck_creatives = await workflow.execute_activity(
                    find_stuck_creatives,
                    args=[
                        input.stuck_transcription_timeout_minutes,
                        input.stuck_decomposition_timeout_minutes,
                    ],
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy,
                )

                if stuck_creatives:
                    workflow.logger.warning(
                        f"Found {len(stuck_creatives)} stuck creatives, starting recovery"
                    )

                    # Start recovery workflows for stuck creatives
                    # Use ALLOW_DUPLICATE_FAILED_ONLY to only restart if previous failed
                    for stuck in stuck_creatives:
                        try:
                            # Use same ID as original workflow to avoid duplicates
                            # ALLOW_DUPLICATE_FAILED_ONLY ensures we only restart
                            # if previous workflow FAILED/TERMINATED, not if still running
                            await workflow.start_child_workflow(
                                CreativePipelineWorkflow.run,
                                CreativeInput(
                                    creative_id=stuck["creative_id"],
                                    buyer_id=stuck.get("buyer_id"),
                                    source_type="recovery",
                                ),
                                id=f"creative-pipeline-{stuck['creative_id']}",
                                task_queue="creative-pipeline",
                                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                            )
                            result.stuck_creatives_recovered += 1
                            workflow.logger.info(
                                f"Started recovery for creative {stuck['creative_id'][:8]} "
                                f"(stuck_reason={stuck['stuck_reason']})"
                            )
                        except workflow.ChildWorkflowError as e:
                            # Check if workflow already running (expected with ALLOW_DUPLICATE_FAILED_ONLY)
                            if "already started" in str(e).lower():
                                workflow.logger.info(
                                    f"Creative {stuck['creative_id'][:8]} workflow already running, skipping recovery"
                                )
                            else:
                                result.stuck_creatives_failed += 1
                                workflow.logger.error(
                                    f"Failed to recover creative {stuck['creative_id'][:8]}: {e}"
                                )
                        except Exception as e:
                            # WorkflowAlreadyStartedError might also be raised
                            if (
                                "already started" in str(e).lower()
                                or "already running" in str(e).lower()
                            ):
                                workflow.logger.info(
                                    f"Creative {stuck['creative_id'][:8]} workflow already running, skipping recovery"
                                )
                            else:
                                result.stuck_creatives_failed += 1
                                workflow.logger.error(
                                    f"Failed to recover creative {stuck['creative_id'][:8]}: {e}"
                                )

                    workflow.logger.info(
                        f"Recovery complete: {result.stuck_creatives_recovered} recovered, "
                        f"{result.stuck_creatives_failed} failed"
                    )
                else:
                    workflow.logger.info("No stuck creatives to recover")

            except Exception as e:
                workflow.logger.error(f"Stuck creatives recovery failed: {e}")
                result.integrity_issues.append(f"Stuck recovery error: {e}")

        # Step 11: Emit maintenance event
        result.completed_at = workflow.now().isoformat()

        await workflow.execute_activity(
            emit_maintenance_event,
            args=[
                result.stale_buyers_reset,
                result.recommendations_expired,
                len(result.integrity_issues),
                result.integrity_issues,  # Pass details for debugging
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        workflow.logger.info(
            f"Maintenance complete: reset={result.stale_buyers_reset}, "
            f"expired={result.recommendations_expired}, stuck_failed={result.stuck_transcriptions_failed}, "
            f"archived={result.failed_creatives_archived}, "
            f"issues={len(result.integrity_issues)}, stale={result.is_stale}, "
            f"hypothesis_retried={result.hypotheses_retried}, "
            f"orphaned_tasks={result.orphaned_tasks_released}, "
            f"stuck_recovered={result.stuck_creatives_recovered}, "
            f"orphaned_hypotheses={result.orphaned_hypotheses_deleted}"
        )

        return result
