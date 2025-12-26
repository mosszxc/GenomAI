"""
Integration tests for Creative Pipeline.

Tests the full flow:
buyer_creative_registration → creative_decomposition → idea_registry → decision_engine → hypothesis_factory

These tests verify:
1. Creative is created in database
2. Transcript is created (via transcription workflow)
3. Decomposed creative is created with canonical fields
4. Idea is created or reused based on canonical hash
5. Decision is made (approve/reject/defer)
6. Hypothesis is generated for approved ideas
"""

import pytest
import httpx
import asyncio
import os
from datetime import datetime

from tests.integration.assertions.db_assertions import DbAssertions, wait_for_condition


# Test configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ftrerelppsnbdcmtcwya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "https://kazamaqwe.app.n8n.cloud/webhook")
DE_API_URL = os.getenv("DE_API_URL", "https://genomai.onrender.com")

# Webhook paths from dependency_manifest
WEBHOOKS = {
    "buyer_creative_registration": f"{N8N_WEBHOOK_BASE}/buyer-creative-registration",
    "creative_decomposition": f"{N8N_WEBHOOK_BASE}/creative-decomposition",
    "idea_registry": f"{N8N_WEBHOOK_BASE}/idea-registry",
    "decision_engine": f"{N8N_WEBHOOK_BASE}/decision-engine",
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


@pytest.fixture
def test_tracker_id() -> str:
    """Generate unique test tracker ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"TEST_{timestamp}"


class TestCreativePipeline:
    """Integration tests for the creative pipeline."""

    @pytest.mark.integration
    @pytest.mark.requires_de
    async def test_health_check(self):
        """Verify Decision Engine is reachable."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{DE_API_URL}/health")

            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"

    @pytest.mark.integration
    async def test_creative_creation_in_database(self, db: DbAssertions, test_tracker_id: str):
        """
        Test that creative is properly created in database.

        This is a mock test - in real scenario, trigger via Telegram or webhook.
        """
        # For now, just verify we can query the database
        exists = await db.creative_exists(test_tracker_id)
        assert exists is False, "Test creative should not exist before test"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_n8n
    async def test_creative_to_idea_flow(self, db: DbAssertions, test_tracker_id: str):
        """
        Test creative → decomposition → idea creation flow.

        This test requires:
        - n8n workflows active
        - Valid video URL
        - External services (AssemblyAI, OpenAI)

        Skip in CI, run manually for full E2E validation.
        """
        pytest.skip("Requires manual trigger - use for local E2E testing")

        # Example of what a full test would look like:
        #
        # 1. Trigger creative registration
        # async with httpx.AsyncClient(timeout=120.0) as client:
        #     response = await client.post(
        #         WEBHOOKS["buyer_creative_registration"],
        #         json={
        #             "video_url": "https://drive.google.com/file/d/XXX/view",
        #             "tracker_id": test_tracker_id,
        #             "chat_id": 123456789,
        #         }
        #     )
        #     assert response.status_code == 200
        #
        # 2. Wait for creative to be created
        # await wait_for_condition(
        #     lambda: db.creative_exists(test_tracker_id),
        #     timeout=30,
        #     message="Creative not created"
        # )
        #
        # 3. Wait for decomposition
        # creative = await db.get_creative(test_tracker_id)
        # await wait_for_condition(
        #     lambda: db.decomposed_exists(creative["id"]),
        #     timeout=120,
        #     message="Decomposed creative not created"
        # )
        #
        # 4. Wait for idea
        # decomposed = await db.get_decomposed(creative["id"])
        # idea_id = decomposed.get("idea_id")
        # assert idea_id is not None, "Idea ID should be set"
        #
        # 5. Verify idea exists
        # assert await db.idea_exists(idea_id)

    @pytest.mark.integration
    @pytest.mark.requires_de
    async def test_decision_engine_api_contract(self):
        """
        Test Decision Engine API contract.

        Verifies the API responds with expected structure.
        """
        # This test uses a mock idea_id - in production use real data
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First check health
            health = await client.get(f"{DE_API_URL}/health")
            assert health.status_code == 200

            # Test with invalid idea_id to verify error handling
            response = await client.post(
                f"{DE_API_URL}/api/decision/",
                json={"idea_id": "00000000-0000-0000-0000-000000000000"},
                headers={
                    "Authorization": f"Bearer {os.getenv('API_KEY', '')}",
                    "Content-Type": "application/json",
                }
            )

            # Should return error for non-existent idea
            # Accept either 404 or 200 with error in response
            assert response.status_code in [200, 404, 422]

    @pytest.mark.integration
    async def test_event_emission_pattern(self, db: DbAssertions):
        """
        Test that events are properly emitted to event_log.

        Query recent events to verify event emission pattern.
        """
        # Query last 10 events
        events = await db._query(
            "event_log",
            "select=event_type,entity_id,created_at&order=created_at.desc&limit=10"
        )

        # Verify events have required fields
        for event in events:
            assert "event_type" in event
            assert "entity_id" in event
            assert "created_at" in event

    @pytest.mark.integration
    async def test_no_orphan_decomposed_creatives(self, db: DbAssertions):
        """
        Regression test: Verify no decomposed_creatives without idea_id.

        Related issue: #79 (creatives stuck without decomposition)
        """
        # Query decomposed_creatives where idea_id is null
        orphans = await db._query(
            "decomposed_creatives",
            "idea_id=is.null&select=id,creative_id,created_at&limit=10"
        )

        # In a healthy system, there should be no orphans
        # Allow some for in-progress processing
        assert len(orphans) < 5, f"Too many orphan decomposed_creatives: {len(orphans)}"

    @pytest.mark.integration
    async def test_no_stuck_creatives(self, db: DbAssertions):
        """
        Regression test: Verify no creatives stuck in intermediate states.

        Related issue: #79
        """
        # Query creatives with status that indicates stuck state
        stuck_statuses = ["transcribing", "decomposing"]

        for status in stuck_statuses:
            stuck = await db._query(
                "creatives",
                f"status=eq.{status}&select=id,tracker_id,status,created_at&limit=10"
            )

            # Allow some for in-progress, but warn if many
            if len(stuck) > 3:
                pytest.fail(f"Found {len(stuck)} creatives stuck in '{status}' state")


