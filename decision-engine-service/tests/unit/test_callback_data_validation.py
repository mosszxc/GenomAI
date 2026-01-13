"""Tests for Telegram callback_data validation."""

import pytest
from src.routes.telegram import parse_callback_data, CallbackDataError


class TestParseCallbackData:
    """Test parse_callback_data function."""

    def test_valid_ke_approve(self):
        """Test valid ke_approve callback."""
        action, identifier = parse_callback_data("ke_approve_abc123")
        assert action == "ke_approve"
        assert identifier == "abc123"

    def test_valid_ke_reject(self):
        """Test valid ke_reject callback."""
        action, identifier = parse_callback_data("ke_reject_def456")
        assert action == "ke_reject"
        assert identifier == "def456"

    def test_valid_ke_skip(self):
        """Test valid ke_skip callback."""
        action, identifier = parse_callback_data("ke_skip_xyz789")
        assert action == "ke_skip"
        assert identifier == "xyz789"

    def test_valid_chat(self):
        """Test valid chat callback with numeric ID."""
        action, identifier = parse_callback_data("chat_123456789")
        assert action == "chat"
        assert identifier == "123456789"

    def test_valid_uuid_identifier(self):
        """Test callback with UUID-like identifier."""
        action, identifier = parse_callback_data("ke_approve_a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert action == "ke_approve"
        assert identifier == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_empty_data_raises(self):
        """Test empty callback_data raises error."""
        with pytest.raises(CallbackDataError, match="Empty callback data"):
            parse_callback_data("")

    def test_too_long_raises(self):
        """Test callback_data exceeding 64 chars raises error."""
        long_data = "ke_approve_" + "a" * 60
        with pytest.raises(CallbackDataError, match="exceeds 64 chars"):
            parse_callback_data(long_data)

    def test_special_chars_raises(self):
        """Test callback_data with special characters raises error."""
        with pytest.raises(CallbackDataError, match="Invalid callback data format"):
            parse_callback_data("ke_approve_abc;DROP TABLE")

    def test_sql_injection_attempt_raises(self):
        """Test SQL injection attempt is rejected."""
        with pytest.raises(CallbackDataError, match="Invalid callback data format"):
            parse_callback_data("chat_1' OR '1'='1")

    def test_script_injection_attempt_raises(self):
        """Test script injection attempt is rejected."""
        with pytest.raises(CallbackDataError, match="Invalid callback data format"):
            parse_callback_data("chat_<script>alert(1)</script>")

    def test_no_underscore_raises(self):
        """Test callback_data without underscore raises error."""
        with pytest.raises(CallbackDataError, match="Invalid callback data format"):
            parse_callback_data("invalidformat")

    def test_uppercase_action_raises(self):
        """Test uppercase action prefix is rejected."""
        with pytest.raises(CallbackDataError, match="Invalid callback data format"):
            parse_callback_data("KE_APPROVE_abc123")

    def test_valid_64_char_boundary(self):
        """Test callback_data exactly at 64 char limit works."""
        # ke_approve_ = 11 chars, so identifier can be 53 chars
        data = "ke_approve_" + "a" * 53
        assert len(data) == 64
        action, identifier = parse_callback_data(data)
        assert action == "ke_approve"
        assert len(identifier) == 53
