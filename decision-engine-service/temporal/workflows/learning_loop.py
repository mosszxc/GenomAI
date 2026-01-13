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
    from temporal.activities.feature_monitoring import (
        UpdateCorrelationsInput,
        UpdateCorrelationsOutput,
        DetectDriftInput,
        DetectDriftOutput,
        EmitFeatureEventInput,
        update_feature_correlations,
        detect_feature_drift,
        emit_feature_event,
    )
    from temporal.activities.module_learning import (
        ProcessModuleLearningBatchInput,
        ProcessModuleLearningBatchOutput,
        process_module_learning_batch,
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
    module_updates: int = 0
    compatibility_updates: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


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
                f"{result.skipped_count} skipped (idempotent), "
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
                            "skipped_count": result.skipped_count,
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

            # Feature correlation monitoring (after processing outcomes)
            await self._run_feature_monitoring()

            # Module learning (update module stats and compatibility)
            module_result = await self._run_module_learning_batch()

            return LearningLoopResult(
                processed_count=result.processed_count,
                updated_ideas=result.updated_ideas,
                new_deaths=result.new_deaths,
                component_updates=result.component_updates,
                premise_updates=result.premise_updates,
                fatigue_updates=result.fatigue_updates,
                module_updates=module_result.get("modules_updated", 0),
                compatibility_updates=module_result.get("compatibilities_updated", 0),
                errors=result.errors + module_result.get("errors", []),
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
                module_updates=0,
                compatibility_updates=0,
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
            outcomes_result: GetUnprocessedOutcomesOutput = await workflow.execute_activity(
                get_unprocessed_outcomes,
                GetUnprocessedOutcomesInput(limit=input.batch_limit),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=LEARNING_RETRY_POLICY,
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
            f"Individual processing complete: {processed_count} processed, {len(new_deaths)} deaths"
        )

        # Feature correlation monitoring (after processing outcomes)
        await self._run_feature_monitoring()

        # Module learning (update module stats and compatibility)
        module_result = await self._run_module_learning_batch()

        return LearningLoopResult(
            processed_count=processed_count,
            updated_ideas=updated_ideas,
            new_deaths=new_deaths,
            component_updates=0,  # Not tracked in individual mode
            premise_updates=0,
            fatigue_updates=processed_count,  # Each outcome updates fatigue
            module_updates=module_result.get("modules_updated", 0),
            compatibility_updates=module_result.get("compatibilities_updated", 0),
            errors=errors + module_result.get("errors", []),
        )

    async def _run_feature_monitoring(self) -> None:
        """
        Run feature correlation monitoring after learning processing.

        1. Update correlations for all shadow/active features
        2. Auto-deprecate low correlation shadow features
        3. Detect drift for active features
        """
        workflow.logger.info("Running feature correlation monitoring")

        # Step 1: Update correlations and auto-deprecate
        try:
            corr_result: UpdateCorrelationsOutput = await workflow.execute_activity(
                update_feature_correlations,
                UpdateCorrelationsInput(),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=LEARNING_RETRY_POLICY,
            )

            workflow.logger.info(
                f"Feature correlations updated: {corr_result.updated_count} features, "
                f"{len(corr_result.deprecated_features)} auto-deprecated"
            )

            # Emit correlation update event
            if corr_result.updated_count > 0:
                await workflow.execute_activity(
                    emit_feature_event,
                    EmitFeatureEventInput(
                        event_type="feature.correlations.updated",
                        payload={
                            "updated_count": corr_result.updated_count,
                            "deprecated_features": corr_result.deprecated_features,
                            "features": [
                                {
                                    "name": r.feature_name,
                                    "correlation": r.correlation,
                                    "sample_size": r.sample_size,
                                }
                                for r in corr_result.results
                                if r.correlation is not None
                            ],
                        },
                    ),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=LEARNING_RETRY_POLICY,
                )

            # Emit deprecation events
            for feature_name in corr_result.deprecated_features:
                await workflow.execute_activity(
                    emit_feature_event,
                    EmitFeatureEventInput(
                        event_type="feature.auto_deprecated",
                        payload={"feature_name": feature_name},
                    ),
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=LEARNING_RETRY_POLICY,
                )

        except Exception as e:
            workflow.logger.error(f"Feature correlation update failed: {e}")

        # Step 2: Detect drift for active features
        try:
            drift_result: DetectDriftOutput = await workflow.execute_activity(
                detect_feature_drift,
                DetectDriftInput(),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=LEARNING_RETRY_POLICY,
            )

            if drift_result.drift_detected:
                workflow.logger.warning(
                    f"Feature drift detected: {len(drift_result.drift_detected)} features"
                )

                # Emit drift events
                for drift in drift_result.drift_detected:
                    await workflow.execute_activity(
                        emit_feature_event,
                        EmitFeatureEventInput(
                            event_type="feature.drift_detected",
                            payload={
                                "feature_name": drift.feature_name,
                                "historical_correlation": drift.historical_correlation,
                                "recent_correlation": drift.recent_correlation,
                                "drift": drift.drift,
                            },
                        ),
                        start_to_close_timeout=timedelta(seconds=15),
                        retry_policy=LEARNING_RETRY_POLICY,
                    )

        except Exception as e:
            workflow.logger.error(f"Feature drift detection failed: {e}")

    async def _run_module_learning_batch(self) -> dict:
        """
        Run module learning for recently processed outcomes.

        Updates module_bank stats and module_compatibility scores
        for all modules used in creatives that were just processed.

        Returns:
            Dict with modules_updated, compatibilities_updated, errors
        """
        workflow.logger.info("Running module learning batch")

        try:
            result: ProcessModuleLearningBatchOutput = await workflow.execute_activity(
                process_module_learning_batch,
                ProcessModuleLearningBatchInput(hours_lookback=2),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=LEARNING_RETRY_POLICY,
            )

            workflow.logger.info(
                f"Module learning complete: "
                f"{result.creatives_processed} creatives, "
                f"{result.modules_updated} modules, "
                f"{result.compatibilities_updated} compatibilities"
            )

            return {
                "modules_updated": result.modules_updated,
                "compatibilities_updated": result.compatibilities_updated,
                "errors": result.errors,
            }

        except Exception as e:
            workflow.logger.error(f"Module learning batch failed: {e}")
            return {
                "modules_updated": 0,
                "compatibilities_updated": 0,
                "errors": [str(e)],
            }