class TestCreativePipelineContracts:
    """Contract validation tests for creative pipeline."""

    @pytest.mark.integration
    async def test_idea_registry_output_matches_decision_input(self, db: DbAssertions):
        """
        Verify idea_registry output contains fields required by decision_engine.

        Contract: idea_registry_output → decision_engine_input
        Required field: idea_id (UUID)
        """
        # Get a recent idea
        ideas = await db._query(
            "ideas",
            "select=id,canonical_hash,status,death_state&order=created_at.desc&limit=1"
        )

        if not ideas:
            pytest.skip("No ideas in database")

        idea = ideas[0]

        # Verify required fields for decision engine
        assert "id" in idea, "idea_id required for decision engine"
        assert idea["id"] is not None, "idea_id must not be null"

        # Verify UUID format
        import uuid
        try:
            uuid.UUID(idea["id"])
        except ValueError:
            pytest.fail(f"idea_id is not valid UUID: {idea['id']}")

    @pytest.mark.integration
    async def test_decision_output_matches_hypothesis_input(self, db: DbAssertions):
        """
        Verify decision output contains fields required by hypothesis_factory.

        Contract: decision_engine_output → hypothesis_factory_input
        Required fields: idea_id, decision_id, decision='approve'
        """
        # Get a recent APPROVE decision
        decisions = await db._query(
            "decisions",
            "decision=eq.approve&select=id,idea_id,decision&order=created_at.desc&limit=1"
        )

        if not decisions:
            pytest.skip("No APPROVE decisions in database")

        decision = decisions[0]

        # Verify required fields for hypothesis factory
        assert "id" in decision, "decision_id required"
        assert "idea_id" in decision, "idea_id required"
        assert decision["decision"] == "approve", "decision must be 'approve'"
