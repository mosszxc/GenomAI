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
from datetime import datetime, timedelta
from typing import List, Optional

from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx


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

    async with httpx.AsyncClient() as client:
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

    async with httpx.AsyncClient() as client:
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

    async with httpx.AsyncClient() as client:
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

    async with httpx.AsyncClient() as client:
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

    async with httpx.AsyncClient() as client:
        # Check 1: Ideas without decisions for > 24h
        cutoff_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        response = await client.get(
            f"{rest_url}/ideas"
            f"?created_at=lt.{cutoff_24h}"
            "&select=id,created_at"
            "&limit=100",
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

        if result["is_stale"]:
            activity.logger.warning(
                f"System is STALE! Score: {result['metrics']['staleness_score']:.2f}, "
                f"recommended action: {result['recommended_action']}"
            )
        else:
            activity.logger.info(
                f"System is healthy. Staleness score: {result['metrics']['staleness_score']:.2f}"
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
