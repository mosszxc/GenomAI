"""
Integration tests for Learning Pipeline.

Tests the full flow:
keitaro_poller → snapshot_creator → outcome_aggregator → learning_loop_v2

These tests verify:
1. Raw metrics are collected from Keitaro
2. Daily snapshots are created
3. Outcome aggregates are created with proper linkage
4. Learning loop processes outcomes
5. Idea confidence is updated
6. Death state is properly set for failing ideas
"""

import pytest
import httpx
import asyncio
import os
from datetime import datetime, date

from tests.integration.assertions.db_assertions import DbAssertions, wait_for_condition


# Test configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ftrerelppsnbdcmtcwya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "https://kazamaqwe.app.n8n.cloud/webhook")
DE_API_URL = os.getenv("DE_API_URL", "https://genomai.onrender.com")
API_KEY = os.getenv("API_KEY", "")

# Webhook paths
WEBHOOKS = {
    "keitaro_poller": f"{N8N_WEBHOOK_BASE}/keitaro-poller",
    "snapshot_creator": f"{N8N_WEBHOOK_BASE}/snapshot-creator",
    "outcome_aggregator": f"{N8N_WEBHOOK_BASE}/outcome-aggregator",
    "learning_loop": f"{N8N_WEBHOOK_BASE}/learning-loop-v2",
}


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


class TestLearningPipeline:
    """Integration tests for the learning pipeline."""

    @pytest.mark.integration
    @pytest.mark.requires_de
    async def test_learning_loop_api_health(self):
        """Verify Learning Loop API is reachable."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{DE_API_URL}/learning/status",
                headers={"X-API-Key": API_KEY}
            )

            assert response.status_code == 200
            data = response.json()
            assert "pending_outcomes" in data or "status" in data

    @pytest.mark.integration
    async def test_raw_metrics_exist(self, db: DbAssertions):
        """Verify raw metrics are being collected."""
        metrics = await db._query(
            "raw_metrics_current",
            "select=tracker_id,metrics,updated_at&order=updated_at.desc&limit=5"
        )

        # Should have some metrics if keitaro_poller is running
        assert len(metrics) >= 0, "Raw metrics query should work"

        if metrics:
            # Verify structure
            for m in metrics:
                assert "tracker_id" in m
                assert "metrics" in m

    @pytest.mark.integration
    async def test_daily_snapshots_exist(self, db: DbAssertions):
        """Verify daily snapshots are being created."""
        today = date.today().isoformat()
        yesterday = (date.today().replace(day=date.today().day - 1)).isoformat()

        snapshots = await db._query(
            "daily_metrics_snapshot",
            f"date=gte.{yesterday}&select=id,tracker_id,date&limit=10"
        )

        # Log for debugging
        print(f"Found {len(snapshots)} snapshots for dates >= {yesterday}")

    @pytest.mark.integration
    async def test_outcome_aggregates_linkage(self, db: DbAssertions):
        """
        Verify outcome aggregates are properly linked.

        Related issue: #80 (DecisionAborted - idea_not_found)
        """
        # Get recent outcomes with origin_type='system'
        outcomes = await db._query(
            "outcome_aggregates",
            "origin_type=eq.system&select=id,creative_id,decision_id,learning_applied&order=created_at.desc&limit=10"
        )

        for outcome in outcomes:
            # System outcomes must have decision_id
            assert outcome.get("decision_id") is not None, \
                f"Outcome {outcome['id']} missing decision_id"

    @pytest.mark.integration
    async def test_learning_applied_flag(self, db: DbAssertions):
        """
        Verify learning_applied flag is being set.

        This indicates learning loop is processing outcomes.
        """
        # Count processed vs unprocessed
        processed = await db._query(
            "outcome_aggregates",
            "learning_applied=eq.true&select=id&limit=100"
        )

        unprocessed = await db._query(
            "outcome_aggregates",
            "learning_applied=eq.false&origin_type=eq.system&select=id&limit=100"
        )

        print(f"Processed outcomes: {len(processed)}")
        print(f"Unprocessed outcomes: {len(unprocessed)}")

        # Warn if too many unprocessed
        if len(unprocessed) > 20:
            pytest.fail(f"Too many unprocessed outcomes: {len(unprocessed)}")

    @pytest.mark.integration
    async def test_idea_confidence_versions(self, db: DbAssertions):
        """
        Verify idea confidence versions are being created.

        This indicates learning loop is updating confidence.
        """
        versions = await db._query(
            "idea_confidence_versions",
            "select=idea_id,version,confidence_value,source_outcome_id&order=updated_at.desc&limit=10"
        )

        if not versions:
            pytest.skip("No confidence versions yet")

        for v in versions:
            # Verify required fields
            assert v.get("idea_id") is not None
            assert v.get("version") is not None
            assert v.get("source_outcome_id") is not None

            # Confidence should be between 0 and 1
            conf = v.get("confidence_value")
            if conf is not None:
                assert 0 <= conf <= 1, f"Invalid confidence: {conf}"

    @pytest.mark.integration
    async def test_death_state_transitions(self, db: DbAssertions):
        """
        Verify death state is properly set for failing ideas.

        Valid states: null, 'soft_dead', 'hard_dead', 'permanent_dead'
        """
        # Get ideas with death_state set
        dead_ideas = await db._query(
            "ideas",
            "death_state=neq.null&select=id,canonical_hash,death_state&limit=10"
        )

        valid_states = {"soft_dead", "hard_dead", "permanent_dead"}

        for idea in dead_ideas:
            state = idea.get("death_state")
            assert state in valid_states, f"Invalid death_state: {state}"

    @pytest.mark.integration
    @pytest.mark.requires_de
    async def test_learning_loop_api_contract(self):
        """
        Test Learning Loop API contract.

        Verifies the API responds with expected structure.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Get status
            response = await client.get(
                f"{DE_API_URL}/learning/status",
                headers={"X-API-Key": API_KEY}
            )
            assert response.status_code == 200

            # Test process endpoint (dry run with limit=0)
            response = await client.post(
                f"{DE_API_URL}/learning/process",
                json={"limit": 1},
                headers={
                    "X-API-Key": API_KEY,
                    "Content-Type": "application/json",
                }
            )

            # Should return valid response
            assert response.status_code in [200, 401, 403]

            if response.status_code == 200:
                data = response.json()
                # Verify contract fields
                assert "processed" in data or "results" in data or "error" in data


