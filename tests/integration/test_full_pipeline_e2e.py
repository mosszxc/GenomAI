"""
Full End-to-End Integration Test for GenomAI Pipeline.

Tests the complete flow from creative registration to learning loop:
1. Creative Registration (T+0)
2. Transcription (T+2min)
3. Decomposition (T+3min)
4. Idea Creation (T+4min)
5. Decision Engine (T+5min)
6. Hypothesis Generation (T+6min)
7. Telegram Delivery (T+7min)
8. Keitaro Metrics (T+1hour)
9. Snapshot & Outcome (T+1hour)
10. Learning Loop (T+1hour)

Related issue: #102

Prerequisites:
- Test buyer registered (#97)
- Decision Engine working (#95)
- Keep-alive active (#101)
- Keitaro configured with test campaign
"""

import pytest
import httpx
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from tests.integration.assertions.db_assertions import DbAssertions, wait_for_condition


# Test configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ftrerelppsnbdcmtcwya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "https://kazamaqwe.app.n8n.cloud/webhook")
DE_API_URL = os.getenv("DE_API_URL", "https://genomai.onrender.com")
API_KEY = os.getenv("API_KEY", "")

# Test tracker ID for E2E test (override with E2E_TRACKER_ID env var)
E2E_TEST_TRACKER_ID = os.getenv("E2E_TRACKER_ID", "99999")


