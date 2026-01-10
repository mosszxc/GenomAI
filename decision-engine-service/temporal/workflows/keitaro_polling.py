"""
Keitaro Polling Workflow

Scheduled workflow that:
1. Fetches all active trackers from Keitaro
2. Gets metrics for each tracker
3. Upserts metrics to raw_metrics_current
4. Triggers snapshot creation via MetricsProcessingWorkflow

Replaces n8n Keitaro Poller workflow (0TrVJOtHiNEEAsTN).
"""

from datetime import timedelta
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy

# Activities will be imported with workflow.unsafe.imports_passed_through()
with workflow.unsafe.imports_passed_through():
    from temporal.activities.keitaro import (
        GetAllTrackersInput,
        GetAllTrackersOutput,
        BatchMetricsInput,
        BatchMetricsOutput,
        get_all_trackers,
        get_batch_metrics,
    )
    from temporal.activities.metrics import (
        UpsertRawMetricsInput,
        CreateSnapshotInput,
        CreateSnapshotOutput,
        EmitMetricsEventInput,
        upsert_raw_metrics,
        create_daily_snapshot,
        emit_metrics_event,
    )


@dataclass
class KeitaroPollerInput:
    """Input for KeitaroPollerWorkflow"""

    interval: str = "yesterday"  # yesterday, today, last_7_days
    create_snapshots: bool = True  # Whether to create daily snapshots


@dataclass
class KeitaroPollerResult:
    """Result from KeitaroPollerWorkflow"""

    trackers_found: int
    metrics_collected: int
    metrics_failed: int
    snapshots_created: int
    errors: list[str]


# Retry policy for Keitaro API calls
KEITARO_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)

# Retry policy for Supabase operations
SUPABASE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)


@workflow.defn
class KeitaroPollerWorkflow:
    """
    Keitaro Poller Workflow

    Scheduled to run every 5-10 minutes.
    Collects metrics from Keitaro and stores in Supabase.
    """

    @workflow.run
    async def run(self, input: KeitaroPollerInput) -> KeitaroPollerResult:
        """
        Main workflow execution.

        Steps:
        1. Get all active trackers
        2. Batch fetch metrics for all trackers
        3. Upsert metrics to raw_metrics_current
        4. Optionally create daily snapshots
        """
        workflow.logger.info(f"Starting Keitaro Poller for interval: {input.interval}")

        errors = []
        metrics_collected = 0
        snapshots_created = 0

        # Step 1: Get all active trackers
        try:
            trackers_result: GetAllTrackersOutput = await workflow.execute_activity(
                get_all_trackers,
                GetAllTrackersInput(interval=input.interval),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=KEITARO_RETRY_POLICY,
            )
        except Exception as e:
            workflow.logger.error(f"Failed to get trackers: {e}")
            return KeitaroPollerResult(
                trackers_found=0,
                metrics_collected=0,
                metrics_failed=0,
                snapshots_created=0,
                errors=[f"Failed to get trackers: {str(e)}"],
            )

        tracker_ids = trackers_result.tracker_ids
        workflow.logger.info(f"Found {len(tracker_ids)} trackers")

        if not tracker_ids:
            return KeitaroPollerResult(
                trackers_found=0,
                metrics_collected=0,
                metrics_failed=0,
                snapshots_created=0,
                errors=[],
            )

        # Step 2: Batch fetch metrics (more efficient than individual calls)
        try:
            batch_result: BatchMetricsOutput = await workflow.execute_activity(
                get_batch_metrics,
                BatchMetricsInput(tracker_ids=tracker_ids, interval=input.interval),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=KEITARO_RETRY_POLICY,
            )
        except Exception as e:
            workflow.logger.error(f"Failed to get batch metrics: {e}")
            errors.append(f"Batch metrics error: {str(e)}")
            batch_result = BatchMetricsOutput(metrics=[], failed_ids=tracker_ids)

        workflow.logger.info(
            f"Batch metrics: {len(batch_result.metrics)} success, "
            f"{len(batch_result.failed_ids)} failed"
        )

        # Step 3: Upsert metrics to raw_metrics_current
        for metrics in batch_result.metrics:
            try:
                await workflow.execute_activity(
                    upsert_raw_metrics,
                    UpsertRawMetricsInput(
                        tracker_id=metrics.tracker_id,
                        metrics_date=metrics.date,
                        metrics=metrics.to_dict(),
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=SUPABASE_RETRY_POLICY,
                )
                metrics_collected += 1

                # Step 4: Create snapshot if enabled
                if input.create_snapshots:
                    try:
                        snapshot_result: CreateSnapshotOutput = (
                            await workflow.execute_activity(
                                create_daily_snapshot,
                                CreateSnapshotInput(
                                    tracker_id=metrics.tracker_id,
                                    snapshot_date=metrics.date,
                                    metrics=metrics.to_dict(),
                                ),
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=SUPABASE_RETRY_POLICY,
                            )
                        )
                        if snapshot_result.created:
                            snapshots_created += 1
                    except Exception as e:
                        # Duplicate snapshot is expected - not an error
                        if "duplicate" not in str(e).lower():
                            errors.append(
                                f"Snapshot error {metrics.tracker_id}: {str(e)}"
                            )

            except Exception as e:
                errors.append(f"Upsert error {metrics.tracker_id}: {str(e)}")

        # Emit completion event
        try:
            await workflow.execute_activity(
                emit_metrics_event,
                EmitMetricsEventInput(
                    event_type="keitaro.polling.completed",
                    entity_type="poller",
                    entity_id=workflow.info().workflow_id,
                    payload={
                        "interval": input.interval,
                        "trackers_found": len(tracker_ids),
                        "metrics_collected": metrics_collected,
                        "snapshots_created": snapshots_created,
                        "errors_count": len(errors),
                    },
                ),
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=SUPABASE_RETRY_POLICY,
            )
        except Exception:
            pass  # Event emission is best-effort

        workflow.logger.info(
            f"Keitaro Poller complete: "
            f"{metrics_collected} metrics, {snapshots_created} snapshots"
        )

        return KeitaroPollerResult(
            trackers_found=len(tracker_ids),
            metrics_collected=metrics_collected,
            metrics_failed=len(batch_result.failed_ids),
            snapshots_created=snapshots_created,
            errors=errors,
        )
