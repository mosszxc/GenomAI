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

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models and activities at module level for deterministic replay
with workflow.unsafe.imports_passed_through():
    from temporal.models.creative import CreativeInput, PipelineResult
    from temporal.models.decision import DecisionResult
    from temporal.tracing import get_workflow_logger
    from temporal.activities.supabase import (
        get_creative,
        save_decomposed_creative,
        upsert_idea,
        update_creative_status,
        emit_event,
        save_transcript,
        get_existing_transcript,
    )
    from temporal.activities.decision_engine import make_decision
    from temporal.activities.transcription import transcribe_audio
    from temporal.activities.llm_decomposition import decompose_creative
    from temporal.activities.hypothesis_generation import (
        generate_hypotheses,
        save_hypotheses,
    )
    from temporal.activities.premise_selection import (
        select_premise,
    )
    from temporal.activities.module_extraction import (
        extract_modules_from_decomposition,
    )


@workflow.defn
class CreativePipelineWorkflow:
    """
    Main creative processing pipeline.

    Flow:
        Creative → Transcription → Decomposition → Idea → Decision → Hypothesis → Telegram

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
        self._creative_id: Optional[str] = None
        self._idea_id: Optional[str] = None
        self._decision: Optional[str] = None
        self._hypothesis_count: int = 0
        self._error: Optional[str] = None
        self._log = None  # Initialized in run() with context
        self._operation_start_time: Optional[datetime] = None  # For deterministic completed_at

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

        # Capture start time BEFORE try block for deterministic completed_at
        # This ensures workflow.now() is called in deterministic execution path
        self._operation_start_time = workflow.now()

        # Initialize structured logger with trace context
        self._log = get_workflow_logger(
            creative_id=input.creative_id,
            buyer_id=input.buyer_id,
        )
        self._log.info("Pipeline started", status=self._status)

        try:
            # Default retry policy for most activities
            default_retry = RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=3,
            )

            # Long-running activity retry (for transcription)
            long_running_retry = RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=2),
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

            # Step 2: Check for existing transcript (RECOVERY PATH)
            self._status = "checking_transcript"
            existing_transcript = await workflow.execute_activity(
                get_existing_transcript,
                input.creative_id,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=default_retry,
            )

            transcript_text: str
            assemblyai_transcript_id: str | None = None
            saved_transcript_id: str | None = None

            if existing_transcript:
                # RECOVERY: Use existing transcript, skip AssemblyAI (saves time & money)
                transcript_text = existing_transcript.get("transcript_text", "")
                assemblyai_transcript_id = existing_transcript.get("assemblyai_transcript_id")
                # Convert bigint id to string for type compatibility
                saved_transcript_id = str(existing_transcript["id"])
                self._log.info(
                    "Using existing transcript",
                    transcript_version=existing_transcript.get("version"),
                    transcript_id=saved_transcript_id,
                )
            else:
                # Step 2b: Transcription (AssemblyAI with heartbeats)
                self._status = "transcribing"
                audio_url = creative.get("media_url") or creative.get("video_url")

                if not audio_url:
                    self._error = "Creative has no media_url or video_url"
                    return self._build_result()

                transcription_result = await workflow.execute_activity(
                    transcribe_audio,
                    args=[
                        audio_url,
                        None,
                        input.creative_id,
                    ],  # url, language, creative_id
                    start_to_close_timeout=timedelta(minutes=15),
                    heartbeat_timeout=timedelta(minutes=5),
                    retry_policy=long_running_retry,
                )

                transcript_text = transcription_result.get("text", "")
                assemblyai_transcript_id = transcription_result.get("transcript_id")

                if not transcript_text:
                    self._error = "Transcription returned empty text"
                    return self._build_result()

                # Step 2c: SAVE TRANSCRIPT (critical for recovery)
                self._status = "saving_transcript"
                saved_transcript = await workflow.execute_activity(
                    save_transcript,
                    args=[input.creative_id, transcript_text, assemblyai_transcript_id],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                # Convert bigint id to string for type compatibility
                saved_transcript_id = str(saved_transcript["id"])

                # Emit transcription event
                await workflow.execute_activity(
                    emit_event,
                    args=[
                        "TranscriptCreated",
                        {
                            "creative_id": input.creative_id,
                            "transcript_id": saved_transcript_id,
                            "assemblyai_transcript_id": assemblyai_transcript_id,
                            "version": saved_transcript.get("version", 1),
                            "words": len(transcript_text.split()) if transcript_text else 0,
                        },
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                )

            # Step 3: LLM Decomposition (OpenAI)
            self._status = "decomposing"
            decomposition_result = await workflow.execute_activity(
                decompose_creative,
                args=[transcript_text, input.creative_id],
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=default_retry,
            )

            decomposition_payload = decomposition_result["payload"]
            canonical_hash = decomposition_result["canonical_hash"]

            # Save decomposed creative
            decomposed = await workflow.execute_activity(
                save_decomposed_creative,
                args=[
                    input.creative_id,
                    decomposition_payload,
                    canonical_hash,
                    saved_transcript_id,
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Emit decomposition event
            await workflow.execute_activity(
                emit_event,
                args=[
                    "CreativeDecomposed",
                    {
                        "creative_id": input.creative_id,
                        "decomposed_creative_id": decomposed["id"],
                        "canonical_hash": canonical_hash,
                        "schema_version": decomposition_result["schema_version"],
                    },
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Step 3.5: Module Extraction (Modular Creative System)
            # Extracts Hook, Promise, Proof modules from decomposed payload
            # Modules inherit metrics from source creative (cold start strategy)
            self._status = "extracting_modules"
            await workflow.execute_activity(
                extract_modules_from_decomposition,
                args=[
                    input.creative_id,
                    decomposed["id"],
                    decomposition_payload,
                    creative.get("vertical"),  # Optional vertical from creative
                    creative.get("geo"),  # Optional geo from creative
                ],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=default_retry,
            )

            # Step 4: Idea Registry (atomic upsert - fixes TOCTOU race condition #471)
            self._status = "registering_idea"

            # Atomically find or create idea by canonical_hash
            # Uses INSERT ... ON CONFLICT DO NOTHING pattern
            idea_result = await workflow.execute_activity(
                upsert_idea,
                args=[canonical_hash, decomposed["id"], input.buyer_id],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            self._idea_id = idea_result["id"]
            idea_status = "new" if idea_result.get("upsert_status") == "created" else "reused"

            # Emit idea event
            await workflow.execute_activity(
                emit_event,
                args=[
                    "IdeaRegistered",
                    {
                        "idea_id": self._idea_id,
                        "status": idea_status,
                        "canonical_hash": canonical_hash,
                    },
                ],
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

            # Emit decision event
            await workflow.execute_activity(
                emit_event,
                args=[
                    "DecisionMade",
                    {
                        "idea_id": self._idea_id,
                        "decision_id": decision_result.decision_id,
                        "decision_type": decision_result.decision_type,
                        "decision_reason": decision_result.decision_reason,
                    },
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Step 6: Hypothesis Generation (only for APPROVE with buyer)
            # Skip if no buyer_id to prevent orphaned hypotheses (#475)
            hypothesis_id = None
            if decision_result.is_approved and input.buyer_id:
                self._status = "generating_hypothesis"

                # Step 6a: Select premise for hypothesis generation
                # Uses Thompson Sampling: 75% exploit best, 25% explore
                premise_result = await workflow.execute_activity(
                    select_premise,
                    args=[
                        self._idea_id,
                        None,  # avatar_id
                        creative.get("geo"),  # geo from creative
                        creative.get("vertical"),  # vertical from creative
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

                selected_premise_id = premise_result.get("premise_id")

                self._log.info(
                    "Premise selected",
                    premise_id=selected_premise_id,
                    selection_reason=premise_result.get("selection_reason"),
                )

                # Step 6b: Generate hypotheses
                hypothesis_result = await workflow.execute_activity(
                    generate_hypotheses,
                    args=[
                        self._idea_id,
                        decision_result.decision_id,
                        decomposition_payload,
                    ],
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=default_retry,
                )

                # Step 6c: Save hypotheses with variables and premise_id
                saved_hypotheses = await workflow.execute_activity(
                    save_hypotheses,
                    args=[
                        hypothesis_result["hypotheses"],
                        self._idea_id,
                        decision_result.decision_id,
                        hypothesis_result["prompt_version"],
                        decomposition_payload,  # Pass variables for denormalization
                        input.buyer_id,  # Propagate buyer_id for delivery routing
                        selected_premise_id,  # Link hypothesis to premise
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

                self._hypothesis_count = len(saved_hypotheses)

                # Emit hypothesis event
                await workflow.execute_activity(
                    emit_event,
                    args=[
                        "HypothesisGenerated",
                        {
                            "idea_id": self._idea_id,
                            "decision_id": decision_result.decision_id,
                            "count": self._hypothesis_count,
                        },
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                )

            elif decision_result.is_approved:
                # APPROVE but no buyer_id - skip hypothesis to prevent orphans (#475)
                workflow.logger.info(
                    f"Skipping hypothesis generation: APPROVE but no buyer_id "
                    f"(idea_id={self._idea_id})"
                )

            # Update creative status
            await workflow.execute_activity(
                update_creative_status,
                args=[input.creative_id, "processed"],
                start_to_close_timeout=timedelta(seconds=10),
            )

            self._status = "completed"
            return self._build_result(
                idea_status=idea_status,
                decision_id=decision_result.decision_id,
                hypothesis_id=hypothesis_id,
            )

        except Exception as e:
            failed_at_stage = self._status  # Capture stage before overwriting
            self._status = "failed"
            self._error = str(e)

            # CRITICAL: Mark creative as failed in DB (Issue #472)
            # Without this, creative stays in 'processing' forever
            try:
                await workflow.execute_activity(
                    update_creative_status,
                    args=[input.creative_id, "failed", str(e)],
                    start_to_close_timeout=timedelta(seconds=30),
                )

                # Emit failure event for monitoring
                await workflow.execute_activity(
                    emit_event,
                    args=[
                        "CreativeFailed",
                        {
                            "creative_id": input.creative_id,
                            "error": str(e)[:500],
                            "failed_at_stage": failed_at_stage,
                        },
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                )
            except Exception as e:
                # Don't fail the workflow if status update fails
                # The workflow result already contains the error
                workflow.logger.warning(f"Failed to update creative status to 'failed': {e}")

            return self._build_result()

    def _build_result(
        self,
        idea_status: str = "unknown",
        decision_id: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
    ) -> PipelineResult:
        """Build pipeline result."""
        # Use pre-captured time to ensure determinism during replay
        # workflow.now() in exception handlers can cause non-determinism errors
        completed_at = self._operation_start_time or workflow.now()
        return PipelineResult(
            creative_id=self._creative_id or "",
            idea_id=self._idea_id,
            idea_status=idea_status,
            decision_id=decision_id,
            decision_type=self._decision,
            hypothesis_id=hypothesis_id,
            hypothesis_count=self._hypothesis_count,
            completed_at=completed_at,
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
            "hypothesis_count": self._hypothesis_count,
            "error": self._error,
        }