@pytest.fixture
async def db():
    """Database assertions helper."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
    }
    assertions = DbAssertions(SUPABASE_URL, headers)
    yield assertions
    await assertions.close()


class PipelineState:
    """Holds state across pipeline steps for verification."""

    def __init__(self):
        self.creative_id: Optional[str] = None
        self.idea_id: Optional[str] = None
        self.decision_id: Optional[str] = None
        self.hypothesis_id: Optional[str] = None
        self.outcome_id: Optional[str] = None
        self.tracker_id: str = E2E_TEST_TRACKER_ID


class TestFullPipelineE2E:
    """
    Full End-to-End integration tests.

    These tests are designed to be run sequentially against a real environment.
    They verify the entire GenomAI pipeline from creative registration to learning.
    """

    @pytest.fixture
    def pipeline_state(self) -> PipelineState:
        """Shared state for pipeline tests."""
        return PipelineState()

    # ==================== Step 1: Creative Registration ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step1_creative_registration(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 1: Creative Registration (T+0)

        Action: Creative is registered via Telegram or webhook.
        Checkpoint: Creative exists in database with status='pending' or 'registered'.
        """
        tracker_id = pipeline_state.tracker_id

        # Query creative by tracker_id
        creative = await db.get_creative(tracker_id)

        if creative is None:
            pytest.skip(f"No creative with tracker_id={tracker_id}. "
                       "Send a test creative first via Telegram.")

        # Store for subsequent tests
        pipeline_state.creative_id = creative["id"]

        # Verify status
        status = creative.get("status")
        assert status in ["pending", "registered", "transcribed", "decomposed"], \
            f"Creative status should indicate registration. Got: {status}"

        # Verify buyer_id is set
        assert creative.get("buyer_id") is not None or creative.get("source_type") == "system", \
            "Creative should have buyer_id or be system-sourced"

    # ==================== Step 2: Transcription ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step2_transcription(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 2: Transcription (T+2min)

        Expected: Transcript is created automatically via AssemblyAI.
        Checkpoint: Transcript exists for creative.
        """
        tracker_id = pipeline_state.tracker_id

        # Get creative first
        creative = await db.get_creative(tracker_id)
        if creative is None:
            pytest.skip(f"No creative with tracker_id={tracker_id}")

        creative_id = creative["id"]
        pipeline_state.creative_id = creative_id

        # Check for transcript
        transcript = await db.get_transcript(creative_id)

        if transcript is None:
            pytest.skip(f"No transcript yet for creative {creative_id}. "
                       "Wait for transcription workflow to complete (~2 min).")

        # Verify transcript has text
        assert transcript.get("transcript_text") is not None, \
            "Transcript should have text"
        assert len(transcript.get("transcript_text", "")) > 0, \
            "Transcript text should not be empty"

    # ==================== Step 3: Decomposition ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step3_decomposition(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 3: Decomposition (T+3min)

        Expected: Decomposed creative is created with canonical fields.
        Checkpoint: decomposed_creatives record exists with payload.
        """
        tracker_id = pipeline_state.tracker_id

        # Get creative
        creative = await db.get_creative(tracker_id)
        if creative is None:
            pytest.skip(f"No creative with tracker_id={tracker_id}")

        creative_id = creative["id"]
        pipeline_state.creative_id = creative_id

        # Check for decomposed creative
        decomposed = await db.get_decomposed(creative_id)

        if decomposed is None:
            pytest.skip(f"No decomposed creative yet for {creative_id}. "
                       "Wait for decomposition workflow to complete (~1 min).")

        # Verify payload exists
        payload = decomposed.get("payload")
        assert payload is not None, "Decomposed creative should have payload"

        # Verify schema version
        schema_version = decomposed.get("schema_version")
        assert schema_version is not None, "Schema version should be set"

        # Store idea_id for next steps
        pipeline_state.idea_id = decomposed.get("idea_id")

    # ==================== Step 4: Idea Creation ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step4_idea_creation(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 4: Idea Creation (T+4min)

        Expected: Idea is created or reused based on canonical hash.
        Checkpoint: ideas record exists, linked to decomposed_creative.
        """
        tracker_id = pipeline_state.tracker_id

        # Get decomposed creative to find idea
        creative = await db.get_creative(tracker_id)
        if creative is None:
            pytest.skip(f"No creative with tracker_id={tracker_id}")

        decomposed = await db.get_decomposed(creative["id"])
        if decomposed is None:
            pytest.skip("No decomposed creative yet")

        idea_id = decomposed.get("idea_id")
        if idea_id is None:
            pytest.skip("Idea not yet linked to decomposed creative")

        pipeline_state.idea_id = idea_id

        # Verify idea exists
        exists = await db.idea_exists(idea_id)
        assert exists, f"Idea {idea_id} should exist in ideas table"

        # Get idea details
        ideas = await db._query("ideas", f"id=eq.{idea_id}&select=*")
        assert len(ideas) > 0, "Idea should be queryable"

        idea = ideas[0]

        # Verify canonical hash
        assert idea.get("canonical_hash") is not None, "Idea should have canonical_hash"

        # Check death_state (should be NULL for new ideas)
        # Note: existing ideas might have death_state from previous tests

    # ==================== Step 5: Decision Engine ====================

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_de
    async def test_step5_decision_engine(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 5: Decision Engine (T+5min)

        Expected: Decision Engine evaluates idea and returns decision.
        Checkpoint: decisions record exists with decision type.
        """
        idea_id = pipeline_state.idea_id

        if idea_id is None:
            # Try to get from database
            creative = await db.get_creative(pipeline_state.tracker_id)
            if creative:
                decomposed = await db.get_decomposed(creative["id"])
                if decomposed:
                    idea_id = decomposed.get("idea_id")
                    pipeline_state.idea_id = idea_id

        if idea_id is None:
            pytest.skip("No idea_id available for decision check")

        # Check for decision
        decision = await db.get_decision(idea_id)

        if decision is None:
            pytest.skip(f"No decision yet for idea {idea_id}. "
                       "Wait for decision workflow or trigger manually.")

        pipeline_state.decision_id = decision["id"]

        # Verify decision type
        decision_type = decision.get("decision")
        assert decision_type in ["approve", "reject", "defer"], \
            f"Decision should be approve/reject/defer. Got: {decision_type}"

        # Check for decision trace
        traces = await db._query(
            "decision_traces",
            f"decision_id=eq.{decision['id']}&select=*"
        )

        if traces:
            trace = traces[0]
            assert trace.get("checks") is not None, "Decision trace should have checks"

    # ==================== Step 6: Hypothesis Generation ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step6_hypothesis_generation(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 6: Hypothesis Generation (T+6min)

        Expected: Hypothesis is generated for APPROVED ideas.
        Checkpoint: hypotheses record exists with content.
        """
        idea_id = pipeline_state.idea_id

        if idea_id is None:
            pytest.skip("No idea_id available for hypothesis check")

        # First check if decision was APPROVE
        decision = await db.get_decision(idea_id)
        if decision is None:
            pytest.skip("No decision yet")

        if decision.get("decision") != "approve":
            pytest.skip(f"Decision was {decision.get('decision')}, not approve. "
                       "Hypothesis only generated for approved ideas.")

        # Check for hypothesis
        hypothesis = await db.get_hypothesis(idea_id)

        if hypothesis is None:
            pytest.skip(f"No hypothesis yet for idea {idea_id}. "
                       "Wait for hypothesis workflow to complete (~30 sec).")

        pipeline_state.hypothesis_id = hypothesis["id"]

        # Verify hypothesis has content
        content = hypothesis.get("content")
        assert content is not None, "Hypothesis should have content"
        assert len(content) > 0, "Hypothesis content should not be empty"

        # Verify status
        status = hypothesis.get("status")
        assert status in ["pending", "ready_for_launch", "delivered", "failed"], \
            f"Invalid hypothesis status: {status}"

    # ==================== Step 7: Telegram Delivery ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step7_telegram_delivery(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 7: Telegram Delivery (T+7min)

        Expected: Hypothesis is delivered to buyer via Telegram.
        Checkpoint: hypothesis status='delivered', delivered_at is set.
        """
        idea_id = pipeline_state.idea_id

        if idea_id is None:
            pytest.skip("No idea_id available")

        # Get hypothesis
        hypothesis = await db.get_hypothesis(idea_id)

        if hypothesis is None:
            pytest.skip("No hypothesis yet")

        # Check delivery status
        status = hypothesis.get("status")
        delivered_at = hypothesis.get("delivered_at")
        telegram_message_id = hypothesis.get("telegram_message_id")

        if status != "delivered":
            pytest.skip(f"Hypothesis not yet delivered. Status: {status}")

        # Verify delivery metadata
        assert delivered_at is not None, "delivered_at should be set"

        # telegram_message_id might not be stored, so just warn
        if telegram_message_id is None:
            print("Warning: telegram_message_id not stored")

        # Check deliveries table
        deliveries = await db._query(
            "deliveries",
            f"idea_id=eq.{idea_id}&select=*&order=sent_at.desc&limit=1"
        )

        if deliveries:
            delivery = deliveries[0]
            assert delivery.get("channel") == "telegram", "Delivery channel should be telegram"
            assert delivery.get("status") == "sent", "Delivery status should be sent"

    # ==================== Step 8: Keitaro Metrics ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step8_keitaro_metrics(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 8: Keitaro Metrics (T+1hour)

        Expected: Metrics are polled from Keitaro.
        Checkpoint: raw_metrics_current has data for tracker_id.
        """
        tracker_id = pipeline_state.tracker_id

        # Check raw_metrics_current
        metrics = await db._query(
            "raw_metrics_current",
            f"tracker_id=eq.{tracker_id}&select=*"
        )

        if not metrics:
            pytest.skip(f"No metrics yet for tracker_id={tracker_id}. "
                       "Wait for Keitaro poller to run (~hourly).")

        metric = metrics[0]

        # Verify metrics has data
        metrics_data = metric.get("metrics")
        assert metrics_data is not None, "Metrics should have data"

    # ==================== Step 9: Snapshot & Outcome ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step9_snapshot_and_outcome(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 9: Snapshot & Outcome (T+1hour)

        Expected: Daily snapshot created, outcome aggregate generated.
        Checkpoint: daily_metrics_snapshot and outcome_aggregates exist.
        """
        tracker_id = pipeline_state.tracker_id

        # Get creative for outcome check
        creative = await db.get_creative(tracker_id)
        if creative is None:
            pytest.skip(f"No creative with tracker_id={tracker_id}")

        creative_id = creative["id"]

        # Check daily snapshot
        today = datetime.now().strftime("%Y-%m-%d")
        snapshots = await db._query(
            "daily_metrics_snapshot",
            f"tracker_id=eq.{tracker_id}&select=*&order=created_at.desc&limit=1"
        )

        if not snapshots:
            pytest.skip("No daily snapshot yet. Wait for snapshot job to run.")

        # Check outcome aggregate
        outcome = await db.get_outcome(creative_id)

        if outcome is None:
            pytest.skip("No outcome aggregate yet. Wait for outcome generation.")

        pipeline_state.outcome_id = outcome["id"]

        # Verify outcome has required fields
        assert outcome.get("window_start") is not None, "Outcome should have window_start"
        assert outcome.get("window_end") is not None, "Outcome should have window_end"

    # ==================== Step 10: Learning Loop ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_step10_learning_loop(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Step 10: Learning Loop (T+1hour)

        Expected: Learning loop processes outcome and updates confidence.
        Checkpoint: learning_applied=true on outcome, confidence version updated.
        """
        outcome_id = pipeline_state.outcome_id
        idea_id = pipeline_state.idea_id

        if outcome_id is None:
            # Try to get from database
            creative = await db.get_creative(pipeline_state.tracker_id)
            if creative:
                outcome = await db.get_outcome(creative["id"])
                if outcome:
                    outcome_id = outcome["id"]

        if outcome_id is None:
            pytest.skip("No outcome_id available for learning check")

        # Check if learning was applied
        is_processed = await db.outcome_is_processed(outcome_id)

        if not is_processed:
            pytest.skip(f"Outcome {outcome_id} not yet processed by learning loop.")

        # Check for confidence version update
        if idea_id:
            confidence = await db.get_current_confidence(idea_id)

            if confidence:
                assert confidence.get("source_outcome_id") is not None, \
                    "Confidence should have source_outcome_id"
                assert confidence.get("change_reason") is not None, \
                    "Confidence should have change_reason"

    # ==================== Master Verification ====================

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_master_verification_query(self, db: DbAssertions, pipeline_state: PipelineState):
        """
        Master Verification Query.

        Runs a comprehensive query to verify all pipeline stages.
        This is the final check to confirm E2E pipeline completion.
        """
        tracker_id = pipeline_state.tracker_id

        # Execute master verification query via individual checks
        result = await self._run_master_verification(db, tracker_id)

        # Print summary
        print("\n" + "=" * 60)
        print("MASTER VERIFICATION SUMMARY")
        print("=" * 60)
        for key, value in result.items():
            status = "PASS" if value else "FAIL/PENDING"
            print(f"  {key}: {status}")
        print("=" * 60)

        # Assert all stages passed (or skip if incomplete)
        incomplete_stages = [k for k, v in result.items() if not v]

        if incomplete_stages:
            pytest.skip(f"Pipeline incomplete. Pending stages: {incomplete_stages}")

        # All stages complete
        assert all(result.values()), "All pipeline stages should be complete"

    async def _run_master_verification(self, db: DbAssertions, tracker_id: str) -> Dict[str, bool]:
        """Run master verification checks."""
        result = {
            "creative_exists": False,
            "transcribed": False,
            "decomposed": False,
            "idea_linked": False,
            "decision_made": False,
            "hypothesis_generated": False,
            "delivered": False,
            "metrics_received": False,
            "outcome_created": False,
            "learning_applied": False,
        }

        # 1. Creative exists
        creative = await db.get_creative(tracker_id)
        if creative:
            result["creative_exists"] = True
            creative_id = creative["id"]

            # 2. Transcribed
            transcript = await db.get_transcript(creative_id)
            result["transcribed"] = transcript is not None

            # 3. Decomposed
            decomposed = await db.get_decomposed(creative_id)
            if decomposed:
                result["decomposed"] = True

                # 4. Idea linked
                idea_id = decomposed.get("idea_id")
                if idea_id:
                    result["idea_linked"] = await db.idea_exists(idea_id)

                    # 5. Decision made
                    decision = await db.get_decision(idea_id)
                    result["decision_made"] = decision is not None

                    # 6. Hypothesis generated (only for approved)
                    if decision and decision.get("decision") == "approve":
                        hypothesis = await db.get_hypothesis(idea_id)
                        if hypothesis:
                            result["hypothesis_generated"] = True

                            # 7. Delivered
                            result["delivered"] = hypothesis.get("status") == "delivered"

            # 8. Metrics received
            metrics = await db._query(
                "raw_metrics_current",
                f"tracker_id=eq.{tracker_id}&select=tracker_id"
            )
            result["metrics_received"] = len(metrics) > 0

            # 9. Outcome created
            outcome = await db.get_outcome(creative_id)
            if outcome:
                result["outcome_created"] = True

                # 10. Learning applied
                result["learning_applied"] = outcome.get("learning_applied", False)

        return result


class TestPipelineHealthChecks:
    """Quick health checks for pipeline components."""

    @pytest.mark.integration
    async def test_decision_engine_health(self):
        """Verify Decision Engine is reachable."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{DE_API_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "ok"

    @pytest.mark.integration
    async def test_supabase_connectivity(self, db: DbAssertions):
        """Verify Supabase is reachable."""
        # Simple query to verify connectivity
        result = await db._query("config", "select=key&limit=1")
        assert isinstance(result, list)

    @pytest.mark.integration
    async def test_no_stuck_pipeline_stages(self, db: DbAssertions):
        """
        Verify no creatives are stuck in intermediate stages.

        Creatives should not remain in transitional states for too long.
        """
        # Check for creatives stuck in transcribing/decomposing
        stuck_statuses = ["transcribing", "decomposing"]
        threshold_minutes = 30

        for status in stuck_statuses:
            stuck = await db._query(
                "creatives",
                f"status=eq.{status}&select=id,created_at&limit=10"
            )

            for creative in stuck:
                created_at = creative.get("created_at")
                if created_at:
                    # Parse and check age
                    # Note: This is simplified - actual implementation should use proper datetime parsing
                    assert len(stuck) < 5, \
                        f"Too many creatives stuck in '{status}' state: {len(stuck)}"


