"""
Unit tests for centralized Supabase client.

Issue: #486 - Centralizing service role key access.
"""

import os
from unittest.mock import patch

import pytest


class TestSupabaseClient:
    """Tests for SupabaseClient class."""

    def test_client_initialization(self):
        """Client initializes with correct URLs."""
        from src.core.supabase import SupabaseClient

        client = SupabaseClient(
            supabase_url="https://test.supabase.co",
            service_role_key="test-key-123",
        )

        assert client.rest_url == "https://test.supabase.co/rest/v1"
        assert client.base_url == "https://test.supabase.co"
        assert client.service_key == "test-key-123"

    def test_get_headers_read(self):
        """Read headers include Accept-Profile but not Content-Profile."""
        from src.core.supabase import SupabaseClient

        client = SupabaseClient(
            supabase_url="https://test.supabase.co",
            service_role_key="test-key-123",
        )

        headers = client.get_headers(for_write=False)

        assert headers["apikey"] == "test-key-123"
        assert headers["Authorization"] == "Bearer test-key-123"
        assert headers["Accept-Profile"] == "genomai"
        assert headers["Content-Type"] == "application/json"
        assert "Content-Profile" not in headers
        assert "Prefer" not in headers

    def test_get_headers_write(self):
        """Write headers include Content-Profile and Prefer."""
        from src.core.supabase import SupabaseClient

        client = SupabaseClient(
            supabase_url="https://test.supabase.co",
            service_role_key="test-key-123",
        )

        headers = client.get_headers(for_write=True)

        assert headers["Content-Profile"] == "genomai"
        assert headers["Prefer"] == "return=representation"


class TestGetSupabase:
    """Tests for get_supabase() singleton function."""

    def setup_method(self):
        """Reset singleton before each test."""
        from src.core.supabase import reset_supabase_client

        reset_supabase_client()

    def teardown_method(self):
        """Reset singleton after each test."""
        from src.core.supabase import reset_supabase_client

        reset_supabase_client()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        },
    )
    def test_get_supabase_returns_singleton(self):
        """Same instance returned on multiple calls."""
        from src.core.supabase import get_supabase

        client1 = get_supabase()
        client2 = get_supabase()

        assert client1 is client2

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        },
    )
    def test_get_supabase_uses_env_vars(self):
        """Client created from environment variables."""
        from src.core.supabase import get_supabase

        client = get_supabase()

        assert client.rest_url == "https://test.supabase.co/rest/v1"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_supabase_raises_without_credentials(self):
        """RuntimeError raised when credentials missing."""
        from src.core.supabase import get_supabase

        # Clear any existing env vars that might interfere
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

        with pytest.raises(RuntimeError, match="Missing Supabase credentials"):
            get_supabase()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        },
    )
    def test_reset_creates_new_client(self):
        """reset_supabase_client() creates new instance on next call."""
        from src.core.supabase import get_supabase, reset_supabase_client

        client1 = get_supabase()
        reset_supabase_client()
        client2 = get_supabase()

        # New instance should be created
        assert client1 is not client2
