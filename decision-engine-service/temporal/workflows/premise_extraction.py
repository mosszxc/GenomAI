"""
Premise Extraction Workflow

Extracts premise patterns from concluded creatives.
Triggered when creative test is concluded (win or loss).

Both outcomes are valuable:
- Win: successful premise patterns
- Loss: anti-patterns to avoid (marked as 'dead')
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import Optional, List

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.premise_extraction import (
        CreativeData,
        ExtractedPremise,
        load_creative_data,
        extract_premises_via_llm,
        upsert_premise_and_learning,
        emit_premise_extraction_event,
    )


@dataclass
class PremiseExtractionInput:
    """Input for PremiseExtractionWorkflow."""

    creative_id: str
    test_result: Optional[str] = None  # 'win' or 'loss', auto-detected if None


@dataclass
class PremiseExtractionOutput:
    """Output from PremiseExtractionWorkflow."""

    creative_id: str
    test_result: str
    premises_extracted: int
    premises_created: int
    learnings_updated: int
    errors: List[str]


# Retry policy for LLM operations
LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)

# Retry policy for DB operations
DB_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)


@workflow.defn
class PremiseExtractionWorkflow:
    """
    Extract premises from concluded creatives.

    Flow:
    1. Load creative data (decomposed + transcript + metrics)
    2. Extract premise patterns via LLM
    3. Create/update premises and learnings
    4. Emit event for observability

    Safe to run multiple times (idempotent).
    """

    @workflow.run
    async def run(self, input: PremiseExtractionInput) -> PremiseExtractionOutput:
        """Execute premise extraction workflow."""

        errors = []
        premises_created = 0
        learnings_updated = 0

        workflow.logger.info(f"Starting premise extraction for {input.creative_id}")

        # Step 1: Load creative data
        try:
            creative_data: CreativeData = await workflow.execute_activity(
                load_creative_data,
                input.creative_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DB_RETRY_POLICY,
            )
        except Exception as e:
            workflow.logger.error(f"Failed to load creative: {e}")
            return PremiseExtractionOutput(
                creative_id=input.creative_id,
                test_result=input.test_result or "unknown",
                premises_extracted=0,
                premises_created=0,
                learnings_updated=0,
                errors=[f"Failed to load creative: {str(e)}"],
            )

        test_result = input.test_result or creative_data.test_result

        # Validate test_result
        if test_result not in ("win", "loss"):
            workflow.logger.warning(
                f"Invalid test_result: {test_result}, skipping extraction"
            )
            return PremiseExtractionOutput(
                creative_id=input.creative_id,
                test_result=test_result,
                premises_extracted=0,
                premises_created=0,
                learnings_updated=0,
                errors=[f"Invalid test_result: {test_result}"],
            )

        # Step 2: Extract premises via LLM
        try:
            extracted_premises: List[
                ExtractedPremise
            ] = await workflow.execute_activity(
                extract_premises_via_llm,
                creative_data,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=LLM_RETRY_POLICY,
            )
        except Exception as e:
            workflow.logger.error(f"LLM extraction failed: {e}")
            errors.append(f"LLM extraction failed: {str(e)}")
            extracted_premises = []

        workflow.logger.info(f"Extracted {len(extracted_premises)} premises")

        # Step 3: Upsert premises and learnings
        for premise in extracted_premises:
            try:
                result = await workflow.execute_activity(
                    upsert_premise_and_learning,
                    args=[
                        premise,
                        test_result,
                        creative_data.geo,
                        creative_data.spend,
                        creative_data.revenue,
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DB_RETRY_POLICY,
                )

                if result.get("success"):
                    if result.get("is_new"):
                        premises_created += 1
                    learnings_updated += 1
                else:
                    errors.append(f"Failed to upsert premise: {premise.name}")

            except Exception as e:
                workflow.logger.error(f"Failed to upsert premise {premise.name}: {e}")
                errors.append(f"Failed to upsert {premise.name}: {str(e)}")

        # Step 4: Emit event
        try:
            await workflow.execute_activity(
                emit_premise_extraction_event,
                args=[input.creative_id, len(extracted_premises), test_result],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=DB_RETRY_POLICY,
            )
        except Exception as e:
            workflow.logger.warning(f"Failed to emit event: {e}")
            # Non-critical, don't add to errors

        workflow.logger.info(
            f"Premise extraction complete: "
            f"extracted={len(extracted_premises)}, "
            f"created={premises_created}, "
            f"learnings={learnings_updated}"
        )

        return PremiseExtractionOutput(
            creative_id=input.creative_id,
            test_result=test_result,
            premises_extracted=len(extracted_premises),
            premises_created=premises_created,
            learnings_updated=learnings_updated,
            errors=errors,
        )


@workflow.defn
class BatchPremiseExtractionWorkflow:
    """
    Batch process multiple creatives for premise extraction.

    Used for:
    1. Initial processing of historical creatives
    2. Catch-up processing if pipeline was down
    """

    @workflow.run
    async def run(self, creative_ids: List[str]) -> dict:
        """Process multiple creatives."""

        results = {
            "total": len(creative_ids),
            "processed": 0,
            "premises_created": 0,
            "errors": [],
        }

        for creative_id in creative_ids:
            try:
                output = await workflow.execute_child_workflow(
                    PremiseExtractionWorkflow.run,
                    PremiseExtractionInput(creative_id=creative_id),
                    id=f"premise-extract-{creative_id}",
                    parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
                )

                results["processed"] += 1
                results["premises_created"] += output.premises_created

                if output.errors:
                    results["errors"].extend(output.errors)

            except Exception as e:
                workflow.logger.error(f"Failed to process {creative_id}: {e}")
                results["errors"].append(f"{creative_id}: {str(e)}")

        workflow.logger.info(
            f"Batch complete: {results['processed']}/{results['total']}"
        )

        return results
