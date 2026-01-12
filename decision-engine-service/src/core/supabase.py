"""
Centralized Supabase Client

Provides a singleton SupabaseClient for all database operations.
All activities and services should use get_supabase() instead of
constructing headers manually.

This centralizes:
- Credentials management (single point of env access)
- Header construction (consistent schema headers)
- URL building (rest_url already includes /rest/v1)

Usage:
    from src.core.supabase import get_supabase

    sb = get_supabase()
    headers = sb.get_headers(for_write=True)
    url = f"{sb.rest_url}/table_name"
"""

import os
from typing import Optional


# Schema name for all operations
SCHEMA = "genomai"


class SupabaseClient:
    """
    Centralized Supabase client with credentials and header management.

    Attributes:
        rest_url: Full REST API URL (includes /rest/v1)
    """

    def __init__(self, supabase_url: str, service_role_key: str):
        """
        Initialize Supabase client.

        Args:
            supabase_url: Base Supabase URL (e.g., https://xxx.supabase.co)
            service_role_key: Service role key for authentication
        """
        self._supabase_url = supabase_url
        self._service_role_key = service_role_key
        # REST URL includes /rest/v1 path
        self.rest_url = f"{supabase_url}/rest/v1"

    @property
    def base_url(self) -> str:
        """Get base Supabase URL (without /rest/v1)."""
        return self._supabase_url

    @property
    def service_key(self) -> str:
        """Get service role key (for legacy APIs that need raw key)."""
        return self._service_role_key

    def get_headers(self, for_write: bool = False) -> dict:
        """
        Get headers for Supabase REST API with genomai schema.

        Args:
            for_write: If True, include Content-Profile and Prefer headers

        Returns:
            Dict of headers for HTTP requests
        """
        headers = {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Accept-Profile": SCHEMA,
            "Content-Type": "application/json",
        }
        if for_write:
            headers["Content-Profile"] = SCHEMA
            headers["Prefer"] = "return=representation"
        return headers


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """
    Get the shared Supabase client instance.

    Creates the client on first call using environment variables:
    - SUPABASE_URL: Base Supabase URL
    - SUPABASE_SERVICE_ROLE_KEY: Service role key

    Returns:
        Shared SupabaseClient instance

    Raises:
        RuntimeError: If credentials are missing
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not service_role_key:
            raise RuntimeError(
                "Missing Supabase credentials: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required"
            )

        _supabase_client = SupabaseClient(supabase_url, service_role_key)
    return _supabase_client


def reset_supabase_client() -> None:
    """
    Reset the Supabase client (for testing).

    Creates a new client on next get_supabase() call.
    """
    global _supabase_client
    _supabase_client = None
