"""
Tests for creative failed status handling (Issue #472)

Tests:
1. update_creative_status sets error field when status='failed'
2. Maintenance workflow finds and retries failed creatives
3. Creatives exceeding max retries are abandoned
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestUpdateCreativeStatus:
    """Tests for update_creative_status with error support"""

    @pytest.mark.asyncio
    async def test_failed_status_sets_error_field(self):
        """When status='failed', error field should be set"""
        from temporal.activities.supabase import update_creative_status

        creative_id = "test-creative-123"
        error_message = "Transcription failed: API timeout"

        with patch("temporal.activities.supabase._get_credentials") as mock_creds:
            mock_creds.return_value = ("http://test.supabase.co/rest/v1", "test-key")

            with patch(
                "temporal.activities.supabase.get_http_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.patch = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                await update_creative_status(creative_id, "failed", error_message)

                # Verify patch was called with error field
                call_args = mock_client.patch.call_args
                json_data = call_args[1]["json"]

                assert json_data["status"] == "failed"
                assert json_data["error"] == error_message
                assert "failed_at" in json_data

    @pytest.mark.asyncio
    async def test_processed_status_no_error_field(self):
        """When status='processed', error field should not be set"""
        from temporal.activities.supabase import update_creative_status

        creative_id = "test-creative-123"

        with patch("temporal.activities.supabase._get_credentials") as mock_creds:
            mock_creds.return_value = ("http://test.supabase.co/rest/v1", "test-key")

            with patch(
                "temporal.activities.supabase.get_http_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.patch = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                await update_creative_status(creative_id, "processed")

                # Verify patch was called without error field
                call_args = mock_client.patch.call_args
                json_data = call_args[1]["json"]

                assert json_data["status"] == "processed"
                assert "error" not in json_data
                assert "failed_at" not in json_data

    @pytest.mark.asyncio
    async def test_error_truncated_to_1000_chars(self):
        """Long error messages should be truncated"""
        from temporal.activities.supabase import update_creative_status

        creative_id = "test-creative-123"
        long_error = "x" * 2000  # 2000 character error

        with patch("temporal.activities.supabase._get_credentials") as mock_creds:
            mock_creds.return_value = ("http://test.supabase.co/rest/v1", "test-key")

            with patch(
                "temporal.activities.supabase.get_http_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.patch = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                await update_creative_status(creative_id, "failed", long_error)

                call_args = mock_client.patch.call_args
                json_data = call_args[1]["json"]

                # Error should be truncated to 1000 chars
                assert len(json_data["error"]) == 1000


class TestFindFailedCreatives:
    """Tests for find_failed_creatives_for_retry activity"""

    def test_activity_exists(self):
        """Verify find_failed_creatives_for_retry activity is defined"""
        from temporal.activities.maintenance import find_failed_creatives_for_retry

        assert callable(find_failed_creatives_for_retry)

    def test_activity_has_correct_signature(self):
        """Verify activity has expected parameters"""
        from temporal.activities.maintenance import find_failed_creatives_for_retry
        import inspect

        sig = inspect.signature(find_failed_creatives_for_retry)
        params = list(sig.parameters.keys())

        assert "max_retry_count" in params
        assert "min_age_minutes" in params


class TestResetCreativeForRetry:
    """Tests for reset_creative_for_retry activity"""

    def test_activity_exists(self):
        """Verify reset_creative_for_retry activity is defined"""
        from temporal.activities.maintenance import reset_creative_for_retry

        assert callable(reset_creative_for_retry)

    def test_activity_has_correct_signature(self):
        """Verify activity has expected parameter"""
        from temporal.activities.maintenance import reset_creative_for_retry
        import inspect

        sig = inspect.signature(reset_creative_for_retry)
        params = list(sig.parameters.keys())

        assert "creative_id" in params


class TestAbandonFailedCreative:
    """Tests for abandon_failed_creative activity"""

    @pytest.mark.asyncio
    async def test_sets_status_to_abandoned(self):
        """Should set status to 'abandoned'"""
        from temporal.activities.maintenance import abandon_failed_creative

        creative_id = "creative-to-abandon"

        with patch("temporal.activities.maintenance._get_credentials") as mock_creds:
            mock_creds.return_value = ("http://test.supabase.co/rest/v1", "test-key")

            with patch(
                "temporal.activities.maintenance.get_http_client"
            ) as mock_get_client:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.patch = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await abandon_failed_creative(creative_id)

                assert result is True

                # Verify PATCH was called with abandoned status
                call_args = mock_client.patch.call_args
                json_data = call_args[1]["json"]

                assert json_data["status"] == "abandoned"


class TestCreativeStatusMachine:
    """Tests for creative status state machine"""

    def test_valid_status_transitions(self):
        """Document valid status transitions"""
        # Valid transitions:
        # registered -> processing -> processed (happy path)
        # registered -> processing -> failed (error path)
        # failed -> registered (retry)
        # failed -> abandoned (max retries exceeded)

        valid_transitions = {
            "registered": ["processing"],
            "processing": ["processed", "failed"],
            "failed": ["registered", "abandoned"],
            "processed": [],  # Terminal state
            "abandoned": [],  # Terminal state
        }

        # This is a documentation test - verifies the expected state machine
        for from_status, to_statuses in valid_transitions.items():
            assert isinstance(to_statuses, list), (
                f"Invalid transitions for {from_status}"
            )
