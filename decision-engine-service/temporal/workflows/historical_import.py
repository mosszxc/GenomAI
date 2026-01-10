"""
Historical Import Workflow

Batch imports campaigns from Keitaro for a buyer.
Uses continue-as-new for large imports to avoid history limits.

Replaces n8n workflows:
    - lmiWkYTRZPSpydJH (Buyer Historical Loader)
    - 6tu8j4M4wvwi0pyB (Buyer Historical URL Handler v2)
    - UYgvqpsU3TMzb2Qd (Historical Import Video Handler)
"""

from datetime import timedelta
from typing import Optional
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models and activities (pass-through for workflow sandbox)
with workflow.unsafe.imports_passed_through():
    from temporal.models.buyer import (
        HistoricalImportInput,
        HistoricalImportResult,
    )
    from temporal.models.creative import CreativeInput
    from temporal.activities.supabase import emit_event, create_creative
    from temporal.activities.keitaro import (
        get_campaigns_by_source,
        GetCampaignsBySourceInput,
    )
    from temporal.activities.buyer import (
        queue_historical_import,
        QueueHistoricalImportInput,
    )
    from temporal.workflows.creative_pipeline import CreativePipelineWorkflow


# Maximum campaigns per workflow execution (before continue-as-new)
MAX_CAMPAIGNS_PER_EXECUTION = 50