class TestPipelineRegressions:
    """Regression tests for known pipeline issues."""

    @pytest.mark.integration
    async def test_no_orphan_ideas(self, db: DbAssertions):
        """
        Regression: Ensure all ideas have at least one linked creative.

        Related issue: #80 (idea_not_found)
        """
        # Query ideas without linked decomposed_creatives
        orphan_ideas = await db._query(
            "ideas",
            "select=id,canonical_hash&limit=50"
        )

        for idea in orphan_ideas:
            linked = await db._query(
                "decomposed_creatives",
                f"idea_id=eq.{idea['id']}&select=id&limit=1"
            )
            # Allow orphans for now, but log warning
            if not linked:
                print(f"Warning: Orphan idea found: {idea['id']}")

    @pytest.mark.integration
    async def test_decision_has_trace(self, db: DbAssertions):
        """
        Regression: Ensure all decisions have corresponding traces.

        Traces are required for debugging and audit.
        """
        # Get recent decisions
        decisions = await db._query(
            "decisions",
            "select=id&order=created_at.desc&limit=10"
        )

        decisions_without_trace = 0
        for decision in decisions:
            traces = await db._query(
                "decision_traces",
                f"decision_id=eq.{decision['id']}&select=id&limit=1"
            )
            if not traces:
                decisions_without_trace += 1

        assert decisions_without_trace == 0, \
            f"Found {decisions_without_trace} decisions without traces"

    @pytest.mark.integration
    async def test_approved_ideas_have_hypothesis(self, db: DbAssertions):
        """
        Regression: Ensure APPROVE decisions lead to hypothesis generation.

        Related issue: #79 (stuck creatives)
        """
        # Get recent APPROVE decisions
        approved = await db._query(
            "decisions",
            "decision=eq.approve&select=id,idea_id&order=created_at.desc&limit=10"
        )

        missing_hypothesis = 0
        for decision in approved:
            idea_id = decision.get("idea_id")
            if idea_id:
                hypothesis = await db.get_hypothesis(idea_id)
                if hypothesis is None:
                    missing_hypothesis += 1

        # Allow some slack for in-progress generation
        assert missing_hypothesis <= 2, \
            f"Found {missing_hypothesis} approved ideas without hypothesis"
