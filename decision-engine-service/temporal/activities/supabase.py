"""
Supabase Activities

Temporal activities for Supabase database operations.
Wraps the existing src/services/supabase.py with Temporal activity decorators.

Input validation added per issue #482.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from temporalio import activity
from src.core.http_client import get_http_client

from temporal.models.validators import (
    validate_uuid,
    validate_sha256_hash,
    validate_url,
    validate_optional_uuid,
    validate_enum,
    validate_dict_payload,
    CREATIVE_STATUSES,
    SOURCE_TYPES,
)

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

    Raises:
        ValueError: If input validation fails
    """
    import uuid

    # Input validation
    video_url = validate_url(video_url, "video_url")
    source_type = validate_enum(source_type, SOURCE_TYPES, "source_type")
    buyer_id = validate_optional_uuid(buyer_id, "buyer_id")

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

    client = get_http_client()
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

    Raises:
        ValueError: If input validation fails
    """
    import uuid

    # Input validation
    video_url = validate_url(video_url, "video_url")
    buyer_id = validate_uuid(buyer_id, "buyer_id")
    if not tracker_id or not tracker_id.strip():
        raise ValueError("tracker_id cannot be empty")
    tracker_id = tracker_id.strip()

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

    client = get_http_client()
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
        activity.logger.info(f"Historical creative {created_creative['id']} has metrics: {metrics}")
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

    Raises:
        ValueError: If creative_id is not a valid UUID
    """
    # Input validation
    creative_id = validate_uuid(creative_id, "creative_id")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
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

    Raises:
        ValueError: If idea_id is not a valid UUID
    """
    # Input validation
    idea_id = validate_uuid(idea_id, "idea_id")

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

    Raises:
        ValueError: If canonical_hash is not a valid SHA256 hash
    """
    # Input validation
    canonical_hash = validate_sha256_hash(canonical_hash, "canonical_hash")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
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
    Create new idea in Supabase atomically with decomposed_creative link.

    Uses RPC function create_idea_with_link for atomic operation.
    Issue #576: Ensures idea creation and link are in single transaction.

    Args:
        canonical_hash: SHA256 hash
        decomposed_creative_id: Linked decomposed creative
        buyer_id: Optional buyer reference (not stored)
        avatar_id: Optional avatar reference

    Returns:
        Created idea dict

    Raises:
        ValueError: If input validation fails
        RuntimeError: If RPC call fails
    """
    import uuid

    # Input validation
    canonical_hash = validate_sha256_hash(canonical_hash, "canonical_hash")
    decomposed_creative_id = validate_uuid(decomposed_creative_id, "decomposed_creative_id")
    buyer_id = validate_optional_uuid(buyer_id, "buyer_id")
    avatar_id = validate_optional_uuid(avatar_id, "avatar_id")

    supabase_url, supabase_key = _get_credentials()
    # RPC URL is at /rest/v1/rpc/<function_name>
    rpc_url = f"{supabase_url}/rpc/create_idea_with_link"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "p_idea_id": str(uuid.uuid4()),
        "p_canonical_hash": canonical_hash,
        "p_avatar_id": avatar_id,
        "p_decomposed_creative_id": decomposed_creative_id,
    }

    client = get_http_client()
    response = await client.post(rpc_url, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()

    if not result or "idea" not in result:
        raise RuntimeError("Failed to create idea: no data returned from RPC")

    created_idea = result["idea"]
    activity.logger.info(
        f"Created idea {created_idea['id']} with linked decomposed_creative {decomposed_creative_id}"
    )
    return created_idea


@activity.defn
async def upsert_idea(
    canonical_hash: str,
    decomposed_creative_id: str,
    buyer_id: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atomically find or create idea by canonical_hash with decomposed_creative link.

    Uses RPC function upsert_idea_with_link for atomic operation.
    Issue #576: Ensures all operations are in single transaction.
    Safe from TOCTOU race conditions (also fixes issue #471).

    Args:
        canonical_hash: SHA256 hash
        decomposed_creative_id: Linked decomposed creative
        buyer_id: Optional buyer reference (not stored in ideas table)
        avatar_id: Optional avatar reference

    Returns:
        Dict with idea data and 'upsert_status': 'created' or 'existing'

    Raises:
        ValueError: If input validation fails
        RuntimeError: If RPC call fails
    """
    import uuid

    # Input validation
    canonical_hash = validate_sha256_hash(canonical_hash, "canonical_hash")
    decomposed_creative_id = validate_uuid(decomposed_creative_id, "decomposed_creative_id")
    buyer_id = validate_optional_uuid(buyer_id, "buyer_id")
    avatar_id = validate_optional_uuid(avatar_id, "avatar_id")

    supabase_url, supabase_key = _get_credentials()
    rpc_url = f"{supabase_url}/rpc/upsert_idea_with_link"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "p_idea_id": str(uuid.uuid4()),
        "p_canonical_hash": canonical_hash,
        "p_avatar_id": avatar_id,
        "p_decomposed_creative_id": decomposed_creative_id,
    }

    client = get_http_client()
    response = await client.post(rpc_url, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()

    if not result or "idea" not in result:
        raise RuntimeError("Failed to upsert idea: no data returned from RPC")

    idea = result["idea"]
    upsert_status = result.get("upsert_status", "unknown")
    idea["upsert_status"] = upsert_status

    activity.logger.info(
        f"{'Created new' if upsert_status == 'created' else 'Found existing'} idea "
        f"{idea['id']} for hash {canonical_hash[:16]}..."
    )
    return idea


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
        payload: LLM decomposition payload (must be a dict)
        canonical_hash: Computed canonical hash
        transcript_id: Optional transcript reference

    Returns:
        Created decomposed_creative dict

    Raises:
        ValueError: If input validation fails
    """
    import uuid

    # Input validation
    creative_id = validate_uuid(creative_id, "creative_id")
    canonical_hash = validate_sha256_hash(canonical_hash, "canonical_hash")
    transcript_id = validate_optional_uuid(transcript_id, "transcript_id")
    payload = validate_dict_payload(payload, "payload")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Note: canonical_hash and transcript_id are passed but not stored in DB
    # canonical_hash is used for idea deduplication later in workflow
    # Don't use json.dumps() - Supabase REST API serializes the body automatically
    decomposed = {
        "id": str(uuid.uuid4()),
        "creative_id": creative_id,
        "payload": payload,  # Pass dict directly, not json.dumps()
        "schema_version": payload.get("schema_version", "v1"),
        "created_at": datetime.utcnow().isoformat(),
    }

    client = get_http_client()
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
async def update_creative_status(
    creative_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """
    Update creative status.

    Args:
        creative_id: Creative UUID
        status: New status value (registered, processing, processed, failed)
        error: Optional error message when status='failed'

    Raises:
        ValueError: If input validation fails
    """
    # Input validation
    creative_id = validate_uuid(creative_id, "creative_id")
    status = validate_enum(status, CREATIVE_STATUSES, "status")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Add error info for failed status
    if status == "failed":
        update_data["error"] = error[:1000] if error else "Unknown error"
        update_data["failed_at"] = datetime.utcnow().isoformat()

    client = get_http_client()
    patch_response = await client.patch(
        f"{rest_url}/creatives?id=eq.{creative_id}",
        headers=headers,
        json=update_data,
    )
    patch_response.raise_for_status()


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

    Raises:
        ValueError: If input validation fails
    """
    import uuid

    # Input validation
    if not event_type or not event_type.strip():
        raise ValueError("event_type cannot be empty")
    event_type = event_type.strip()
    entity_id = validate_optional_uuid(entity_id, "entity_id")

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

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/event_log",
        headers=headers,
        json=event,
    )
    response.raise_for_status()
    data = response.json()

    return data[0] if data else event


