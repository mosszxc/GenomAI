"""
Supabase Activities

Temporal activities for Supabase database operations.
Wraps the existing src/services/supabase.py with Temporal activity decorators.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from temporalio import activity
import httpx

# Schema name for all operations
SCHEMA = "genomai"


def _get_credentials() -> tuple[str, str]:
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with genomai schema."""
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


@activity.defn
async def create_creative(
    video_url: str,
    source_type: str,
    buyer_id: Optional[str] = None,
    target_geo: Optional[str] = None,
    target_vertical: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create new creative in Supabase.

    Args:
        video_url: Video URL (required)
        source_type: Source type e.g. 'telegram', 'keitaro' (required)
        buyer_id: Optional buyer UUID
        target_geo: Optional target GEO
        target_vertical: Optional target vertical

    Returns:
        Created creative dict with id
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    creative = {
        "id": str(uuid.uuid4()),
        "video_url": video_url,
        "source_type": source_type,
        "status": "registered",
        "created_at": datetime.utcnow().isoformat(),
    }

    if buyer_id:
        creative["buyer_id"] = buyer_id
    if target_geo:
        creative["target_geo"] = target_geo
    if target_vertical:
        creative["target_vertical"] = target_vertical

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/creatives",
            headers=headers,
            json=creative,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to create creative: no data returned")

        return data[0]


@activity.defn
async def create_historical_creative(
    video_url: str,
    tracker_id: str,
    buyer_id: str,
    metrics: Optional[Dict[str, Any]] = None,
    target_geo: Optional[str] = None,
    target_vertical: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create creative from historical import with tracker_id and metrics.

    Args:
        video_url: Video URL (required)
        tracker_id: Keitaro campaign/tracker ID (required)
        buyer_id: Buyer UUID (required)
        metrics: Optional Keitaro metrics from import queue
        target_geo: Optional target GEO
        target_vertical: Optional target vertical

    Returns:
        Created creative dict with id
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    creative = {
        "id": str(uuid.uuid4()),
        "video_url": video_url,
        "tracker_id": tracker_id,
        "buyer_id": buyer_id,
        "source_type": "historical",
        "status": "registered",
        "created_at": datetime.utcnow().isoformat(),
    }

    if target_geo:
        creative["target_geo"] = target_geo
    if target_vertical:
        creative["target_vertical"] = target_vertical

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/creatives",
            headers=headers,
            json=creative,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to create historical creative: no data returned")

        created_creative = data[0]

        # If we have metrics, create outcome_aggregate record
        if metrics:
            activity.logger.info(
                f"Historical creative {created_creative['id']} has metrics: {metrics}"
            )
            # Metrics will be processed by outcome_aggregator later

        return created_creative


@activity.defn
async def get_creative(creative_id: str) -> Optional[Dict[str, Any]]:
    """
    Load creative from Supabase.

    Args:
        creative_id: Creative UUID

    Returns:
        Creative dict or None if not found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/creatives?id=eq.{creative_id}&select=*",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        return data[0] if data else None


@activity.defn
async def get_idea(idea_id: str) -> Optional[Dict[str, Any]]:
    """
    Load idea from Supabase with joined decomposed_creative data.

    Reuses logic from src/services/supabase.load_idea()

    Args:
        idea_id: Idea UUID

    Returns:
        Idea dict with merged canonical schema fields, or None
    """
    # Import existing function to reuse logic
    from src.services.supabase import load_idea

    return await load_idea(idea_id)


@activity.defn
async def check_idea_exists(canonical_hash: str) -> Optional[Dict[str, Any]]:
    """
    Check if idea with canonical hash already exists.

    Args:
        canonical_hash: SHA256 hash of decomposed creative

    Returns:
        Existing idea dict or None
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/ideas?canonical_hash=eq.{canonical_hash}&select=*&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        return data[0] if data else None


@activity.defn
async def create_idea(
    canonical_hash: str,
    decomposed_creative_id: str,
    buyer_id: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create new idea in Supabase.

    Args:
        canonical_hash: SHA256 hash
        decomposed_creative_id: Linked decomposed creative
        buyer_id: Optional buyer reference
        avatar_id: Optional avatar reference

    Returns:
        Created idea dict
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    idea = {
        "id": str(uuid.uuid4()),
        "canonical_hash": canonical_hash,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
    }

    if buyer_id:
        idea["buyer_id"] = buyer_id
    if avatar_id:
        idea["avatar_id"] = avatar_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/ideas",
            headers=headers,
            json=idea,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to create idea: no data returned")

        created_idea = data[0]

        # Link decomposed_creative to idea
        await client.patch(
            f"{rest_url}/decomposed_creatives?id=eq.{decomposed_creative_id}",
            headers=headers,
            json={"idea_id": created_idea["id"]},
        )

        return created_idea


@activity.defn
async def save_decomposed_creative(
    creative_id: str,
    payload: Dict[str, Any],
    canonical_hash: str,
    transcript_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save decomposed creative to Supabase.

    Args:
        creative_id: Source creative UUID
        payload: LLM decomposition payload
        canonical_hash: Computed canonical hash
        transcript_id: Optional transcript reference

    Returns:
        Created decomposed_creative dict
    """
    import uuid
    import json

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    decomposed = {
        "id": str(uuid.uuid4()),
        "creative_id": creative_id,
        "payload": json.dumps(payload) if isinstance(payload, dict) else payload,
        "canonical_hash": canonical_hash,
        "schema_version": payload.get("schema_version", "v1"),
        "created_at": datetime.utcnow().isoformat(),
    }

    if transcript_id:
        decomposed["transcript_id"] = transcript_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/decomposed_creatives",
            headers=headers,
            json=decomposed,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to save decomposed creative")

        return data[0]


@activity.defn
async def update_creative_status(creative_id: str, status: str) -> None:
    """
    Update creative status.

    Args:
        creative_id: Creative UUID
        status: New status value
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{rest_url}/creatives?id=eq.{creative_id}",
            headers=headers,
            json={"status": status, "updated_at": datetime.utcnow().isoformat()},
        )


@activity.defn
async def emit_event(
    event_type: str,
    payload: Dict[str, Any],
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Emit event to Supabase event_log table.

    Replaces n8n event emission pattern.

    Args:
        event_type: Event type (e.g., "CreativeDecomposed", "DecisionMade")
        payload: Event payload
        entity_type: Optional entity type (e.g., "creative", "decision")
        entity_id: Optional entity UUID

    Returns:
        Created event dict
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "payload": payload,
        "occurred_at": datetime.utcnow().isoformat(),
    }

    if entity_type:
        event["entity_type"] = entity_type
    if entity_id:
        event["entity_id"] = entity_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/event_log",
            headers=headers,
            json=event,
        )
        response.raise_for_status()
        data = response.json()

        return data[0] if data else event
