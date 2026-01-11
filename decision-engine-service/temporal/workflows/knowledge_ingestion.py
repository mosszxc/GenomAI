"""
Knowledge Ingestion Workflow

Processes uploaded transcripts and extracts structured knowledge.
Saves extractions as pending for human review via Telegram.

Queue: knowledge
Trigger: API endpoint or Telegram file upload
"""

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models and activities (pass-through for workflow sandbox)
with workflow.unsafe.imports_passed_through():
    from temporal.models.knowledge import (
        KnowledgeSourceInput,
        KnowledgeIngestionResult,
    )
    from temporal.activities.knowledge_extraction import (
        extract_knowledge_from_transcript,
    )
    from temporal.activities.knowledge_db import (
        save_knowledge_source,
        save_pending_extractions,
        mark_source_processed,
    )
    from temporal.activities.buyer import send_telegram_message


# Default retry policy for activities
DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)


@workflow.defn
class KnowledgeIngestionWorkflow:
    """
    Process transcript and extract knowledge.

    Steps:
        1. Save source to knowledge_sources
        2. Extract knowledge via LLM
        3. Save extractions as pending
        4. Notify admin via Telegram
        5. Mark source as processed
    """

    @workflow.run
    async def run(self, input: KnowledgeSourceInput) -> KnowledgeIngestionResult:
        workflow.logger.info(f"Starting knowledge ingestion: {input.title}")

        # 1. Save source to DB
        source_id = await workflow.execute_activity(
            save_knowledge_source,
            args=[
                input.title,
                input.content,
                input.source_type,
                input.url,
                input.created_by,
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY,
        )

        workflow.logger.info(f"Source saved: {source_id}")

        # 2. Extract knowledge via LLM
        try:
            extraction_result = await workflow.execute_activity(
                extract_knowledge_from_transcript,
                args=[input.content, source_id, input.title],
                start_to_close_timeout=timedelta(minutes=5),  # LLM can be slow
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=2),
                    maximum_attempts=2,  # LLM retries are expensive
                ),
            )
        except Exception as e:
            workflow.logger.error(f"LLM extraction failed: {e}")
            return KnowledgeIngestionResult(
                source_id=source_id,
                extraction_count=0,
                status="error",
                error_message=str(e),
            )

        extractions = extraction_result.get("extractions", [])
        workflow.logger.info(f"Extracted {len(extractions)} knowledge items")

        if not extractions:
            # No knowledge found - mark processed and return
            await workflow.execute_activity(
                mark_source_processed,
                args=[source_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )
            return KnowledgeIngestionResult(
                source_id=source_id,
                extraction_count=0,
                status="no_extractions",
            )

        # 3. Save extractions as pending
        extraction_ids = await workflow.execute_activity(
            save_pending_extractions,
            args=[source_id, extractions],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY,
        )

        workflow.logger.info(f"Saved {len(extraction_ids)} pending extractions")

        # 4. Notify admin via Telegram
        if input.created_by:
            type_counts = {}
            for ext in extractions:
                t = ext.get("knowledge_type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1

            type_summary = ", ".join([f"{v} {k}" for k, v in type_counts.items()])

            message = (
                f"<b>Knowledge Extraction Complete</b>\n\n"
                f"<b>Source:</b> {input.title}\n"
                f"<b>Extracted:</b> {len(extractions)} items\n"
                f"<b>Types:</b> {type_summary}\n\n"
                f"Use /knowledge to review pending items."
            )

            try:
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[input.created_by, message],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY,
                )
            except Exception as e:
                workflow.logger.warning(f"Failed to notify admin: {e}")

        # 5. Mark source as processed
        await workflow.execute_activity(
            mark_source_processed,
            args=[source_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY,
        )

        return KnowledgeIngestionResult(
            source_id=source_id,
            extraction_count=len(extractions),
            status="pending_review",
        )