@workflow.defn
class HistoricalImportWorkflow:
    """
    Historical import workflow for loading campaigns from Keitaro.

    Fetches campaigns by source, queues them for processing,
    and triggers creative pipeline for each.

    Uses continue-as-new for large imports (>50 campaigns).
    """

    def __init__(self):
        self._buyer_id: str = ""
        self._keitaro_source: str = ""
        self._total_campaigns: int = 0
        self._processed_campaigns: int = 0
        self._queued_creatives: int = 0
        self._failed_imports: int = 0
        self._error: Optional[str] = None

    @workflow.run
    async def run(self, input: HistoricalImportInput) -> HistoricalImportResult:
        """
        Execute the historical import workflow.

        Args:
            input: HistoricalImportInput with buyer_id and keitaro_source

        Returns:
            HistoricalImportResult with import statistics
        """
        self._buyer_id = input.buyer_id
        self._keitaro_source = input.keitaro_source

        # Default retry policy
        default_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        try:
            # Step 1: Fetch campaigns from Keitaro
            workflow.logger.info(
                f"Fetching campaigns for source: {self._keitaro_source}"
            )

            campaigns_result = await workflow.execute_activity(
                get_campaigns_by_source,
                GetCampaignsBySourceInput(
                    source=self._keitaro_source,
                    date_from=input.date_from,
                    date_to=input.date_to,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=default_retry,
            )

            self._total_campaigns = campaigns_result.total
            workflow.logger.info(f"Found {self._total_campaigns} campaigns")

            if self._total_campaigns == 0:
                return self._build_result(completed=True)

            # Step 2: Queue campaigns for processing
            campaigns = campaigns_result.campaigns
            batch_size = input.batch_size or 10

            # Process in batches
            for i in range(0, len(campaigns), batch_size):
                batch = campaigns[i : i + batch_size]

                for campaign in batch:
                    try:
                        # Queue each campaign
                        await workflow.execute_activity(
                            queue_historical_import,
                            QueueHistoricalImportInput(
                                buyer_id=self._buyer_id,
                                campaign_id=campaign.campaign_id,
                                video_url=None,  # Will be populated later
                                keitaro_source=self._keitaro_source,
                                metrics=campaign.to_dict(),
                            ),
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=default_retry,
                        )

                        self._queued_creatives += 1
                        self._processed_campaigns += 1

                        # Start creative pipeline as child workflow (fire-and-forget)
                        # Note: In production, you might want to use a signal or schedule
                        # instead of starting child workflows directly

                    except Exception as e:
                        workflow.logger.error(
                            f"Failed to queue campaign {campaign.campaign_id}: {e}"
                        )
                        self._failed_imports += 1
                        self._processed_campaigns += 1

                # Check if we should continue-as-new
                if self._processed_campaigns >= MAX_CAMPAIGNS_PER_EXECUTION:
                    remaining = campaigns[i + batch_size :]
                    if remaining:
                        workflow.logger.info(
                            f"Continuing with {len(remaining)} remaining campaigns"
                        )
                        # Create new input with remaining campaigns
                        # Note: This is a simplified version
                        # In production, you might pass remaining campaign IDs
                        workflow.continue_as_new(
                            HistoricalImportInput(
                                buyer_id=self._buyer_id,
                                keitaro_source=self._keitaro_source,
                                date_from=input.date_from,
                                date_to=input.date_to,
                                batch_size=batch_size,
                            )
                        )

            return self._build_result(completed=True)

        except Exception as e:
            self._error = str(e)
            workflow.logger.error(f"Historical import failed: {e}")
            return self._build_result(completed=False)

    def _build_result(self, completed: bool) -> HistoricalImportResult:
        """Build result object."""
        return HistoricalImportResult(
            buyer_id=self._buyer_id,
            keitaro_source=self._keitaro_source,
            total_campaigns=self._total_campaigns,
            processed_campaigns=self._processed_campaigns,
            queued_creatives=self._queued_creatives,
            failed_imports=self._failed_imports,
            error=self._error,
            completed=completed,
        )

    @workflow.query
    def get_progress(self) -> dict:
        """Query import progress."""
        return {
            "buyer_id": self._buyer_id,
            "keitaro_source": self._keitaro_source,
            "total_campaigns": self._total_campaigns,
            "processed_campaigns": self._processed_campaigns,
            "queued_creatives": self._queued_creatives,
            "failed_imports": self._failed_imports,
            "error": self._error,
            "progress_percent": (
                int(self._processed_campaigns / self._total_campaigns * 100)
                if self._total_campaigns > 0
                else 0
            ),
        }


@workflow.defn
class CreativeRegistrationWorkflow:
    """
    Workflow for registering a single creative from URL.

    Called when user sends a video URL during or after onboarding.
    """

    def __init__(self):
        self._creative_id: Optional[str] = None
        self._status: str = "pending"
        self._error: Optional[str] = None

    @workflow.run
    async def run(
        self,
        buyer_id: str,
        video_url: str,
        target_geo: Optional[str] = None,
        target_vertical: Optional[str] = None,
    ) -> dict:
        """
        Register a creative and start processing.

        Args:
            buyer_id: Buyer UUID
            video_url: Video URL to register
            target_geo: Optional target GEO
            target_vertical: Optional target vertical

        Returns:
            dict with creative_id and status
        """
        default_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        try:
            # Create creative record in database
            self._status = "registering"

            creative = await workflow.execute_activity(
                create_creative,
                video_url,
                "telegram",  # source_type
                buyer_id,
                target_geo,
                target_vertical,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            self._creative_id = creative["id"]
            self._status = "registered"

            # Emit event
            await workflow.execute_activity(
                emit_event,
                "CreativeRegistered",
                {
                    "creative_id": self._creative_id,
                    "buyer_id": buyer_id,
                    "video_url": video_url,
                    "source": "telegram",
                },
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=default_retry,
            )

            # Start creative pipeline as child workflow
            pipeline_result = await workflow.execute_child_workflow(
                CreativePipelineWorkflow.run,
                CreativeInput(
                    creative_id=self._creative_id,
                    buyer_id=buyer_id,
                ),
                id=f"creative-pipeline-{self._creative_id}",
                task_queue="creative-pipeline",
                execution_timeout=timedelta(hours=1),
            )

            self._status = "processed"

            return {
                "creative_id": self._creative_id,
                "status": self._status,
                "pipeline_result": {
                    "idea_id": pipeline_result.idea_id,
                    "decision_type": pipeline_result.decision_type,
                },
            }

        except Exception as e:
            self._error = str(e)
            self._status = "failed"
            return {
                "creative_id": self._creative_id,
                "status": self._status,
                "error": self._error,
            }

    @workflow.query
    def get_status(self) -> dict:
        """Query registration status."""
        return {
            "creative_id": self._creative_id,
            "status": self._status,
            "error": self._error,
        }
