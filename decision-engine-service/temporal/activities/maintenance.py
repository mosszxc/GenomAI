"""
Maintenance Activities

Temporal activities for periodic maintenance tasks.
Replaces n8n workflow H1uuOanSy627H4kg (Pipeline Health Monitor).

Includes:
- Stale buyer state reset
- Recommendation expiry
- Data integrity checks
- Staleness detection (Inspiration System)
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from temporalio import activity
from temporalio.client import Client as TemporalClient
from temporalio.exceptions import ApplicationError
from src.core.http_client import get_http_client


SCHEMA = "genomai"


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    return f"{supabase_url}/rest/v1", supabase_key


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


@activity.defn
async def reset_stale_buyer_states(timeout_hours: int = 6) -> int:
    """
    Reset buyer states that have been stuck for too long.

    Buyers with states like 'awaiting_name', 'awaiting_geo', etc.
    for more than timeout_hours are reset to allow fresh onboarding.

    Args:
        timeout_hours: Hours after which a state is considered stale

    Returns:
        Number of buyer states reset
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Calculate cutoff time
    cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Looking for buyer states older than {cutoff_iso}")

    client = get_http_client()
    # Find stale buyer_states
    # buyer_states uses telegram_id as primary key, not id

    response = await client.get(
        f"{rest_url}/buyer_states"
        f"?updated_at=lt.{cutoff_iso}"
        f"&state=neq.idle"
        "&select=telegram_id,state",
        headers=_get_headers(supabase_key),
    )

    if response.status_code == 404:
        # buyer_states table doesn't exist, skip
        activity.logger.info("No buyer_states table found, skipping reset")
        return 0

    if response.status_code != 200:
        activity.logger.warning(f"Error checking buyer_states: {response.text}")
        return 0

    stale_states = response.json()

    if not stale_states:
        activity.logger.info("No stale buyer states found")
        return 0

    # Reset stale states to idle
    telegram_ids = [s["telegram_id"] for s in stale_states]
    for telegram_id in telegram_ids:
        await client.patch(
            f"{rest_url}/buyer_states?telegram_id=eq.{telegram_id}",
            headers=headers,
            json={"state": "idle", "context": {}},
        )

    activity.logger.info(f"Reset {len(telegram_ids)} stale buyer states")
    return len(telegram_ids)


