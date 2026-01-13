"""Tests for Telegram webhook secret verification."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from src.routes.telegram import verify_webhook_secret, TELEGRAM_SECRET_HEADER


class TestWebhookSecretVerification:
    """Test suite for webhook secret verification."""

    def test_no_secret_configured_allows_request(self):
        """When TELEGRAM_WEBHOOK_SECRET is not set, all requests pass."""
        request = MagicMock()
        request.headers = {}

        with patch.dict("os.environ", {}, clear=True):
            # Should not raise
            verify_webhook_secret(request)

    def test_missing_header_raises_401(self):
        """When secret is configured but header is missing, raise 401."""
        request = MagicMock()
        request.headers = {}

        with patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": "test_secret"}):
            with pytest.raises(HTTPException) as exc:
                verify_webhook_secret(request)
            assert exc.value.status_code == 401
            assert "Missing" in exc.value.detail

    def test_invalid_secret_raises_401(self):
        """When secret doesn't match, raise 401."""
        request = MagicMock()
        request.headers = {TELEGRAM_SECRET_HEADER: "wrong_secret"}

        with patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": "correct_secret"}):
            with pytest.raises(HTTPException) as exc:
                verify_webhook_secret(request)
            assert exc.value.status_code == 401
            assert "Invalid" in exc.value.detail

    def test_valid_secret_passes(self):
        """When secret matches, request passes."""
        request = MagicMock()
        request.headers = {TELEGRAM_SECRET_HEADER: "my_secret_token"}

        with patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": "my_secret_token"}):
            # Should not raise
            verify_webhook_secret(request)

    def test_empty_secret_env_skips_verification(self):
        """Empty TELEGRAM_WEBHOOK_SECRET string skips verification."""
        request = MagicMock()
        request.headers = {}

        with patch.dict("os.environ", {"TELEGRAM_WEBHOOK_SECRET": ""}):
            # Should not raise (empty string is falsy)
            verify_webhook_secret(request)
