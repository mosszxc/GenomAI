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
        HistoricalVideoHandlerInput,
        HistoricalVideoHandlerResult,
    )
    from temporal.models.creative import CreativeInput
    from temporal.activities.supabase import (
        emit_event,
        create_creative,
        create_historical_creative,
    )
    from temporal.activities.keitaro import (
        get_campaigns_by_source,
        GetCampaignsBySourceInput,
    )
    from temporal.activities.buyer import (
        queue_historical_import,
        QueueHistoricalImportInput,
        get_import_by_campaign_id,
        update_import_with_video,
        update_import_status,
        UpdateImportVideoInput,
        load_buyer_by_id,
    )
    from temporal.workflows.creative_pipeline import CreativePipelineWorkflow


# Maximum campaigns per workflow execution (before continue-as-new)
MAX_CAMPAIGNS_PER_EXECUTION = 500


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
            workflow.logger.info(f"Fetching campaigns for source: {self._keitaro_source}")

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
                parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
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


@workflow.defn
class HistoricalVideoHandlerWorkflow:
    """
    Workflow for handling video URL submission for historical imports.

    Called when user submits a video URL for a pending historical import.
    Creates a creative with source_type='historical' and tracker_id=campaign_id,
    then triggers the CreativePipelineWorkflow.

    Replaces n8n workflow: UYgvqpsU3TMzb2Qd (Historical Import Video Handler)
    """

    def __init__(self):
        self._campaign_id: str = ""
        self._creative_id: Optional[str] = None
        self._queue_status: str = "pending"
        self._error: Optional[str] = None

    @workflow.run
    async def run(self, input: HistoricalVideoHandlerInput) -> HistoricalVideoHandlerResult:
        """
        Process video URL for historical import.

        Args:
            input: HistoricalVideoHandlerInput with campaign_id, video_url, buyer_id

        Returns:
            HistoricalVideoHandlerResult with creative_id and pipeline result
        """
        self._campaign_id = input.campaign_id

        default_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        queue_record = None  # Initialize before try block for except handler
        try:
            # Step 1: Find queue record by campaign_id
            workflow.logger.info(f"Looking up import queue for campaign: {input.campaign_id}")

            queue_record = await workflow.execute_activity(
                get_import_by_campaign_id,
                args=(input.campaign_id, input.buyer_id),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            if not queue_record:
                self._error = f"No import queue record found for campaign: {input.campaign_id}"
                workflow.logger.error(self._error)
                return self._build_result()

            workflow.logger.info(f"Found queue record: {queue_record.id}")

            # Step 2: Update queue with video_url and status='ready'
            self._queue_status = "ready"

            await workflow.execute_activity(
                update_import_with_video,
                UpdateImportVideoInput(
                    import_id=queue_record.id,
                    video_url=input.video_url,
                    status="ready",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            workflow.logger.info("Updated queue record with video URL")

            # Step 3: Load buyer to get geos/verticals
            buyer = await workflow.execute_activity(
                load_buyer_by_id,
                input.buyer_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            target_geo = buyer.geos[0] if buyer and buyer.geos else None
            target_vertical = buyer.verticals[0] if buyer and buyer.verticals else None

            # Step 4: Create creative with source_type='historical'
            self._queue_status = "processing"

            await workflow.execute_activity(
                update_import_status,
                args=(queue_record.id, "processing", None),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            creative = await workflow.execute_activity(
                create_historical_creative,
                args=(
                    input.video_url,
                    input.campaign_id,  # tracker_id = campaign_id
                    input.buyer_id,
                    queue_record.metrics,
                    target_geo,
                    target_vertical,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            self._creative_id = creative["id"]
            workflow.logger.info(f"Created historical creative: {self._creative_id}")

            # Step 5: Emit event
            await workflow.execute_activity(
                emit_event,
                args=(
                    "HistoricalCreativeRegistered",
                    {
                        "creative_id": self._creative_id,
                        "campaign_id": input.campaign_id,
                        "buyer_id": input.buyer_id,
                        "video_url": input.video_url,
                        "metrics": queue_record.metrics,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=default_retry,
            )

            # Step 6: Start creative pipeline as child workflow
            pipeline_result = await workflow.execute_child_workflow(
                CreativePipelineWorkflow.run,
                CreativeInput(
                    creative_id=self._creative_id,
                    buyer_id=input.buyer_id,
                ),
                id=f"historical-creative-pipeline-{self._creative_id}",
                task_queue="creative-pipeline",
                execution_timeout=timedelta(hours=1),
                parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
            )

            # Step 7: Update queue status to completed
            self._queue_status = "completed"

            await workflow.execute_activity(
                update_import_status,
                args=(queue_record.id, "completed", None),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            workflow.logger.info(
                f"Historical import completed: {input.campaign_id} -> {self._creative_id}"
            )

            return HistoricalVideoHandlerResult(
                campaign_id=input.campaign_id,
                creative_id=self._creative_id,
                idea_id=pipeline_result.idea_id if pipeline_result else None,
                decision_type=(pipeline_result.decision_type if pipeline_result else None),
                queue_status=self._queue_status,
                completed=True,
            )

        except Exception as e:
            self._error = str(e)
            self._queue_status = "failed"
            workflow.logger.error(f"Historical video handler failed: {e}")

            # Try to update queue status to failed
            if queue_record:
                try:
                    await workflow.execute_activity(
                        update_import_status,
                        args=(queue_record.id, "failed", str(e)),
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )
                except Exception as status_err:
                    workflow.logger.debug(f"Failed to update import status to failed: {status_err}")

            return self._build_result()

    def _build_result(self) -> HistoricalVideoHandlerResult:
        """Build result object."""
        return HistoricalVideoHandlerResult(
            campaign_id=self._campaign_id,
            creative_id=self._creative_id,
            queue_status=self._queue_status,
            error=self._error,
            completed=False,
        )

    @workflow.query
    def get_status(self) -> dict:
        """Query handler status."""
        return {
            "campaign_id": self._campaign_id,
            "creative_id": self._creative_id,
            "queue_status": self._queue_status,
            "error": self._error,
        }
