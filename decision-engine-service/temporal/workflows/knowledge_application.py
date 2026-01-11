"""
Knowledge Application Workflow

Applies approved knowledge extractions to the system.
Routes to appropriate application activity based on knowledge_type.

Queue: knowledge
Trigger: Approved extraction (via API or Telegram)
"""

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models and activities (pass-through for workflow sandbox)
with workflow.unsafe.imports_passed_through():
    from temporal.models.knowledge import (
        ApplyKnowledgeInput,
        ApplyKnowledgeResult,
    )
    from temporal.activities.knowledge_db import (
        get_extraction,
        update_extraction_status,
        apply_premise_knowledge,
        apply_process_rule,
        apply_component_weight,
        apply_creative_attribute,
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
class KnowledgeApplicationWorkflow:
    """
    Apply approved knowledge to the system.

    Routes extraction to appropriate application activity based on type:
        - premise → premises table
        - creative_attribute → schema registry (manual)
        - process_rule → config table
        - component_weight → component_learnings
    """

    @workflow.run
    async def run(self, input: ApplyKnowledgeInput) -> ApplyKnowledgeResult:
        workflow.logger.info(f"Applying knowledge: {input.extraction_id}")

        # 1. Load extraction
        extraction = await workflow.execute_activity(
            get_extraction,
            args=[input.extraction_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY,
        )

        knowledge_type = extraction.get("knowledge_type")
        name = extraction.get("name")
        workflow.logger.info(f"Extraction type: {knowledge_type}, name: {name}")

        # 2. Route by type
        result = None
        error_message = None

        try:
            if knowledge_type == "premise":
                result = await workflow.execute_activity(
                    apply_premise_knowledge,
                    args=[extraction],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY,
                )

            elif knowledge_type == "creative_attribute":
                result = await workflow.execute_activity(
                    apply_creative_attribute,
                    args=[extraction],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY,
                )

            elif knowledge_type == "process_rule":
                result = await workflow.execute_activity(
                    apply_process_rule,
                    args=[extraction],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY,
                )

            elif knowledge_type == "component_weight":
                result = await workflow.execute_activity(
                    apply_component_weight,
                    args=[extraction],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY,
                )

            else:
                error_message = f"Unknown knowledge_type: {knowledge_type}"
                workflow.logger.error(error_message)

        except Exception as e:
            error_message = str(e)
            workflow.logger.error(f"Application failed: {e}")

        # 3. Update extraction status
        if result and result.get("success"):
            await workflow.execute_activity(
                update_extraction_status,
                args=[
                    input.extraction_id,
                    "applied",
                    input.reviewed_by,
                    None,  # review_notes
                    result.get("target_id"),
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )

            # Notify if we have reviewer info
            if input.reviewed_by:
                message = (
                    f"<b>Knowledge Applied</b>\n\n"
                    f"<b>Type:</b> {knowledge_type}\n"
                    f"<b>Name:</b> {name}\n"
                    f"<b>Target:</b> {result.get('target_table')}\n"
                )
                if result.get("note"):
                    message += f"\n<i>{result.get('note')}</i>"

                try:
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[input.reviewed_by, message],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=DEFAULT_RETRY,
                    )
                except Exception as e:
                    workflow.logger.warning(f"Failed to notify: {e}")

            return ApplyKnowledgeResult(
                extraction_id=input.extraction_id,
                target_table=result.get("target_table", ""),
                target_id=result.get("target_id"),
                operation=result.get("operation", ""),
                success=True,
                note=result.get("note"),
            )

        else:
            # Application failed
            return ApplyKnowledgeResult(
                extraction_id=input.extraction_id,
                target_table="",
                target_id=None,
                operation="",
                success=False,
                error_message=error_message,
            )
