"""
Unit tests for Telegram Login Widget authentication
"""

import hashlib
import hmac
import time

import pytest

from src.routes.auth import (
    TelegramAuthData,
    verify_telegram_auth,
    is_auth_date_valid,
    AUTH_DATE_MAX_AGE_SECONDS,
)


class TestVerifyTelegramAuth:
    """Tests for HMAC-SHA256 verification"""

    def test_valid_hash_returns_true(self):
        """Valid hash should return True"""
        bot_token = "test_bot_token_12345"
        auth_date = int(time.time())

        # Build auth data
        data = TelegramAuthData(
            id=123456789,
            first_name="John",
            auth_date=auth_date,
            hash="placeholder",  # Will be replaced with valid hash
        )

        # Calculate valid hash
        check_dict = {
            "id": data.id,
            "first_name": data.first_name,
            "auth_date": data.auth_date,
        }
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(check_dict.items())
        )
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        valid_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Update data with valid hash
        data.hash = valid_hash

        assert verify_telegram_auth(data, bot_token) is True

    def test_invalid_hash_returns_false(self):
        """Invalid hash should return False"""
        bot_token = "test_bot_token_12345"

        data = TelegramAuthData(
            id=123456789,
            first_name="John",
            auth_date=int(time.time()),
            hash="invalid_hash_value",
        )

        assert verify_telegram_auth(data, bot_token) is False

    def test_hash_includes_optional_fields(self):
        """Hash should include optional fields when present"""
        bot_token = "test_bot_token_12345"
        auth_date = int(time.time())

        # Build auth data with optional fields
        data = TelegramAuthData(
            id=123456789,
            first_name="John",
            last_name="Doe",
            username="johndoe",
            photo_url="https://t.me/i/userpic/320/abc.jpg",
            auth_date=auth_date,
            hash="placeholder",
        )

        # Calculate valid hash with all fields
        check_dict = {
            "id": data.id,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "username": data.username,
            "photo_url": data.photo_url,
            "auth_date": data.auth_date,
        }
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(check_dict.items())
        )
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        valid_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        data.hash = valid_hash

        assert verify_telegram_auth(data, bot_token) is True


class TestIsAuthDateValid:
    """Tests for auth_date freshness check"""

    def test_fresh_auth_date_is_valid(self):
        """Auth date within 24h should be valid"""
        auth_date = int(time.time()) - 3600  # 1 hour ago
        assert is_auth_date_valid(auth_date) is True

    def test_current_auth_date_is_valid(self):
        """Current auth date should be valid"""
        auth_date = int(time.time())
        assert is_auth_date_valid(auth_date) is True

    def test_expired_auth_date_is_invalid(self):
        """Auth date older than 24h should be invalid"""
        auth_date = int(time.time()) - AUTH_DATE_MAX_AGE_SECONDS - 1
        assert is_auth_date_valid(auth_date) is False

    def test_boundary_auth_date_is_valid(self):
        """Auth date exactly at boundary should be valid"""
        auth_date = int(time.time()) - AUTH_DATE_MAX_AGE_SECONDS
        assert is_auth_date_valid(auth_date) is True
