"""
Singleton HTTP Client

Provides a shared httpx.AsyncClient instance with connection pooling.
All activities and services should use get_http_client() instead of
creating new httpx.AsyncClient instances.

Usage:
    from src.core.http_client import get_http_client

    client = get_http_client()
    response = await client.post(url, headers=headers, json=data)
"""

import httpx
from typing import Optional


_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get the shared HTTP client instance.

    Creates the client on first call with optimized settings:
    - max_connections=100: Handle concurrent requests
    - timeout=30s: Reasonable default for API calls

    Returns:
        Shared httpx.AsyncClient instance
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(30.0),
        )
    return _http_client


async def close_http_client() -> None:
    """
    Close the shared HTTP client.

    Call this during application shutdown to properly release connections.
    """
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def reset_http_client() -> None:
    """
    Reset the HTTP client (for testing).

    Creates a new client on next get_http_client() call.
    """
    global _http_client
    _http_client = None
