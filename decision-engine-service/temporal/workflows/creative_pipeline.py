"""
Creative Pipeline Workflow

Main workflow that processes a creative through the entire pipeline:
1. Transcription (AssemblyAI)
2. Decomposition (LLM)
3. Idea Registry (create/reuse)
4. Decision Engine (4-check wall)
5. Hypothesis Generation (if approved)
6. Telegram Delivery (if approved)

Replaces 6 n8n workflows with single durable workflow.
"""

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models
with workflow.unsafe.imports_passed_through():
    from temporal.models.creative import CreativeInput, PipelineResult
    from temporal.models.decision import DecisionResult


@workflow.defn
class CreativePipelineWorkflow:
    """
    Main creative processing pipeline.

    Flow:
        Creative → Transcription → Decomposition → Idea → Decision → Hypothesis

    Replaces:
        - GenomAI - Creative Transcription
        - creative_decomposition_llm
        - idea_registry_create
        - decision_engine_mvp
        - hypothesis_factory_generate
        - Telegram Hypothesis Delivery
    """

    def __init__(self):
        self._status = "initialized"
        self._creative_id: str | None = None
        self._idea_id: str | None = None
        self._decision: str | None = None
        self._error: str | None = None

    @workflow.run
    async def run(self, input: CreativeInput) -> PipelineResult:
        """
        Execute the creative pipeline.

        Args:
            input: Creative input with creative_id and metadata

        Returns:
            PipelineResult with all pipeline outputs
        """
        self._creative_id = input.creative_id
        self._status = "started"

        try:
            # Import activities inside workflow
            from temporal.activities.supabase import (
                get_creative,
                save_decomposed_creative,
                check_idea_exists,
                create_idea,
                update_creative_status,
                emit_event,
            )
            from temporal.activities.decision_engine import make_decision

            # Default retry policy for most activities
            default_retry = RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
            )

            # Step 1: Load creative
            self._status = "loading_creative"
            creative = await workflow.execute_activity(
                get_creative,
                input.creative_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            if not creative:
                self._error = f"Creative {input.creative_id} not found"
                return self._build_result()

            # Step 2: Transcription (placeholder - will implement transcription activity)
            self._status = "transcribing"
            # TODO: Implement transcription activity with heartbeats
            # For now, assume transcript exists in creative
            transcript_text = creative.get("transcript", "")

            # Step 3: LLM Decomposition (placeholder - will implement LLM activity)
            self._status = "decomposing"
            # TODO: Implement LLM decomposition activity
            # For now, create minimal decomposition
            decomposition_payload = {
                "schema_version": "v1",
                "angle_type": "pain",
                "core_belief": "transformation",
                "promise_type": "result",
            }

            # Compute canonical hash
            import hashlib
            import json

            canonical_hash = hashlib.sha256(
                json.dumps(decomposition_payload, sort_keys=True).encode()
            ).hexdigest()

            # Save decomposed creative
            decomposed = await workflow.execute_activity(
                save_decomposed_creative,
                input.creative_id,
                decomposition_payload,
                canonical_hash,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Emit event
            await workflow.execute_activity(
                emit_event,
                "CreativeDecomposed",
                {
                    "creative_id": input.creative_id,
                    "decomposed_creative_id": decomposed["id"],
                    "canonical_hash": canonical_hash,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Step 4: Idea Registry
            self._status = "registering_idea"

            # Check if idea already exists
            existing_idea = await workflow.execute_activity(
                check_idea_exists,
                canonical_hash,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=default_retry,
            )

            idea_status = "reused"
            if existing_idea:
                self._idea_id = existing_idea["id"]
            else:
                idea_status = "new"
                new_idea = await workflow.execute_activity(
                    create_idea,
                    canonical_hash,
                    decomposed["id"],
                    input.buyer_id,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                self._idea_id = new_idea["id"]

            # Emit event
            await workflow.execute_activity(
                emit_event,
                "IdeaRegistered",
                {
                    "idea_id": self._idea_id,
                    "status": idea_status,
                    "canonical_hash": canonical_hash,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Step 5: Decision Engine
            self._status = "deciding"
            decision_result: DecisionResult = await workflow.execute_activity(
                make_decision,
                self._idea_id,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=default_retry,
            )

            self._decision = decision_result.decision_type

            # Emit event
            await workflow.execute_activity(
                emit_event,
                "DecisionMade",
                {
                    "idea_id": self._idea_id,
                    "decision_id": decision_result.decision_id,
                    "decision_type": decision_result.decision_type,
                    "decision_reason": decision_result.decision_reason,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Step 6: Hypothesis Generation (only for APPROVE)
            hypothesis_id = None
            if decision_result.is_approved:
                self._status = "generating_hypothesis"
                # TODO: Implement hypothesis generation activity
                # For now, skip hypothesis
                pass

            # Update creative status
            await workflow.execute_activity(
                update_creative_status,
                input.creative_id,
                "processed",
                start_to_close_timeout=timedelta(seconds=10),
            )

            self._status = "completed"
            return self._build_result(
                idea_status=idea_status,
                decision_id=decision_result.decision_id,
                hypothesis_id=hypothesis_id,
            )

        except Exception as e:
            self._status = "failed"
            self._error = str(e)
            return self._build_result()

    def _build_result(
        self,
        idea_status: str = "unknown",
        decision_id: str | None = None,
        hypothesis_id: str | None = None,
    ) -> PipelineResult:
        """Build pipeline result."""
        from datetime import datetime

        return PipelineResult(
            creative_id=self._creative_id or "",
            idea_id=self._idea_id,
            idea_status=idea_status,
            decision_id=decision_id,
            decision_type=self._decision,
            hypothesis_id=hypothesis_id,
            completed_at=datetime.utcnow(),
            error=self._error,
        )

    @workflow.query
    def get_status(self) -> str:
        """Query current workflow status."""
        return self._status

    @workflow.query
    def get_progress(self) -> dict:
        """Query workflow progress details."""
        return {
            "status": self._status,
            "creative_id": self._creative_id,
            "idea_id": self._idea_id,
            "decision": self._decision,
            "error": self._error,
        }
