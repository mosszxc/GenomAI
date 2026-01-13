"""
Modular Hypothesis Workflow

Orchestrates modular hypothesis generation:
1. Check if enough modules exist
2. Select top module combinations (hook → promise → proof)
3. LLM synthesis for each combination
4. Save hypotheses with review_status=pending_review

Part of Modular Creative System (Phase 3).
"""

from datetime import timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.modular_generation import (
        check_modular_readiness,
        select_module_combinations,
        synthesize_hypothesis_text,
        save_modular_hypothesis,
    )


@dataclass
class ModularHypothesisInput:
    """Input for ModularHypothesisWorkflow"""

    idea_id: str
    decision_id: str
    count: int = 3
    vertical: Optional[str] = None
    geo: Optional[str] = None
    buyer_id: Optional[str] = None


@dataclass
class ModularHypothesisResult:
    """Result from ModularHypothesisWorkflow"""

    success: bool
    hypotheses_count: int
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    combinations_used: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


# Retry policy for modular generation
MODULAR_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
    maximum_attempts=3,
)

# Retry policy for LLM calls (longer timeouts)
LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=2,
)


@workflow.defn
class ModularHypothesisWorkflow:
    """
    Modular Hypothesis Generation Workflow

    Generates hypotheses by combining top-performing modules.
    Uses 90/10 exploitation/exploration split for diversity.
    LLM synthesizes coherent ad text from module components.

    Hypotheses are created with:
    - generation_mode = 'modular'
    - review_status = 'pending_review'
    """

    @workflow.run
    async def run(self, input: ModularHypothesisInput) -> ModularHypothesisResult:
        """
        Main workflow execution.

        Steps:
        1. Check modular generation readiness
        2. Select module combinations
        3. For each combination: LLM synthesis + save
        """
        workflow.logger.info(
            f"Starting ModularHypothesisWorkflow for idea={input.idea_id}, count={input.count}"
        )

        # Step 1: Check readiness
        readiness = await workflow.execute_activity(
            check_modular_readiness,
            args=[input.vertical, input.geo],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=MODULAR_RETRY_POLICY,
        )

        if not readiness.get("ready", False):
            reason = readiness.get("reason", "Unknown reason")
            workflow.logger.warning(f"Modular generation not ready: {reason}")
            return ModularHypothesisResult(
                success=False,
                hypotheses_count=0,
                error=f"Not ready: {reason}",
            )

        workflow.logger.info(
            f"Modules available: "
            f"hooks={readiness['hooks_count']}, "
            f"promises={readiness['promises_count']}, "
            f"proofs={readiness['proofs_count']}"
        )

        # Step 2: Select module combinations
        combinations = await workflow.execute_activity(
            select_module_combinations,
            args=[input.count, input.vertical, input.geo],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=MODULAR_RETRY_POLICY,
        )

        if not combinations:
            workflow.logger.warning("No module combinations available")
            return ModularHypothesisResult(
                success=False,
                hypotheses_count=0,
                error="No valid combinations found",
            )

        workflow.logger.info(f"Selected {len(combinations)} module combinations")

        # Step 3: Synthesize and save each hypothesis
        hypotheses = []
        combinations_used = []
        errors = []

        for i, combo in enumerate(combinations):
            try:
                workflow.logger.info(
                    f"Processing combination {i + 1}/{len(combinations)}: "
                    f"hook={combo['hook']['id'][:8]}..."
                )

                # LLM synthesis
                synthesized_text = await workflow.execute_activity(
                    synthesize_hypothesis_text,
                    args=[combo["hook"], combo["promise"], combo["proof"]],
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=LLM_RETRY_POLICY,
                )

                # Save hypothesis
                hypothesis = await workflow.execute_activity(
                    save_modular_hypothesis,
                    args=[
                        synthesized_text,
                        input.idea_id,
                        input.decision_id,
                        combo["hook"]["id"],
                        combo["promise"]["id"],
                        combo["proof"]["id"],
                        input.buyer_id,
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=MODULAR_RETRY_POLICY,
                )

                hypotheses.append(hypothesis)
                combinations_used.append(
                    {
                        "hook_id": combo["hook"]["id"],
                        "promise_id": combo["promise"]["id"],
                        "proof_id": combo["proof"]["id"],
                        "combined_score": combo.get("combined_score", 0),
                    }
                )

                workflow.logger.info(
                    f"Hypothesis {hypothesis['id']} created (review_status=pending_review)"
                )

            except Exception as e:
                error_msg = f"Combination {i + 1} failed: {str(e)}"
                workflow.logger.error(error_msg)
                errors.append(error_msg)
                continue

        # Final result
        success = len(hypotheses) > 0

        if errors:
            workflow.logger.warning(f"Completed with {len(errors)} errors: {errors}")

        workflow.logger.info(
            f"ModularHypothesisWorkflow complete: "
            f"{len(hypotheses)}/{len(combinations)} hypotheses generated"
        )

        return ModularHypothesisResult(
            success=success,
            hypotheses_count=len(hypotheses),
            hypotheses=hypotheses,
            combinations_used=combinations_used,
            error="; ".join(errors) if errors else None,
        )
