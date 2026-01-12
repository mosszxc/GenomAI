"""
Unit tests for Learning Loop idempotency.

Issue #473: Learning Loop не идемпотентен — duplicate processing

Tests that:
1. is_outcome_already_processed returns True if outcome was processed
2. process_single_outcome skips already-processed outcomes
3. process_learning_batch counts skipped outcomes
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_env(monkeypatch):
    """Set up required environment variables."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")


class TestIsOutcomeAlreadyProcessed:
    """Tests for is_outcome_already_processed function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_confidence_version_exists(self, mock_env):
        """If confidence version with source_outcome_id exists, return True."""
        from src.services.learning_loop import is_outcome_already_processed

        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "existing-version-id"}]
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.learning_loop.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await is_outcome_already_processed("test-outcome-id")

            assert result is True
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_confidence_version(self, mock_env):
        """If no confidence version with source_outcome_id exists, return False."""
        from src.services.learning_loop import is_outcome_already_processed

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.learning_loop.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await is_outcome_already_processed("test-outcome-id")

            assert result is False


class TestProcessSingleOutcomeIdempotency:
    """Tests for idempotency in process_single_outcome."""

    @pytest.mark.asyncio
    async def test_skips_already_processed_outcome(self, mock_env):
        """Already-processed outcome should be skipped."""
        from src.services.learning_loop import process_single_outcome

        outcome = {
            "id": "test-outcome-id",
            "creative_id": "test-creative-id",
            "cpa": 15.0,
            "spend": 100.0,
            "environment_ctx": None,
            "window_end": datetime.now().isoformat(),
        }

        with patch(
            "src.services.learning_loop.is_outcome_already_processed",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_check:
            with patch(
                "src.services.learning_loop.mark_outcome_processed",
                new_callable=AsyncMock,
            ) as mock_mark:
                result = await process_single_outcome(outcome)

                assert result.get("skipped") is True
                assert result.get("reason") == "already_processed"
                mock_check.assert_called_once_with("test-outcome-id")
                mock_mark.assert_called_once()

    @pytest.mark.asyncio
    async def test_processes_new_outcome(self, mock_env):
        """New outcome should be processed normally."""
        from src.services.learning_loop import process_single_outcome

        outcome = {
            "id": "test-outcome-id",
            "creative_id": "test-creative-id",
            "cpa": 15.0,
            "spend": 100.0,
            "environment_ctx": None,
            "window_end": datetime.now().isoformat(),
        }

        with patch(
            "src.services.learning_loop.is_outcome_already_processed",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch(
                "src.services.learning_loop.resolve_idea_for_outcome",
                new_callable=AsyncMock,
                return_value=None,  # Simulate no idea found
            ):
                result = await process_single_outcome(outcome)

                # Should return error (no idea) but NOT skipped
                assert result.get("skipped") is None
                assert "error" in result


class TestLearningResultSkippedCount:
    """Tests for LearningResult skipped_count field."""

    def test_skipped_count_initialized_to_zero(self, mock_env):
        """LearningResult should initialize skipped_count to 0."""
        from src.services.learning_loop import LearningResult

        result = LearningResult()

        assert result.skipped_count == 0

    def test_skipped_count_in_to_dict(self, mock_env):
        """to_dict() should include skipped_count."""
        from src.services.learning_loop import LearningResult

        result = LearningResult(processed_count=5, skipped_count=3)
        data = result.to_dict()

        assert data["skipped_count"] == 3
        assert data["processed_count"] == 5


class TestProcessLearningBatchIdempotency:
    """Tests for idempotency in process_learning_batch."""

    @pytest.mark.asyncio
    async def test_counts_skipped_outcomes(self, mock_env):
        """process_learning_batch should count skipped outcomes."""
        from src.services.learning_loop import process_learning_batch

        mock_outcomes = [
            {"id": "outcome-1", "cpa": 10.0},
            {"id": "outcome-2", "cpa": 15.0},
        ]

        with patch(
            "src.services.learning_loop.fetch_unprocessed_outcomes",
            new_callable=AsyncMock,
            return_value=mock_outcomes,
        ):
            with patch(
                "src.services.learning_loop.process_single_outcome",
                new_callable=AsyncMock,
                side_effect=[
                    {"skipped": True, "reason": "already_processed"},
                    {"idea_id": "idea-1", "new_confidence": 0.5, "delta": 0.1},
                ],
            ):
                result = await process_learning_batch(limit=2)

                assert result.skipped_count == 1
                assert result.processed_count == 1
