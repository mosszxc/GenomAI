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

    # Note: buyer_id is not stored in ideas table, only avatar_id
    idea = {
        "id": str(uuid.uuid4()),
        "canonical_hash": canonical_hash,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
    }

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
async def upsert_idea(
    canonical_hash: str,
    decomposed_creative_id: str,
    buyer_id: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atomically find or create idea by canonical_hash.

    Uses INSERT ... ON CONFLICT DO NOTHING + SELECT pattern.
    Safe from TOCTOU race conditions (fixes issue #471).

    Args:
        canonical_hash: SHA256 hash
        decomposed_creative_id: Linked decomposed creative
        buyer_id: Optional buyer reference (not stored in ideas table)
        avatar_id: Optional avatar reference

    Returns:
        Dict with idea data and 'upsert_status': 'created' or 'existing'
    """
    import uuid

    rest_url, supabase_key = _get_credentials()

    # Step 1: Try INSERT with resolution=ignore-duplicates
    # This does INSERT ... ON CONFLICT DO NOTHING atomically
    headers = _get_headers(supabase_key, for_write=True)
    headers["Prefer"] = "return=representation,resolution=ignore-duplicates"

    idea = {
        "id": str(uuid.uuid4()),
        "canonical_hash": canonical_hash,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
    }

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

        if data:
            # INSERT succeeded - this is a new idea
            created_idea = data[0]
            created_idea["upsert_status"] = "created"

            # Link decomposed_creative to idea
            link_headers = _get_headers(supabase_key, for_write=True)
            await client.patch(
                f"{rest_url}/decomposed_creatives?id=eq.{decomposed_creative_id}",
                headers=link_headers,
                json={"idea_id": created_idea["id"]},
            )

            activity.logger.info(
                f"Created new idea {created_idea['id']} for hash {canonical_hash[:16]}..."
            )
            return created_idea

        # Step 2: INSERT returned empty (conflict) - fetch existing
        read_headers = _get_headers(supabase_key)
        response = await client.get(
            f"{rest_url}/ideas?canonical_hash=eq.{canonical_hash}&select=*&limit=1",
            headers=read_headers,
        )
        response.raise_for_status()
        existing = response.json()

        if existing:
            existing_idea = existing[0]
            existing_idea["upsert_status"] = "existing"

            # Link decomposed_creative to existing idea
            link_headers = _get_headers(supabase_key, for_write=True)
            await client.patch(
                f"{rest_url}/decomposed_creatives?id=eq.{decomposed_creative_id}",
                headers=link_headers,
                json={"idea_id": existing_idea["id"]},
            )

            activity.logger.info(
                f"Found existing idea {existing_idea['id']} for hash {canonical_hash[:16]}..."
            )
            return existing_idea

        # This should not happen - UNIQUE conflict but no record found
        raise RuntimeError(
            f"Race condition recovery failed: idea with hash {canonical_hash} "
            "not found after conflict"
        )


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
        ValueError: If payload is not a valid dict
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Validate payload is a dict (not string, null, array, etc.)
    if not isinstance(payload, dict):
        raise ValueError(
            f"payload must be a dict, got {type(payload).__name__}: {payload!r:.200}"
        )

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
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)
    read_headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # Idempotency check: if same assemblyai_transcript_id exists, return it
        if assemblyai_transcript_id:
            response = await client.get(
                f"{rest_url}/transcripts"
                f"?assemblyai_transcript_id=eq.{assemblyai_transcript_id}"
                f"&select=*&limit=1",
                headers=read_headers,
            )
            response.raise_for_status()
            existing = response.json()
            if existing:
                activity.logger.info(
                    f"Transcript already exists for assemblyai_id={assemblyai_transcript_id}"
                )
                return existing[0]

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

        if assemblyai_transcript_id:
            transcript["assemblyai_transcript_id"] = assemblyai_transcript_id

        response = await client.post(
            f"{rest_url}/transcripts",
            headers=headers,
            json=transcript,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to save transcript: no data returned")

        activity.logger.info(
            f"Saved transcript for creative={creative_id}, version={next_version}"
        )
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
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/transcripts"
            f"?creative_id=eq.{creative_id}"
            f"&select=*"
            f"&order=version.desc"
            f"&limit=1",
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
