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
from typing import Optional
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
            # Import activities inside workflow with pass-through to avoid sandbox restrictions
            with workflow.unsafe.imports_passed_through():
                from temporal.activities.supabase import (
                    get_creative,
                    save_decomposed_creative,
                    check_idea_exists,
                    create_idea,
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
                from temporal.activities.telegram import (
                    send_hypothesis_to_telegram,
                    get_buyer_chat_id,
                    emit_delivery_event,
                )

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
            assemblyai_transcript_id: str = None
            saved_transcript_id: str = None

            if existing_transcript:
                # RECOVERY: Use existing transcript, skip AssemblyAI (saves time & money)
                transcript_text = existing_transcript.get("transcript_text", "")
                assemblyai_transcript_id = existing_transcript.get(
                    "assemblyai_transcript_id"
                )
                saved_transcript_id = existing_transcript.get("id")
                workflow.logger.info(
                    f"Using existing transcript version={existing_transcript.get('version')} "
                    f"for creative={input.creative_id}"
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
                    audio_url,
                    None,  # language_code - auto-detect
                    start_to_close_timeout=timedelta(minutes=15),
                    heartbeat_timeout=timedelta(seconds=60),
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
                    input.creative_id,
                    transcript_text,
                    assemblyai_transcript_id,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                saved_transcript_id = saved_transcript.get("id")

                # Emit transcription event
                await workflow.execute_activity(
                    emit_event,
                    "TranscriptCreated",
                    {
                        "creative_id": input.creative_id,
                        "transcript_id": saved_transcript_id,
                        "assemblyai_transcript_id": assemblyai_transcript_id,
                        "version": saved_transcript.get("version", 1),
                        "words": len(transcript_text.split()) if transcript_text else 0,
                    },
                    start_to_close_timeout=timedelta(seconds=10),
                )

            # Step 3: LLM Decomposition (OpenAI)
            self._status = "decomposing"
            decomposition_result = await workflow.execute_activity(
                decompose_creative,
                transcript_text,
                input.creative_id,
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=default_retry,
            )

            decomposition_payload = decomposition_result["payload"]
            canonical_hash = decomposition_result["canonical_hash"]

            # Save decomposed creative
            decomposed = await workflow.execute_activity(
                save_decomposed_creative,
                input.creative_id,
                decomposition_payload,
                canonical_hash,
                saved_transcript_id,  # DB transcript ID (not AssemblyAI ID)
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Emit decomposition event
            await workflow.execute_activity(
                emit_event,
                "CreativeDecomposed",
                {
                    "creative_id": input.creative_id,
                    "decomposed_creative_id": decomposed["id"],
                    "canonical_hash": canonical_hash,
                    "schema_version": decomposition_result["schema_version"],
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

            # Emit idea event
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

            # Emit decision event
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

                # Generate hypotheses
                hypothesis_result = await workflow.execute_activity(
                    generate_hypotheses,
                    self._idea_id,
                    decision_result.decision_id,
                    decomposition_payload,
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=default_retry,
                )

                # Save hypotheses with variables from decomposition
                saved_hypotheses = await workflow.execute_activity(
                    save_hypotheses,
                    hypothesis_result["hypotheses"],
                    self._idea_id,
                    decision_result.decision_id,
                    hypothesis_result["prompt_version"],
                    decomposition_payload,  # Pass variables for denormalization
                    input.buyer_id,  # Propagate buyer_id for delivery routing
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

                self._hypothesis_count = len(saved_hypotheses)

                # Emit hypothesis event
                await workflow.execute_activity(
                    emit_event,
                    "HypothesisGenerated",
                    {
                        "idea_id": self._idea_id,
                        "decision_id": decision_result.decision_id,
                        "count": self._hypothesis_count,
                    },
                    start_to_close_timeout=timedelta(seconds=10),
                )

                # Step 7: Telegram Delivery (only for APPROVE with buyer)
                if input.buyer_id and saved_hypotheses:
                    self._status = "delivering_telegram"

                    # Get buyer's chat ID
                    chat_id = await workflow.execute_activity(
                        get_buyer_chat_id,
                        input.buyer_id,
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=default_retry,
                    )

                    if chat_id:
                        # Send first hypothesis to Telegram
                        first_hypothesis = saved_hypotheses[0]
                        hypothesis_id = first_hypothesis["id"]

                        delivery_result = await workflow.execute_activity(
                            send_hypothesis_to_telegram,
                            hypothesis_id,
                            first_hypothesis["content"],
                            chat_id,
                            self._idea_id,
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=default_retry,
                        )

                        # Emit delivery event
                        await workflow.execute_activity(
                            emit_delivery_event,
                            hypothesis_id,
                            self._idea_id,
                            delivery_result["status"],
                            start_to_close_timeout=timedelta(seconds=10),
                        )

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
        decision_id: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
    ) -> PipelineResult:
        """Build pipeline result."""
        return PipelineResult(
            creative_id=self._creative_id or "",
            idea_id=self._idea_id,
            idea_status=idea_status,
            decision_id=decision_id,
            decision_type=self._decision,
            hypothesis_id=hypothesis_id,
            hypothesis_count=self._hypothesis_count,
            completed_at=workflow.now(),  # Use workflow.now() for determinism
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
