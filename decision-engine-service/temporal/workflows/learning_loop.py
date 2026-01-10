"""
Learning Loop Workflow

Processes outcomes and applies learning:
1. Fetches unprocessed outcomes
2. Updates confidence versions
3. Updates fatigue state versions
4. Checks and applies death conditions
5. Processes component and premise learning

Replaces n8n Learning Loop v2 workflow (fzXkoG805jQZUR3S).
"""

from datetime import timedelta
from dataclasses import dataclass

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.learning import (
        ProcessLearningInput,
        ProcessLearningOutput,
        GetUnprocessedOutcomesInput,
        GetUnprocessedOutcomesOutput,
        ProcessSingleOutcomeInput,
        ProcessSingleOutcomeOutput,
        EmitLearningEventInput,
        process_learning_batch,
        get_unprocessed_outcomes,
        process_single_outcome,
        emit_learning_event,
    )


@dataclass
class LearningLoopInput:
    """Input for LearningLoopWorkflow"""

    batch_limit: int = 100
    process_individually: bool = False  # False = use batch, True = process one by one


@dataclass
class LearningLoopResult:
    """Result from LearningLoopWorkflow"""

    processed_count: int
    updated_ideas: list[str]
    new_deaths: list[dict]
    component_updates: int
    premise_updates: int
    fatigue_updates: int
    errors: list[str]


# Retry policy for learning operations
LEARNING_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)


@workflow.defn
class LearningLoopWorkflow:
    """
    Learning Loop Workflow

    Processes outcomes and updates idea confidence/fatigue.
    Idempotent - safe to retry.
    """

    @workflow.run
    async def run(self, input: LearningLoopInput) -> LearningLoopResult:
        """
        Main workflow execution.

        Two modes:
        1. Batch mode (default): Uses existing learning_loop.py batch processing
        2. Individual mode: Processes outcomes one by one with separate activities

        Batch mode is more efficient but individual mode provides better observability.
        """
        workflow.logger.info(
            f"Starting Learning Loop "
            f"(limit: {input.batch_limit}, individual: {input.process_individually})"
        )

        if input.process_individually:
            return await self._run_individual(input)
        else:
            return await self._run_batch(input)

    async def _run_batch(self, input: LearningLoopInput) -> LearningLoopResult:
        """Run learning in batch mode using existing learning_loop.py"""
        workflow.logger.info("Running in batch mode")

        try:
            result: ProcessLearningOutput = await workflow.execute_activity(
                process_learning_batch,
                ProcessLearningInput(batch_limit=input.batch_limit),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=LEARNING_RETRY_POLICY,
            )

            workflow.logger.info(
                f"Learning batch complete: "
                f"{result.processed_count} processed, "
                f"{len(result.new_deaths)} deaths"
            )

            # Emit completion event
            try:
                await workflow.execute_activity(
                    emit_learning_event,
                    EmitLearningEventInput(
                        event_type="learning.batch.completed",
                        idea_id=workflow.info().workflow_id,
                        payload={
                            "processed_count": result.processed_count,
                            "new_deaths": len(result.new_deaths),
                            "component_updates": result.component_updates,
                            "premise_updates": result.premise_updates,
                            "fatigue_updates": result.fatigue_updates,
                            "errors_count": len(result.errors),
                        },
                    ),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=LEARNING_RETRY_POLICY,
                )
            except Exception:
                pass  # Event emission is best-effort

            return LearningLoopResult(
                processed_count=result.processed_count,
                updated_ideas=result.updated_ideas,
                new_deaths=result.new_deaths,
                component_updates=result.component_updates,
                premise_updates=result.premise_updates,
                fatigue_updates=result.fatigue_updates,
                errors=result.errors,
            )

        except Exception as e:
            workflow.logger.error(f"Learning batch failed: {e}")
            return LearningLoopResult(
                processed_count=0,
                updated_ideas=[],
                new_deaths=[],
                component_updates=0,
                premise_updates=0,
                fatigue_updates=0,
                errors=[str(e)],
            )

    async def _run_individual(self, input: LearningLoopInput) -> LearningLoopResult:
        """Run learning by processing outcomes individually"""
        workflow.logger.info("Running in individual mode")

        errors = []
        updated_ideas = []
        new_deaths = []

        # Step 1: Get unprocessed outcomes
        try:
            outcomes_result: GetUnprocessedOutcomesOutput = (
                await workflow.execute_activity(
                    get_unprocessed_outcomes,
                    GetUnprocessedOutcomesInput(limit=input.batch_limit),
                    start_to_close_timeout=timedelta(minutes=1),
                    retry_policy=LEARNING_RETRY_POLICY,
                )
            )
        except Exception as e:
            return LearningLoopResult(
                processed_count=0,
                updated_ideas=[],
                new_deaths=[],
                component_updates=0,
                premise_updates=0,
                fatigue_updates=0,
                errors=[f"Failed to get outcomes: {str(e)}"],
            )

        outcomes = outcomes_result.outcomes
        workflow.logger.info(f"Found {len(outcomes)} outcomes to process")

        if not outcomes:
            return LearningLoopResult(
                processed_count=0,
                updated_ideas=[],
                new_deaths=[],
                component_updates=0,
                premise_updates=0,
                fatigue_updates=0,
                errors=[],
            )

        # Step 2: Process each outcome
        processed_count = 0
        for outcome in outcomes:
            try:
                result: ProcessSingleOutcomeOutput = await workflow.execute_activity(
                    process_single_outcome,
                    ProcessSingleOutcomeInput(
                        outcome_id=outcome.id,
                        creative_id=outcome.creative_id,
                        cpa=outcome.cpa,
                        spend=outcome.spend,
                        environment_ctx=outcome.environment_ctx,
                        window_end=outcome.window_end,
                    ),
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=LEARNING_RETRY_POLICY,
                )

                if result.success:
                    processed_count += 1
                    if result.idea_id:
                        updated_ideas.append(result.idea_id)
                    if result.death_state:
                        new_deaths.append(
                            {
                                "idea_id": result.idea_id,
                                "death_state": result.death_state,
                            }
                        )
                else:
                    errors.append(f"Outcome {outcome.id}: {result.error}")

            except Exception as e:
                errors.append(f"Outcome {outcome.id}: {str(e)}")

        workflow.logger.info(
            f"Individual processing complete: "
            f"{processed_count} processed, {len(new_deaths)} deaths"
        )

        return LearningLoopResult(
            processed_count=processed_count,
            updated_ideas=updated_ideas,
            new_deaths=new_deaths,
            component_updates=0,  # Not tracked in individual mode
            premise_updates=0,
            fatigue_updates=processed_count,  # Each outcome updates fatigue
            errors=errors,
        )
