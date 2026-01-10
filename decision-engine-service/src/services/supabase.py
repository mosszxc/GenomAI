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
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


async def load_idea(idea_id: str) -> dict | None:
    """
    Load Idea from Supabase with Canonical Schema payload (schema: genomai)

    Joins ideas with decomposed_creatives to get full Canonical Schema fields.
    Returns idea with merged payload fields (angle_type, horizon, etc.)
    """
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key)

        async with httpx.AsyncClient() as client:
            # First, load the idea
            response = await client.get(
                f"{rest_url}/ideas?id=eq.{idea_id}&select=*", headers=headers
            )
            response.raise_for_status()
            ideas_data = response.json()

            if not ideas_data or len(ideas_data) == 0:
                return None

            idea = ideas_data[0]

            # Then, load decomposed_creative linked to this idea
            response = await client.get(
                f"{rest_url}/decomposed_creatives?idea_id=eq.{idea_id}&select=*&order=created_at.desc&limit=1",
                headers=headers,
            )
            response.raise_for_status()
            decomposed_data = response.json()

            # Merge payload fields into idea if decomposed_creative exists
            if decomposed_data and len(decomposed_data) > 0:
                decomposed = decomposed_data[0]
                payload = decomposed.get("payload", {})

                # Handle payload as string or dict
                if isinstance(payload, str):
                    import json

                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = {}

                # Merge Canonical Schema fields into idea
                # V1 required fields
                canonical_fields = [
                    "angle_type",
                    "core_belief",
                    "promise_type",
                    "emotion_primary",
                    "emotion_intensity",
                    "message_structure",
                    "opening_type",
                    "state_before",
                    "state_after",
                    "context_frame",
                    "source_type",
                    "risk_level",
                    "horizon",
                    "schema_version",
                    # V2 optional fields (copywriting psychology)
                    "ump_present",
                    "ump_type",
                    "ums_present",
                    "ums_type",
                    "paradigm_shift_present",
                    "paradigm_shift_type",
                    "specificity_level",
                    "specificity_markers",
                    "hook_mechanism",
                    "hook_stopping_power",
                    "proof_type",
                    "proof_source",
                    "story_type",
                    "story_bridge_present",
                    "desire_level",
                    "emotional_trigger",
                    "social_proof_pattern",
                    "proof_progression",
                    "cta_style",
                    "risk_reversal_type",
                    "focus_score",
                    "idea_count",
                    "emotion_count",
                ]
                for field in canonical_fields:
                    if field in payload:
                        idea[field] = payload[field]

                # Add decomposed_creative reference
                idea["decomposed_creative_id"] = decomposed.get("id")
                idea["creative_id"] = decomposed.get("creative_id")

            # Map cluster_id to active_cluster_id for backward compatibility
            idea["active_cluster_id"] = idea.get("cluster_id")

            return idea
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
                f"{rest_url}/ideas?status=eq.active&select=id", headers=headers
            )
            response.raise_for_status()

            # Get count from Content-Range header
            content_range = response.headers.get("Content-Range", "")
            # Format: "0-N/total" or "*/total"
            total = 0
            if "/" in content_range:
                total = int(content_range.split("/")[1])

            return {
                "active_ideas_count": total,
                "max_active_ideas": 100,
                "current_state": "exploit",
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
                f"{rest_url}/decisions", headers=headers, json=decision
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


async def delete_decision(decision_id: str) -> None:
    """Delete Decision from Supabase (rollback helper)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key, for_write=True)

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{rest_url}/decisions?id=eq.{decision_id}", headers=headers
            )
            response.raise_for_status()
    except Exception:
        # Log but don't raise - this is cleanup
        pass


async def save_decision_trace(trace: dict) -> dict:
    """Save Decision Trace to Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key, for_write=True)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{rest_url}/decision_traces", headers=headers, json=trace
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
