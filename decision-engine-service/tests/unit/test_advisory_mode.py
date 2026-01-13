"""
Test advisory mode for Decision Engine.

Issue #604: DE Advisory Mode (Warnings for Buyers)
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.decision_engine import make_decision, _create_warning
from src.utils.validators import validate_decision_request, VALID_DECISION_MODES


class TestModeValidation:
    """Test mode parameter validation."""

    def test_valid_modes_defined(self):
        """Valid modes should be strict and advisory."""
        assert "strict" in VALID_DECISION_MODES
        assert "advisory" in VALID_DECISION_MODES
        assert len(VALID_DECISION_MODES) == 2

    def test_mode_validation_accepts_strict(self):
        """Strict mode should be accepted."""
        body = {"idea_id": "test-uuid", "mode": "strict"}
        error = validate_decision_request(body)
        assert error is None

    def test_mode_validation_accepts_advisory(self):
        """Advisory mode should be accepted."""
        body = {"idea_id": "test-uuid", "mode": "advisory"}
        error = validate_decision_request(body)
        assert error is None

    def test_mode_validation_rejects_invalid(self):
        """Invalid mode should be rejected."""
        body = {"idea_id": "test-uuid", "mode": "invalid_mode"}
        error = validate_decision_request(body)
        assert error is not None
        assert "mode must be one of" in error

    def test_mode_validation_rejects_non_string(self):
        """Non-string mode should be rejected."""
        body = {"idea_id": "test-uuid", "mode": 123}
        error = validate_decision_request(body)
        assert error is not None
        assert "mode must be a string" in error

    def test_mode_optional_defaults_to_strict(self):
        """Mode is optional, defaults to strict."""
        body = {"idea_id": "test-uuid"}
        error = validate_decision_request(body)
        assert error is None


class TestCreateWarning:
    """Test warning creation from failed checks."""

    def test_death_memory_warning(self):
        """Death memory warning should have correct format."""
        check_result = {
            "name": "death_memory",
            "result": "FAILED",
            "details": {"death_state": "soft_dead", "idea_id": "test-id"},
        }
        warning = _create_warning(check_result, severity="high")

        assert warning["check"] == "death_memory"
        assert warning["severity"] == "high"
        assert "soft_dead" in warning["message"]
        assert warning["details"]["death_state"] == "soft_dead"

    def test_fatigue_constraint_warning(self):
        """Fatigue constraint warning should have correct format."""
        check_result = {
            "name": "fatigue_constraint",
            "result": "FAILED",
            "details": {"note": "fatigue exceeded"},
        }
        warning = _create_warning(check_result, severity="medium")

        assert warning["check"] == "fatigue_constraint"
        assert warning["severity"] == "medium"
        assert "fatigue" in warning["message"].lower()


class TestAdvisoryModeDecision:
    """Test decision engine in advisory mode."""

    @pytest.fixture
    def valid_idea(self):
        """Create a valid idea for testing."""
        return {
            "id": "test-idea-id",
            "canonical_hash": "abc123",
            "status": "pending",
            "name": "Test Idea",
            "hook": "test hook",
            "angle": "fear",
            "geo": "US",
            "creative_type": "video",
            "budget_usd": 100,
        }

    @pytest.fixture
    def dead_idea(self):
        """Create a dead idea for testing."""
        return {
            "id": "dead-idea-id",
            "canonical_hash": "def456",
            "status": "pending",
            "name": "Dead Idea",
            "hook": "test hook",
            "angle": "fear",
            "geo": "US",
            "creative_type": "video",
            "budget_usd": 100,
            "death_state": "soft_dead",
        }

    @pytest.mark.asyncio
    async def test_strict_mode_rejects_dead_idea(self, dead_idea):
        """In strict mode, dead idea should be rejected."""
        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
            ),
        ):
            result = await make_decision(
                {"idea_id": dead_idea["id"], "idea": dead_idea, "mode": "strict"}
            )

            assert result["decision"]["decision_type"] == "reject"
            assert result["decision"]["decision_reason"] == "idea_dead"
            assert "warnings" not in result

    @pytest.mark.asyncio
    async def test_advisory_mode_warns_for_dead_idea(self, dead_idea):
        """In advisory mode, dead idea should return warning instead of reject."""
        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
            ),
        ):
            result = await make_decision(
                {"idea_id": dead_idea["id"], "idea": dead_idea, "mode": "advisory"}
            )

            assert result["decision"]["decision_type"] == "approve_with_warnings"
            assert result["decision"]["decision_reason"] == "approved_with_warnings"
            assert "warnings" in result
            assert len(result["warnings"]) == 1
            assert result["warnings"][0]["check"] == "death_memory"
            assert result["warnings"][0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_advisory_mode_approves_valid_idea(self, valid_idea):
        """In advisory mode, valid idea should be approved without warnings."""
        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
            ),
        ):
            result = await make_decision(
                {"idea_id": valid_idea["id"], "idea": valid_idea, "mode": "advisory"}
            )

            assert result["decision"]["decision_type"] == "approve"
            assert result["decision"]["decision_reason"] == "all_checks_passed"
            assert "warnings" not in result or len(result.get("warnings", [])) == 0

    @pytest.mark.asyncio
    async def test_default_mode_is_strict(self, dead_idea):
        """Default mode should be strict."""
        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
            ),
        ):
            # No mode specified
            result = await make_decision({"idea_id": dead_idea["id"], "idea": dead_idea})

            # Should reject (strict mode behavior)
            assert result["decision"]["decision_type"] == "reject"

    @pytest.mark.asyncio
    async def test_schema_invalid_always_rejects(self, valid_idea):
        """Schema validation failure should always reject, even in advisory mode."""
        invalid_idea = valid_idea.copy()
        del invalid_idea["canonical_hash"]  # Remove required schema field

        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
            ),
        ):
            result = await make_decision(
                {"idea_id": invalid_idea["id"], "idea": invalid_idea, "mode": "advisory"}
            )

            assert result["decision"]["decision_type"] == "reject"
            assert result["decision"]["decision_reason"] == "schema_invalid"


class TestWarningsInTrace:
    """Test that warnings are included in decision trace."""

    @pytest.fixture
    def dead_idea(self):
        """Create a dead idea for testing."""
        return {
            "id": "dead-idea-id",
            "canonical_hash": "ghi789",
            "status": "pending",
            "name": "Dead Idea",
            "hook": "test hook",
            "angle": "fear",
            "geo": "US",
            "creative_type": "video",
            "budget_usd": 100,
            "death_state": "hard_dead",
        }

    @pytest.mark.asyncio
    async def test_warnings_saved_in_trace(self, dead_idea):
        """Warnings should be saved in decision trace."""
        saved_trace = None

        async def capture_trace(decision, trace):
            nonlocal saved_trace
            saved_trace = trace

        with (
            patch(
                "src.services.decision_engine.get_existing_decision",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.services.decision_engine.load_system_state",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "src.services.decision_engine.save_decision_with_trace",
                new_callable=AsyncMock,
                side_effect=capture_trace,
            ),
        ):
            await make_decision({"idea_id": dead_idea["id"], "idea": dead_idea, "mode": "advisory"})

            assert saved_trace is not None
            assert "warnings" in saved_trace
            assert len(saved_trace["warnings"]) == 1
            assert saved_trace["warnings"][0]["check"] == "death_memory"
