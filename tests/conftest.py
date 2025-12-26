"""
Pytest configuration and shared fixtures for GenomAI tests.
"""

import os
import asyncio
from datetime import datetime
from typing import Generator

import pytest
import httpx

# Test configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ftrerelppsnbdcmtcwya.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "https://kazamaqwe.app.n8n.cloud/webhook")
DE_API_URL = os.getenv("DE_API_URL", "https://genomai.onrender.com")
DE_API_KEY = os.getenv("API_KEY", "")

# Test data prefix for isolation
TEST_PREFIX = "TEST_"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def supabase_headers() -> dict:
    """Supabase API headers with genomai schema."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
    }


@pytest.fixture(scope="session")
def de_api_headers() -> dict:
    """Decision Engine API headers."""
    return {
        "Authorization": f"Bearer {DE_API_KEY}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
def http_client() -> Generator[httpx.AsyncClient, None, None]:
    """Shared async HTTP client."""
    client = httpx.AsyncClient(timeout=60.0)
    yield client
    asyncio.get_event_loop().run_until_complete(client.aclose())


@pytest.fixture
def test_tracker_id() -> str:
    """Generate unique test tracker ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{TEST_PREFIX}{timestamp}"


@pytest.fixture
def test_video_url() -> str:
    """Test video URL (placeholder)."""
    return "https://drive.google.com/file/d/TEST_VIDEO_ID/view"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (timeout > 30s)"
    )
    config.addinivalue_line(
        "markers", "requires_n8n: mark test as requiring n8n access"
    )
    config.addinivalue_line(
        "markers", "requires_de: mark test as requiring Decision Engine"
    )
