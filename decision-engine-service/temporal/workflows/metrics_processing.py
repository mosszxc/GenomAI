"""
Metrics Processing Workflow

Processes snapshots and creates outcomes:
1. Gets unprocessed snapshots
2. Creates outcome aggregates via OutcomeService
3. Triggers LearningLoopWorkflow

Replaces n8n workflows:
- Snapshot Creator (Gii8l2XwnX43Wqr4)
- Outcome Processor (bbbQC4Aua5E3SYSK)
- Outcome Aggregator (243QnGrUSDtXLjqU)
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.metrics import (
        GetUnprocessedSnapshotsInput,
        GetUnprocessedSnapshotsOutput,
        ProcessOutcomeInput,
        ProcessOutcomeOutput,
        EmitMetricsEventInput,
        get_unprocessed_snapshots,
        process_outcome,
        emit_metrics_event,
    )


@dataclass
class MetricsProcessingInput:
    """Input for MetricsProcessingWorkflow"""
    batch_limit: int = 50  # Number of snapshots to process per run
    trigger_learning: bool = True  # Whether to trigger learning loop


@dataclass
class MetricsProcessingResult:
    """Result from MetricsProcessingWorkflow"""
    snapshots_processed: int
    outcomes_created: int
    outcomes_failed: int
    learning_triggered: bool
    errors: list[str]


# Retry policy for Supabase operations
SUPABASE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5
)


@workflow.defn
class MetricsProcessingWorkflow:
    """
    Metrics Processing Workflow

    Processes daily snapshots into outcome aggregates.
    Triggered after KeitaroPollerWorkflow or on schedule.
    """

    @workflow.run
    async def run(self, input: MetricsProcessingInput) -> MetricsProcessingResult:
        """
        Main workflow execution.

        Steps:
        1. Get unprocessed snapshots
        2. Process each snapshot into outcome
        3. Trigger learning loop if enabled
        """
        workflow.logger.info(f"Starting Metrics Processing (limit: {input.batch_limit})")

        errors = []
        outcomes_created = 0
        outcomes_failed = 0

        # Step 1: Get unprocessed snapshots
        try:
            snapshots_result: GetUnprocessedSnapshotsOutput = await workflow.execute_activity(
                get_unprocessed_snapshots,
                GetUnprocessedSnapshotsInput(limit=input.batch_limit),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=SUPABASE_RETRY_POLICY
            )
        except Exception as e:
            workflow.logger.error(f"Failed to get snapshots: {e}")
            return MetricsProcessingResult(
                snapshots_processed=0,
                outcomes_created=0,
                outcomes_failed=0,
                learning_triggered=False,
                errors=[f"Failed to get snapshots: {str(e)}"]
            )

        snapshot_ids = snapshots_result.snapshot_ids
        workflow.logger.info(f"Found {len(snapshot_ids)} snapshots to process")

        if not snapshot_ids:
            return MetricsProcessingResult(
                snapshots_processed=0,
                outcomes_created=0,
                outcomes_failed=0,
                learning_triggered=False,
                errors=[]
            )

        # Step 2: Process each snapshot
        for snapshot_id in snapshot_ids:
            try:
                outcome_result: ProcessOutcomeOutput = await workflow.execute_activity(
                    process_outcome,
                    ProcessOutcomeInput(snapshot_id=snapshot_id),
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=SUPABASE_RETRY_POLICY
                )

                if outcome_result.success:
                    outcomes_created += 1
                    workflow.logger.info(
                        f"Outcome created: {outcome_result.outcome_id}"
                    )
                else:
                    # Some errors are expected (no idea found, no decision, etc.)
                    if outcome_result.error_code not in ["IDEA_NOT_FOUND", "NO_APPROVED_DECISION"]:
                        outcomes_failed += 1
                        errors.append(
                            f"Snapshot {snapshot_id}: "
                            f"{outcome_result.error_code} - {outcome_result.error_message}"
                        )

            except Exception as e:
                outcomes_failed += 1
                errors.append(f"Snapshot {snapshot_id}: {str(e)}")

        # Step 3: Trigger learning loop if needed and we created outcomes
        learning_triggered = False
        if input.trigger_learning and outcomes_created > 0:
            try:
                # Start child workflow for learning
                learning_triggered = await workflow.start_child_workflow(
                    "LearningLoopWorkflow",
                    LearningLoopInput(batch_limit=100),
                    id=f"learning-{workflow.info().workflow_id}",
                    task_queue="metrics"
                )
                learning_triggered = True
                workflow.logger.info("Learning loop triggered")
            except Exception as e:
                # Learning trigger is best-effort
                workflow.logger.warning(f"Failed to trigger learning: {e}")

        # Emit completion event
        try:
            await workflow.execute_activity(
                emit_metrics_event,
                EmitMetricsEventInput(
                    event_type="metrics.processing.completed",
                    entity_type="processor",
                    entity_id=workflow.info().workflow_id,
                    payload={
                        "snapshots_processed": len(snapshot_ids),
                        "outcomes_created": outcomes_created,
                        "outcomes_failed": outcomes_failed,
                        "learning_triggered": learning_triggered
                    }
                ),
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=SUPABASE_RETRY_POLICY
            )
        except Exception:
            pass  # Event emission is best-effort

        workflow.logger.info(
            f"Metrics Processing complete: "
            f"{outcomes_created} outcomes created, {outcomes_failed} failed"
        )

        return MetricsProcessingResult(
            snapshots_processed=len(snapshot_ids),
            outcomes_created=outcomes_created,
            outcomes_failed=outcomes_failed,
            learning_triggered=learning_triggered,
            errors=errors
        )


# Forward declaration for child workflow
@dataclass
class LearningLoopInput:
    """Input for LearningLoopWorkflow"""
    batch_limit: int = 100
