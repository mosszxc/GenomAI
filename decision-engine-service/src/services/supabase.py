"""
Supabase client and data access functions

Uses direct HTTP requests with proper schema headers to ensure
all operations use the genomai schema.
"""

import os
import httpx
from src.core.http_client import get_http_client
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

        client = get_http_client()
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

        client = get_http_client()
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


async def get_existing_decision(idea_id: str, decision_epoch: int) -> dict | None:
    """
    Check if a decision already exists for this idea and epoch.

    Used for idempotency - prevents duplicate decisions from being created.

    Args:
        idea_id: The idea UUID
        decision_epoch: The decision epoch number

    Returns:
        Existing decision dict if found, None otherwise
    """
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key)

        client = get_http_client()
        response = await client.get(
            f"{rest_url}/decisions?idea_id=eq.{idea_id}&decision_epoch=eq.{decision_epoch}&select=*&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]
        return None
    except Exception:
        # On error, return None to allow new decision creation
        return None


async def get_decision_trace(decision_id: str) -> dict | None:
    """
    Load Decision Trace by decision_id.

    Args:
        decision_id: The decision UUID

    Returns:
        Decision trace dict if found, None otherwise
    """
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key)

        client = get_http_client()
        response = await client.get(
            f"{rest_url}/decision_traces?decision_id=eq.{decision_id}&select=*&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]
        return None
    except Exception:
        return None


async def save_decision(decision: dict) -> dict:
    """Save Decision to Supabase (schema: genomai)"""
    try:
        rest_url, supabase_key = _get_credentials()
        headers = _get_headers(supabase_key, for_write=True)

        client = get_http_client()
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

        client = get_http_client()
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

        client = get_http_client()
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


async def save_decision_with_trace(decision: dict, trace: dict) -> dict:
    """
    Save Decision and Decision Trace atomically using RPC.

    Uses Supabase RPC function to ensure both records are saved
    in a single transaction. If either fails, both are rolled back.

    Args:
        decision: Decision dict with id, idea_id, decision, decision_epoch, created_at
        trace: Decision trace dict with id, decision_id, checks, result, created_at

    Returns:
        dict: {"decision": {...}, "trace": {...}}

    Raises:
        SupabaseError: If the RPC call fails
    """
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise SupabaseError("Missing Supabase credentials")

        rpc_url = f"{supabase_url}/rest/v1/rpc/save_decision_with_trace"

        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "p_decision_id": decision["id"],
            "p_idea_id": decision["idea_id"],
            "p_decision": decision["decision"],
            "p_decision_epoch": decision["decision_epoch"],
            "p_decision_created_at": decision["created_at"],
            "p_trace_id": trace["id"],
            "p_trace_checks": trace["checks"],
            "p_trace_result": trace["result"],
            "p_trace_created_at": trace["created_at"],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(rpc_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        if "23505" in error_detail:
            raise SupabaseError(
                f"Decision already exists for idea_id={decision['idea_id']} epoch={decision['decision_epoch']}"
            )
        raise SupabaseError(f"Failed to save decision with trace: {error_detail}")
    except Exception as e:
        raise SupabaseError(f"Failed to save decision with trace: {str(e)}")