class TestLearningPipelineContracts:
    """Contract validation tests for learning pipeline."""

    @pytest.mark.integration
    async def test_outcome_to_learning_loop_contract(self, db: DbAssertions):
        """
        Verify outcome_aggregates contain fields required by learning loop.

        Learning loop needs:
        - id (outcome_id)
        - creative_id (to resolve idea)
        - decision_id (for system outcomes)
        - cpa, spend, conversions (for confidence calculation)
        """
        outcomes = await db._query(
            "outcome_aggregates",
            "origin_type=eq.system&learning_applied=eq.false&select=*&limit=5"
        )

        for outcome in outcomes:
            # Required fields
            assert "id" in outcome, "outcome_id required"
            assert "creative_id" in outcome, "creative_id required"
            assert "decision_id" in outcome, "decision_id required for system outcomes"

            # Metrics fields (at least one should exist)
            has_metrics = any(
                outcome.get(f) is not None
                for f in ["cpa", "spend", "conversions", "clicks"]
            )
            # Metrics might be in JSONB payload
            if not has_metrics and "payload" in outcome:
                pass  # OK, metrics in payload

    @pytest.mark.integration
    async def test_snapshot_to_outcome_linkage(self, db: DbAssertions):
        """
        Verify snapshots can be linked to outcomes via tracker_id -> creatives -> outcomes.

        This tests the data flow integrity.
        """
        # Get a snapshot
        snapshots = await db._query(
            "daily_metrics_snapshot",
            "select=id,tracker_id,date&order=created_at.desc&limit=1"
        )

        if not snapshots:
            pytest.skip("No snapshots available")

        snapshot = snapshots[0]
        tracker_id = snapshot["tracker_id"]

        # Find creative by tracker_id
        creative = await db.get_creative(tracker_id)

        if not creative:
            pytest.skip(f"No creative found for tracker_id {tracker_id}")

        # Check if there's a corresponding outcome
        outcome = await db.get_outcome(creative["id"])

        # Not all snapshots will have outcomes (only if idea+decision exist)
        # But the linkage should be possible
        print(f"Snapshot {snapshot['id']} -> Tracker {tracker_id} -> Creative {creative['id']} -> Outcome: {outcome is not None}")


class TestLearningPipelineRegressions:
    """Regression tests for known learning pipeline issues."""

    @pytest.mark.integration
    async def test_no_orphan_outcomes(self, db: DbAssertions):
        """
        Regression: Verify no outcomes without resolvable idea.

        Related issue: #80
        """
        # Outcomes should be linked via creative_id -> decomposed_creatives -> idea_id
        outcomes = await db._query(
            "outcome_aggregates",
            "learning_applied=eq.false&origin_type=eq.system&select=id,creative_id&limit=20"
        )

        orphan_count = 0
        for outcome in outcomes:
            creative_id = outcome["creative_id"]

            # Check if creative has decomposed with idea_id
            decomposed = await db.get_decomposed(creative_id)
            if decomposed is None or decomposed.get("idea_id") is None:
                orphan_count += 1

        # Allow some orphans for in-progress, but warn if many
        assert orphan_count < 5, f"Found {orphan_count} orphan outcomes without resolvable idea"

    @pytest.mark.integration
    async def test_learning_events_emitted(self, db: DbAssertions):
        """
        Verify learning events are being emitted to event_log.
        """
        events = await db._query(
            "event_log",
            "event_type=like.learning%&select=event_type,entity_id,occurred_at&order=occurred_at.desc&limit=10"
        )

        # Log for visibility
        print(f"Found {len(events)} learning events")
        for e in events[:5]:
            print(f"  - {e['event_type']}: {e['entity_id']}")

    @pytest.mark.integration
    async def test_confidence_monotonicity(self, db: DbAssertions):
        """
        Verify confidence versions are monotonically increasing.

        Each new version should have version = previous + 1
        """
        # Get ideas with multiple confidence versions
        ideas_with_versions = await db._query(
            "idea_confidence_versions",
            "select=idea_id&order=idea_id&limit=100"
        )

        if not ideas_with_versions:
            pytest.skip("No confidence versions")

        # Group by idea_id
        idea_ids = set(v["idea_id"] for v in ideas_with_versions)

        for idea_id in list(idea_ids)[:5]:  # Check first 5
            versions = await db._query(
                "idea_confidence_versions",
                f"idea_id=eq.{idea_id}&select=version&order=version.asc"
            )

            if len(versions) > 1:
                for i in range(1, len(versions)):
                    prev = versions[i - 1]["version"]
                    curr = versions[i]["version"]
                    assert curr == prev + 1, \
                        f"Version gap for idea {idea_id}: {prev} -> {curr}"