@activity.defn
async def expire_old_recommendations(expiry_days: int = 7) -> int:
    """
    Expire recommendations that are too old and never accepted.

    Recommendations with status 'pending' older than expiry_days
    are marked as 'expired'.

    Args:
        expiry_days: Days after which a pending recommendation expires

    Returns:
        Number of recommendations expired
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Calculate cutoff time
    cutoff = datetime.utcnow() - timedelta(days=expiry_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Expiring recommendations older than {cutoff_iso}")

    client = get_http_client()
    # Find old pending recommendations
    response = await client.get(
        f"{rest_url}/recommendations"
        f"?status=eq.pending"
        f"&created_at=lt.{cutoff_iso}"
        "&select=id",
        headers=_get_headers(supabase_key),
    )
    response.raise_for_status()

    old_recommendations = response.json()

    if not old_recommendations:
        activity.logger.info("No old pending recommendations found")
        return 0

    # Mark as expired
    rec_ids = [r["id"] for r in old_recommendations]

    response = await client.patch(
        f"{rest_url}/recommendations?id=in.({','.join(rec_ids)})",
        headers=headers,
        json={
            "status": "expired",
            "expires_at": datetime.utcnow().isoformat(),
        },
    )
    response.raise_for_status()

    activity.logger.info(f"Expired {len(rec_ids)} old recommendations")
    return len(rec_ids)


@activity.defn
async def mark_stuck_transcriptions_failed(timeout_minutes: int = 10) -> int:
    """
    Mark creatives stuck in transcription queue as failed.

    Creatives with status 'registered' and no transcript for more than
    timeout_minutes are marked as 'transcription_failed'.

    Args:
        timeout_minutes: Minutes after which a transcription is considered stuck

    Returns:
        Number of creatives marked as failed
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Looking for stuck transcriptions older than {cutoff_iso}")

    client = get_http_client()
    # Find creatives without transcripts that are older than timeout
    # Using left join simulation: get registered creatives, then check for transcripts
    response = await client.get(
        f"{rest_url}/creatives"
        f"?status=eq.registered"
        f"&created_at=lt.{cutoff_iso}"
        "&select=id,video_url,created_at",
        headers=_get_headers(supabase_key),
    )

    if response.status_code != 200:
        activity.logger.warning(f"Error checking creatives: {response.text}")
        return 0

    registered_creatives = response.json()

    if not registered_creatives:
        activity.logger.info("No stuck transcriptions found")
        return 0

    # Check which ones have transcripts
    stuck_ids = []
    for creative in registered_creatives:
        transcript_resp = await client.get(
            f"{rest_url}/transcripts?creative_id=eq.{creative['id']}&limit=1",
            headers=_get_headers(supabase_key),
        )
        if transcript_resp.status_code == 200 and not transcript_resp.json():
            stuck_ids.append(creative["id"])

    if not stuck_ids:
        activity.logger.info("No stuck transcriptions found")
        return 0

    # Mark as transcription_failed
    for creative_id in stuck_ids:
        await client.patch(
            f"{rest_url}/creatives?id=eq.{creative_id}",
            headers=headers,
            json={
                "status": "transcription_failed",
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

    activity.logger.info(f"Marked {len(stuck_ids)} creatives as transcription_failed")
    return len(stuck_ids)


@activity.defn
async def archive_failed_creatives(retention_days: int = 7) -> int:
    """
    Archive creatives that have been in failed status for too long.

    Creatives with status 'transcription_failed' older than retention_days
    are archived to keep the active pipeline clean.

    Args:
        retention_days: Days to retain failed creatives before archiving

    Returns:
        Number of creatives archived
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Looking for failed creatives older than {cutoff_iso}")

    client = get_http_client()
    # Find old failed creatives
    response = await client.get(
        f"{rest_url}/creatives"
        f"?status=eq.transcription_failed"
        f"&updated_at=lt.{cutoff_iso}"
        "&select=id,video_url,updated_at",
        headers=_get_headers(supabase_key),
    )

    if response.status_code != 200:
        activity.logger.warning(f"Error checking failed creatives: {response.text}")
        return 0

    failed_creatives = response.json()

    if not failed_creatives:
        activity.logger.info("No old failed creatives found")
        return 0

    # Archive them
    archived_count = 0
    for creative in failed_creatives:
        archive_resp = await client.patch(
            f"{rest_url}/creatives?id=eq.{creative['id']}",
            headers=headers,
            json={
                "status": "archived",
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        if archive_resp.status_code in (200, 204):
            archived_count += 1
            activity.logger.info(
                f"Archived creative {creative['id'][:8]} "
                f"(failed since {creative['updated_at'][:10]})"
            )

    activity.logger.info(f"Archived {archived_count} failed creatives")
    return archived_count


@activity.defn
async def check_data_integrity() -> List[str]:
    """
    Check for data integrity issues.

    Checks:
    - Orphaned creatives (no idea)
    - Ideas without decisions for > 24h
    - Hypotheses without delivery for > 1h

    Returns:
        List of integrity issues found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    issues = []

    activity.logger.info("Running data integrity checks")

    client = get_http_client()
    # Check 1: Ideas without decisions for > 24h
    cutoff_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()

    response = await client.get(
        f"{rest_url}/ideas?created_at=lt.{cutoff_24h}&select=id,created_at&limit=100",
        headers=headers,
    )

    if response.status_code == 200:
        old_ideas = response.json()

        # Check which ones have decisions
        for idea in old_ideas:
            decision_resp = await client.get(
                f"{rest_url}/decisions?idea_id=eq.{idea['id']}&limit=1",
                headers=headers,
            )
            if decision_resp.status_code == 200 and not decision_resp.json():
                issues.append(f"Idea {idea['id'][:8]} has no decision after 24h")

    # Check 2: Pending hypotheses for > 1h without delivery
    # Only check hypotheses with status=pending (exclude failed/delivered)
    cutoff_1h = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    response = await client.get(
        f"{rest_url}/hypotheses"
        f"?delivered_at=is.null"
        f"&status=eq.pending"
        f"&created_at=lt.{cutoff_1h}"
        "&select=id,buyer_id"
        "&limit=100",
        headers=headers,
    )

    if response.status_code == 200:
        undelivered = response.json()
        # Filter: only hypotheses WITH buyer_id are real issues
        # (hypotheses without buyer cannot be delivered)
        real_issues = [h for h in undelivered if h.get("buyer_id")]
        orphan_hypotheses = [h for h in undelivered if not h.get("buyer_id")]

        if real_issues:
            ids = [h["id"][:8] for h in real_issues[:5]]
            issues.append(
                f"{len(real_issues)} hypotheses pending delivery for > 1h: {', '.join(ids)}"
            )
        if orphan_hypotheses:
            ids = [h["id"][:8] for h in orphan_hypotheses[:5]]
            issues.append(
                f"{len(orphan_hypotheses)} orphan hypotheses without buyer_id: {', '.join(ids)}"
            )

    if issues:
        activity.logger.warning(f"Found {len(issues)} integrity issues")
    else:
        activity.logger.info("No integrity issues found")

    return issues


@activity.defn
async def cleanup_orphaned_hypotheses() -> int:
    """
    Delete hypotheses without buyer_id (orphaned).

    Issue #475: Hypotheses created without buyer_id can never be delivered
    and accumulate in the database. This activity cleans them up.

    Returns:
        Number of orphaned hypotheses deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    activity.logger.info("Looking for orphaned hypotheses (buyer_id IS NULL)")

    client = get_http_client()
    # Find orphaned hypotheses
    response = await client.get(
        f"{rest_url}/hypotheses?buyer_id=is.null&select=id",
        headers=_get_headers(supabase_key),
    )

    if response.status_code != 200:
        activity.logger.warning(f"Error checking orphaned hypotheses: {response.text}")
        return 0

    orphaned = response.json()

    if not orphaned:
        activity.logger.info("No orphaned hypotheses found")
        return 0

    # Delete orphaned hypotheses
    orphan_ids = [h["id"] for h in orphaned]
    deleted_count = 0

    for orphan_id in orphan_ids:
        delete_resp = await client.delete(
            f"{rest_url}/hypotheses?id=eq.{orphan_id}",
            headers=headers,
        )
        if delete_resp.status_code in (200, 204):
            deleted_count += 1
            activity.logger.info(f"Deleted orphaned hypothesis {orphan_id[:8]}")

    activity.logger.info(f"Deleted {deleted_count} orphaned hypotheses")
    return deleted_count


@activity.defn
async def emit_maintenance_event(
    buyers_reset: int,
    recommendations_expired: int,
    issues_count: int,
    issues_details: Optional[List[str]] = None,
) -> dict:
    """
    Emit maintenance completed event.

    Args:
        buyers_reset: Number of buyer states reset
        recommendations_expired: Number of recommendations expired
        issues_count: Number of integrity issues found
        issues_details: List of integrity issue descriptions (optional)

    Returns:
        Created event dict
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "buyers_reset": buyers_reset,
        "recommendations_expired": recommendations_expired,
        "integrity_issues": issues_count,
    }
    # Add details if present (for debugging/alerting)
    if issues_details:
        payload["integrity_issues_details"] = issues_details

    event = {
        "id": str(uuid.uuid4()),
        "event_type": "MaintenanceCompleted",
        "entity_type": "system",
        "payload": payload,
        "occurred_at": datetime.utcnow().isoformat(),
    }

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
async def release_orphaned_agent_tasks(timeout_minutes: int = 10) -> int:
    """
    Release agent tasks that have not received a heartbeat for too long.

    Tasks with status='claimed' and last_heartbeat older than timeout_minutes
    are marked as 'abandoned' and can be reclaimed.

    Part of Multi-Agent Orchestration Phase 2 (Issue #350).

    Args:
        timeout_minutes: Minutes after which a task without heartbeat is abandoned

    Returns:
        Number of tasks released
    """
    rest_url, supabase_key = _get_credentials()

    activity.logger.info(
        f"Checking for orphaned agent tasks (timeout={timeout_minutes}min)"
    )

    client = get_http_client()
    # Call the release_orphaned_tasks function via RPC
    response = await client.post(
        f"{rest_url}/rpc/release_orphaned_tasks",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        },
        json={"p_timeout_minutes": timeout_minutes},
    )

    if response.status_code == 404:
        # Function or table doesn't exist yet
        activity.logger.info("release_orphaned_tasks function not found, skipping")
        return 0

    if response.status_code != 200:
        activity.logger.warning(f"Error releasing orphaned tasks: {response.text}")
        return 0

    released_count = response.json()
    if released_count > 0:
        activity.logger.warning(f"Released {released_count} orphaned agent tasks")
    else:
        activity.logger.info("No orphaned agent tasks found")

    return released_count


