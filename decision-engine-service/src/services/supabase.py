"""
Supabase client and data access functions

Uses direct HTTP requests with proper schema headers to ensure
all operations use the genomai schema.
"""
import os
import httpx
from src.utils.errors import SupabaseError


# Schema name for all operations
SCHEMA = "genomai"


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    # Extract the REST URL from Supabase URL
    # Supabase URL format: https://xxx.supabase.co
    # REST URL format: https://xxx.supabase.co/rest/v1
    rest_url = f"{supabase_url}/rest/v1"

    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with schema"""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json"
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


async def load_idea(idea_id: str) -> dict | None:
    """Load Idea from Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{rest_url}/ideas?id=eq.{idea_id}&select=*",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                return None

            return data[0]
    except httpx.HTTPStatusError as e:
        raise SupabaseError(f"Failed to load idea: HTTP {e.response.status_code}")
    except Exception as e:
        raise SupabaseError(f"Failed to load idea: {str(e)}")


async def load_system_state() -> dict:
    """Load System State from Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key)
        headers["Prefer"] = "count=exact"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{rest_url}/ideas?status=eq.active&select=id",
                headers=headers
            )
            response.raise_for_status()

            # Get count from Content-Range header
            content_range = response.headers.get("Content-Range", "")
            # Format: "0-N/total" or "*/total"
            total = 0
            if "/" in content_range:
                total = int(content_range.split("/")[1])

            return {
                'active_ideas_count': total,
                'max_active_ideas': 100,
                'current_state': 'exploit'
            }
    except Exception as e:
        raise SupabaseError(f"Failed to load system state: {str(e)}")


async def save_decision(decision: dict) -> dict:
    """Save Decision to Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key, for_write=True)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{rest_url}/decisions",
                headers=headers,
                json=decision
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                raise SupabaseError("Failed to save decision: no data returned")

            return data[0]
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise SupabaseError(f"Failed to save decision: {error_detail}")
    except Exception as e:
        raise SupabaseError(f"Failed to save decision: {str(e)}")


async def save_decision_trace(trace: dict) -> dict:
    """Save Decision Trace to Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key, for_write=True)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{rest_url}/decision_traces",
                headers=headers,
                json=trace
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                raise SupabaseError("Failed to save decision trace: no data returned")

            return data[0]
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise SupabaseError(f"Failed to save decision trace: {error_detail}")
    except Exception as e:
        raise SupabaseError(f"Failed to save decision trace: {str(e)}")