@activity.defn
async def save_transcript(
    creative_id: str,
    transcript_text: str,
    assemblyai_transcript_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save transcript to Supabase transcripts table with version management.

    If transcript for creative already exists, creates new version.
    Implements idempotency - if same assemblyai_transcript_id exists, returns existing.

    Args:
        creative_id: Creative UUID
        transcript_text: Full transcript text from AssemblyAI
        assemblyai_transcript_id: AssemblyAI transcript ID for audit trail

    Returns:
        Saved transcript dict with id, creative_id, version, transcript_text

    Raises:
        ValueError: If input validation fails
    """
    # Input validation
    creative_id = validate_uuid(creative_id, "creative_id")
    if not transcript_text or not transcript_text.strip():
        raise ValueError("transcript_text cannot be empty")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)
    read_headers = _get_headers(supabase_key)

    client = get_http_client()
    # Note: assemblyai_transcript_id column doesn't exist in DB
    # Idempotency handled via UNIQUE(creative_id, version) constraint

    # Get current max version for creative
    response = await client.get(
        f"{rest_url}/transcripts"
        f"?creative_id=eq.{creative_id}"
        f"&select=version"
        f"&order=version.desc"
        f"&limit=1",
        headers=read_headers,
    )
    response.raise_for_status()
    versions = response.json()

    next_version = 1
    if versions and versions[0].get("version"):
        next_version = versions[0]["version"] + 1

    # Insert new transcript
    transcript = {
        "creative_id": creative_id,
        "version": next_version,
        "transcript_text": transcript_text,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Use on_conflict for idempotent retry handling (Issue #579)
    # UNIQUE constraint: (creative_id, version)
    upsert_headers = {
        **headers,
        "Prefer": "resolution=ignore-duplicates,return=representation",
    }
    response = await client.post(
        f"{rest_url}/transcripts?on_conflict=creative_id,version",
        headers=upsert_headers,
        json=transcript,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        # Conflict occurred (retry case) - fetch existing transcript
        response = await client.get(
            f"{rest_url}/transcripts"
            f"?creative_id=eq.{creative_id}"
            f"&version=eq.{next_version}"
            f"&select=*",
            headers=read_headers,
        )
        response.raise_for_status()
        existing = response.json()
        if existing:
            activity.logger.info(
                f"Transcript already exists (retry case) creative={creative_id}, version={next_version}"
            )
            return existing[0]
        raise RuntimeError("Failed to save transcript: no data returned")

    activity.logger.info(f"Saved transcript for creative={creative_id}, version={next_version}")
    return data[0]


@activity.defn
async def get_existing_transcript(creative_id: str) -> Optional[Dict[str, Any]]:
    """
    Get latest transcript for creative if exists.

    Used for recovery: if decomposition fails, we can reuse saved transcript
    instead of paying for re-transcription.

    Args:
        creative_id: Creative UUID

    Returns:
        Latest transcript dict or None

    Raises:
        ValueError: If creative_id is not a valid UUID
    """
    # Input validation
    creative_id = validate_uuid(creative_id, "creative_id")

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/transcripts?creative_id=eq.{creative_id}&select=*&order=version.desc&limit=1",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        activity.logger.info(
            f"Found existing transcript for creative={creative_id}, "
            f"version={data[0].get('version')}"
        )
    return data[0] if data else None