@dataclass
class StuckCreative:
    """Creative stuck in pipeline."""

    creative_id: str
    buyer_id: Optional[str]
    stuck_reason: str  # "transcription" | "decomposition"
    stuck_since: str  # ISO timestamp
    stuck_duration_minutes: int  # Issue #481: how long it's been stuck


def _calculate_stuck_duration_minutes(stuck_since_iso: str) -> int:
    """Calculate how many minutes since stuck_since timestamp."""
    try:
        # Parse ISO timestamp (handle with/without timezone)
        stuck_since = stuck_since_iso.replace("Z", "+00:00")
        if "+" not in stuck_since and "-" not in stuck_since[10:]:
            # No timezone, assume UTC
            stuck_dt = datetime.fromisoformat(stuck_since)
        else:
            stuck_dt = datetime.fromisoformat(stuck_since).replace(tzinfo=None)
        return int((datetime.utcnow() - stuck_dt).total_seconds() / 60)
    except Exception:
        return 0


@activity.defn
async def find_stuck_creatives(
    transcription_timeout_minutes: int = 5,
    decomposition_timeout_minutes: int = 30,
) -> List[dict]:
    """
    Find creatives stuck in transcription or decomposition stages.

    Issue #398: Creatives can get stuck if:
    1. Workflow never started (status='pending', no transcript)
    2. Workflow failed between transcript and decomposition

    Issue #481: Now includes stuck_duration_minutes for recovery decisions.

    Args:
        transcription_timeout_minutes: Minutes to wait before considering
            transcription as stuck
        decomposition_timeout_minutes: Minutes to wait before considering
            decomposition as stuck

    Returns:
        List of stuck creatives with their creative_id, buyer_id, stuck_reason,
        stuck_since, and stuck_duration_minutes
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    stuck_creatives = []

    # Cutoffs
    transcription_cutoff = (
        datetime.utcnow() - timedelta(minutes=transcription_timeout_minutes)
    ).isoformat()
    decomposition_cutoff = (
        datetime.utcnow() - timedelta(minutes=decomposition_timeout_minutes)
    ).isoformat()

    activity.logger.info(
        f"Looking for stuck creatives: "
        f"transcription>{transcription_timeout_minutes}min, "
        f"decomposition>{decomposition_timeout_minutes}min"
    )

    client = get_http_client()
    # 1. Find creatives stuck on transcription
    # status='pending' AND no transcript AND created > X minutes ago
    response = await client.get(
        f"{rest_url}/creatives"
        f"?status=eq.pending"
        f"&created_at=lt.{transcription_cutoff}"
        f"&created_at=gt.{(datetime.utcnow() - timedelta(hours=24)).isoformat()}"
        "&select=id,buyer_id,created_at",
        headers=headers,
    )

    if response.status_code == 200:
        pending_creatives = response.json()

        for creative in pending_creatives:
            # Check if transcript exists
            transcript_resp = await client.get(
                f"{rest_url}/transcripts?creative_id=eq.{creative['id']}&limit=1",
                headers=headers,
            )
            if transcript_resp.status_code == 200 and not transcript_resp.json():
                stuck_since = creative["created_at"]
                stuck_creatives.append(
                    {
                        "creative_id": creative["id"],
                        "buyer_id": creative.get("buyer_id"),
                        "stuck_reason": "transcription",
                        "stuck_since": stuck_since,
                        "stuck_duration_minutes": _calculate_stuck_duration_minutes(
                            stuck_since
                        ),
                    }
                )

    # 2. Find creatives stuck on decomposition
    # Has transcript but no decomposed_creative AND transcript created > X minutes ago
    response = await client.get(
        f"{rest_url}/transcripts"
        f"?created_at=lt.{decomposition_cutoff}"
        f"&created_at=gt.{(datetime.utcnow() - timedelta(hours=24)).isoformat()}"
        "&select=creative_id,created_at",
        headers=headers,
    )

    if response.status_code == 200:
        transcripts = response.json()

        for transcript in transcripts:
            creative_id = transcript["creative_id"]

            # Check if decomposed_creative exists
            decomp_resp = await client.get(
                f"{rest_url}/decomposed_creatives?creative_id=eq.{creative_id}&limit=1",
                headers=headers,
            )

            if decomp_resp.status_code == 200 and not decomp_resp.json():
                # Get buyer_id from creative
                creative_resp = await client.get(
                    f"{rest_url}/creatives?id=eq.{creative_id}&select=buyer_id",
                    headers=headers,
                )
                buyer_id = None
                if creative_resp.status_code == 200:
                    creatives = creative_resp.json()
                    if creatives:
                        buyer_id = creatives[0].get("buyer_id")

                stuck_since = transcript["created_at"]
                stuck_creatives.append(
                    {
                        "creative_id": creative_id,
                        "buyer_id": buyer_id,
                        "stuck_reason": "decomposition",
                        "stuck_since": stuck_since,
                        "stuck_duration_minutes": _calculate_stuck_duration_minutes(
                            stuck_since
                        ),
                    }
                )

    if stuck_creatives:
        activity.logger.warning(
            f"Found {len(stuck_creatives)} stuck creatives: "
            f"transcription={len([s for s in stuck_creatives if s['stuck_reason'] == 'transcription'])}, "
            f"decomposition={len([s for s in stuck_creatives if s['stuck_reason'] == 'decomposition'])}"
        )
    else:
        activity.logger.info("No stuck creatives found")

    return stuck_creatives


@activity.defn
async def find_failed_creatives_for_retry(
    max_retry_count: int = 3,
    min_age_minutes: int = 30,
) -> List[dict]:
    """
    Find failed creatives eligible for retry.

    Issue #472: Creatives with status='failed' can be retried up to max_retry_count times.
    Only creatives that failed more than min_age_minutes ago are considered.

    Args:
        max_retry_count: Maximum number of retry attempts before abandoning
        min_age_minutes: Minimum age of failure before retry (to avoid rapid retries)

    Returns:
        List of creatives eligible for retry with their creative_id, buyer_id, error
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Only retry creatives that failed at least min_age_minutes ago
    cutoff = (datetime.utcnow() - timedelta(minutes=min_age_minutes)).isoformat()

    activity.logger.info(
        f"Looking for failed creatives to retry (max_retries={max_retry_count}, "
        f"min_age={min_age_minutes}min)"
    )

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/creatives"
        f"?status=eq.failed"
        f"&retry_count=lt.{max_retry_count}"
        f"&failed_at=lt.{cutoff}"
        "&select=id,buyer_id,error,retry_count,failed_at"
        "&limit=10",  # Process in batches
        headers=headers,
    )

    if response.status_code != 200:
        activity.logger.warning(f"Error finding failed creatives: {response.text}")
        return []

    failed_creatives = response.json()

    if failed_creatives:
        activity.logger.info(
            f"Found {len(failed_creatives)} failed creatives eligible for retry"
        )
    else:
        activity.logger.info("No failed creatives eligible for retry")

    return failed_creatives


