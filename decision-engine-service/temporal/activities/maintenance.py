"""
Maintenance Activities

Temporal activities for periodic maintenance tasks.
Replaces n8n workflow H1uuOanSy627H4kg (Pipeline Health Monitor).
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import List

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
        "Content-Type": "application/json"
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
        # Find stale buyer_states (not buyers, but buyer_states table if exists)
        # For GenomAI, buyer state is stored in a separate table or as buyer.status

        # First, check if buyer_states table exists
        response = await client.get(
            f"{rest_url}/buyer_states"
            f"?updated_at=lt.{cutoff_iso}"
            "&select=id,buyer_id,state",
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

        # Delete stale states
        state_ids = [s["id"] for s in stale_states]
        for state_id in state_ids:
            await client.delete(
                f"{rest_url}/buyer_states?id=eq.{state_id}",
                headers=headers,
            )

        activity.logger.info(f"Reset {len(state_ids)} stale buyer states")
        return len(state_ids)


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
            f"{rest_url}/recommendations"
            f"?id=in.({','.join(rec_ids)})",
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
        cutoff_1h = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        response = await client.get(
            f"{rest_url}/hypotheses"
            f"?delivery_status=is.null"
            f"&created_at=lt.{cutoff_1h}"
            "&select=id"
            "&limit=100",
            headers=headers,
        )

        if response.status_code == 200:
            undelivered = response.json()
            if undelivered:
                issues.append(f"{len(undelivered)} hypotheses pending delivery for > 1h")

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
) -> dict:
    """
    Emit maintenance completed event.

    Args:
        buyers_reset: Number of buyer states reset
        recommendations_expired: Number of recommendations expired
        issues_count: Number of integrity issues found

    Returns:
        Created event dict
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    event = {
        "id": str(uuid.uuid4()),
        "event_type": "MaintenanceCompleted",
        "entity_type": "system",
        "payload": {
            "buyers_reset": buyers_reset,
            "recommendations_expired": recommendations_expired,
            "integrity_issues": issues_count,
        },
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