@activity.defn
async def reset_creative_for_retry(creative_id: str) -> bool:
    """
    Reset a failed creative for retry.

    Issue #472: Increments retry_count and resets status to 'registered'
    so the creative can be picked up by the pipeline again.

    Args:
        creative_id: Creative UUID to reset

    Returns:
        True if reset successful, False otherwise
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    activity.logger.info(f"Resetting creative {creative_id[:8]} for retry")

    client = get_http_client()
    # First get current retry_count
    get_resp = await client.get(
        f"{rest_url}/creatives?id=eq.{creative_id}&select=retry_count",
        headers=_get_headers(supabase_key),
    )

    if get_resp.status_code != 200 or not get_resp.json():
        activity.logger.warning(f"Creative {creative_id[:8]} not found")
        return False

    current_retry = get_resp.json()[0].get("retry_count", 0)

    # Reset for retry
    response = await client.patch(
        f"{rest_url}/creatives?id=eq.{creative_id}",
        headers=headers,
        json={
            "status": "registered",
            "retry_count": current_retry + 1,
            "error": None,  # Clear previous error
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    if response.status_code in (200, 204):
        activity.logger.info(
            f"Creative {creative_id[:8]} reset for retry #{current_retry + 1}"
        )
        return True
    else:
        activity.logger.warning(
            f"Failed to reset creative {creative_id[:8]}: {response.text}"
        )
        return False


@activity.defn
async def abandon_failed_creative(creative_id: str) -> bool:
    """
    Mark a failed creative as abandoned (too many retries).

    Issue #472: Creatives that exceed max_retry_count are marked as 'abandoned'
    to prevent infinite retry loops.

    Args:
        creative_id: Creative UUID to abandon

    Returns:
        True if successful, False otherwise
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    activity.logger.info(
        f"Abandoning creative {creative_id[:8]} (max retries exceeded)"
    )

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/creatives?id=eq.{creative_id}",
        headers=headers,
        json={
            "status": "abandoned",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    if response.status_code in (200, 204):
        activity.logger.info(f"Creative {creative_id[:8]} marked as abandoned")
        return True
    else:
        activity.logger.warning(
            f"Failed to abandon creative {creative_id[:8]}: {response.text}"
        )
        return False


@activity.defn
async def check_staleness(
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
) -> dict:
    """
    Check system staleness and save snapshot.

    Part of Inspiration System - detects when system needs external inspiration.

    Args:
        avatar_id: Optional avatar filter (None = global)
        geo: Optional geo filter

    Returns:
        dict with staleness metrics and is_stale flag
    """
    # Import here to avoid circular imports
    from src.services.staleness_detector import check_staleness_and_act

    activity.logger.info(f"Checking staleness for avatar={avatar_id}, geo={geo}")

    try:
        result = await check_staleness_and_act(avatar_id, geo)

        # Safe access to staleness_score with default
        staleness_score = result.get("metrics", {}).get("staleness_score")
        if staleness_score is None:
            staleness_score = 0.0

        if result["is_stale"]:
            activity.logger.warning(
                f"System is STALE! Score: {staleness_score:.2f}, "
                f"recommended action: {result.get('recommended_action')}"
            )
        else:
            activity.logger.info(
                f"System is healthy. Staleness score: {staleness_score:.2f}"
            )

        return result
    except Exception as e:
        activity.logger.error(f"Staleness check failed: {e}")
        # Return neutral result on error
        return {
            "metrics": {},
            "is_stale": False,
            "recommended_action": None,
            "error": str(e),
        }


async def _get_temporal_client() -> TemporalClient:
    """Get Temporal client for workflow operations."""
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    return await TemporalClient.connect(temporal_host, namespace=namespace)


@activity.defn
async def cancel_stuck_creative_workflow(creative_id: str) -> bool:
    """
    Cancel a stuck creative pipeline workflow.

    Issue #481: When a creative is stuck for > 2 hours, we need to
    explicitly cancel the workflow before we can restart it.

    Args:
        creative_id: Creative UUID whose workflow should be cancelled

    Returns:
        True if cancelled successfully, False otherwise
    """
    workflow_id = f"creative-pipeline-{creative_id}"

    activity.logger.info(f"Attempting to cancel workflow {workflow_id}")

    try:
        client = await _get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)

        # Check if workflow is running
        try:
            desc = await handle.describe()
            status = desc.status.name if desc.status else "UNKNOWN"

            if status == "RUNNING":
                await handle.cancel()
                activity.logger.info(f"Cancelled stuck workflow {workflow_id}")
                return True
            elif status in ("COMPLETED", "FAILED", "CANCELED", "TERMINATED"):
                activity.logger.info(
                    f"Workflow {workflow_id} already {status}, no cancel needed"
                )
                return True
            else:
                activity.logger.warning(
                    f"Workflow {workflow_id} in unexpected status: {status}"
                )
                return False

        except Exception as e:
            if "not found" in str(e).lower():
                activity.logger.info(
                    f"Workflow {workflow_id} not found, nothing to cancel"
                )
                return True
            raise

    except Exception as e:
        activity.logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
        return False


@activity.defn
async def reset_creative_for_recovery(creative_id: str) -> bool:
    """
    Reset a stuck creative status for recovery.

    Issue #481: After cancelling a stuck workflow, we reset the creative
    status to 'registered' so it can be picked up by a new workflow.

    Args:
        creative_id: Creative UUID to reset

    Returns:
        True if reset successful, False otherwise
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    activity.logger.info(f"Resetting creative {creative_id[:8]} for recovery")

    client = get_http_client()

    # Reset status to 'registered' (not pending) so workflow can process it
    response = await client.patch(
        f"{rest_url}/creatives?id=eq.{creative_id}",
        headers=headers,
        json={
            "status": "registered",
            "error": None,
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    if response.status_code in (200, 204):
        activity.logger.info(
            f"Creative {creative_id[:8]} reset to 'registered' for recovery"
        )
        return True
    else:
        activity.logger.warning(
            f"Failed to reset creative {creative_id[:8]}: {response.text}"
        )
        return False
