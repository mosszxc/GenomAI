"""
Hygiene Cleanup Activities

Temporal activities for periodic data cleanup.
Part of Hygiene Agent system.

Cleanup operations:
- Expired historical_import_queue entries
- Rejected knowledge_extractions
- Orphan raw_metrics_current
- Idle buyer_states
- Old staleness_snapshots
"""

import os
from datetime import datetime, timedelta
from typing import Dict

from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx


SCHEMA = "genomai"


def _get_credentials():
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    return f"{supabase_url}/rest/v1", supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with schema."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation,count=exact"
    return headers


@activity.defn
async def cleanup_expired_import_queue(retention_days: int = 7) -> int:
    """
    Delete expired entries from historical_import_queue.

    Args:
        retention_days: Days to keep expired entries

    Returns:
        Number of records deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Cleaning historical_import_queue older than {cutoff_iso}")

    async with httpx.AsyncClient() as client:
        # Delete expired entries
        response = await client.delete(
            f"{rest_url}/historical_import_queue"
            f"?status=in.(expired,pending_video)"
            f"&created_at=lt.{cutoff_iso}",
            headers=headers,
        )

        if response.status_code == 404:
            activity.logger.info("Table historical_import_queue not found")
            return 0

        if response.status_code not in (200, 204):
            activity.logger.warning(f"Error cleaning import queue: {response.text}")
            return 0

        # Extract count from content-range header
        count = _extract_delete_count(response)
        activity.logger.info(f"Deleted {count} expired import queue entries")
        return count


@activity.defn
async def cleanup_rejected_knowledge(retention_days: int = 30) -> int:
    """
    Delete rejected knowledge_extractions older than retention period.

    Args:
        retention_days: Days to keep rejected extractions

    Returns:
        Number of records deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Cleaning rejected knowledge older than {cutoff_iso}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{rest_url}/knowledge_extractions"
            f"?status=eq.rejected"
            f"&reviewed_at=lt.{cutoff_iso}",
            headers=headers,
        )

        if response.status_code == 404:
            activity.logger.info("Table knowledge_extractions not found")
            return 0

        if response.status_code not in (200, 204):
            activity.logger.warning(f"Error cleaning knowledge: {response.text}")
            return 0

        count = _extract_delete_count(response)
        activity.logger.info(f"Deleted {count} rejected knowledge extractions")
        return count


@activity.defn
async def cleanup_orphan_raw_metrics() -> int:
    """
    Delete raw_metrics_current entries without matching creatives.

    Returns:
        Number of records deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    activity.logger.info("Cleaning orphan raw_metrics_current entries")

    async with httpx.AsyncClient() as client:
        # First, get tracker_ids that exist in creatives
        valid_response = await client.get(
            f"{rest_url}/creatives?select=tracker_id",
            headers=_get_headers(supabase_key),
        )

        if valid_response.status_code != 200:
            activity.logger.warning("Could not fetch valid tracker_ids")
            return 0

        valid_trackers = {r["tracker_id"] for r in valid_response.json() if r.get("tracker_id")}

        # Get all metrics tracker_ids
        metrics_response = await client.get(
            f"{rest_url}/raw_metrics_current?select=tracker_id",
            headers=_get_headers(supabase_key),
        )

        if metrics_response.status_code != 200:
            activity.logger.warning("Could not fetch metrics tracker_ids")
            return 0

        metrics_trackers = {r["tracker_id"] for r in metrics_response.json() if r.get("tracker_id")}

        # Find orphans
        orphan_trackers = metrics_trackers - valid_trackers

        if not orphan_trackers:
            activity.logger.info("No orphan raw_metrics found")
            return 0

        # Delete orphans (batch by 50)
        deleted = 0
        for tracker_id in list(orphan_trackers)[:50]:  # Limit to 50 per run
            del_response = await client.delete(
                f"{rest_url}/raw_metrics_current?tracker_id=eq.{tracker_id}",
                headers=headers,
            )
            if del_response.status_code in (200, 204):
                deleted += 1

        activity.logger.info(f"Deleted {deleted} orphan raw_metrics entries")
        return deleted


@activity.defn
async def cleanup_idle_buyer_states(retention_days: int = 30) -> int:
    """
    Delete buyer_states that have been idle for too long.

    Args:
        retention_days: Days to keep idle states

    Returns:
        Number of records deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Cleaning idle buyer_states older than {cutoff_iso}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{rest_url}/buyer_states"
            f"?state=eq.idle"
            f"&updated_at=lt.{cutoff_iso}",
            headers=headers,
        )

        if response.status_code == 404:
            activity.logger.info("Table buyer_states not found")
            return 0

        if response.status_code not in (200, 204):
            activity.logger.warning(f"Error cleaning buyer_states: {response.text}")
            return 0

        count = _extract_delete_count(response)
        activity.logger.info(f"Deleted {count} idle buyer states")
        return count


@activity.defn
async def archive_staleness_snapshots(retention_days: int = 90) -> int:
    """
    Delete old staleness_snapshots.

    Args:
        retention_days: Days to keep snapshots

    Returns:
        Number of records deleted
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Archiving staleness_snapshots older than {cutoff_iso}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{rest_url}/staleness_snapshots"
            f"?created_at=lt.{cutoff_iso}",
            headers=headers,
        )

        if response.status_code == 404:
            activity.logger.info("Table staleness_snapshots not found")
            return 0

        if response.status_code not in (200, 204):
            activity.logger.warning(f"Error archiving staleness: {response.text}")
            return 0

        count = _extract_delete_count(response)
        activity.logger.info(f"Archived {count} staleness snapshots")
        return count


@activity.defn
async def run_all_cleanup(
    import_queue_days: int = 7,
    knowledge_days: int = 30,
    buyer_states_days: int = 30,
    staleness_days: int = 90,
) -> Dict[str, int]:
    """
    Run all cleanup operations and return stats.

    Returns:
        Dict with counts per cleanup type
    """
    stats = {
        "import_queue": 0,
        "knowledge": 0,
        "raw_metrics": 0,
        "buyer_states": 0,
        "staleness": 0,
    }

    # Run each cleanup (they're idempotent)
    try:
        stats["import_queue"] = await cleanup_expired_import_queue(import_queue_days)
    except Exception as e:
        activity.logger.error(f"import_queue cleanup failed: {e}")

    try:
        stats["knowledge"] = await cleanup_rejected_knowledge(knowledge_days)
    except Exception as e:
        activity.logger.error(f"knowledge cleanup failed: {e}")

    try:
        stats["raw_metrics"] = await cleanup_orphan_raw_metrics()
    except Exception as e:
        activity.logger.error(f"raw_metrics cleanup failed: {e}")

    try:
        stats["buyer_states"] = await cleanup_idle_buyer_states(buyer_states_days)
    except Exception as e:
        activity.logger.error(f"buyer_states cleanup failed: {e}")

    try:
        stats["staleness"] = await archive_staleness_snapshots(staleness_days)
    except Exception as e:
        activity.logger.error(f"staleness cleanup failed: {e}")

    total = sum(stats.values())
    activity.logger.info(f"Cleanup complete: {total} total records cleaned")

    return stats


def _extract_delete_count(response: httpx.Response) -> int:
    """Extract deleted count from response headers or body."""
    # Try content-range header (format: */count or 0-n/count)
    content_range = response.headers.get("content-range", "")
    if "/" in content_range:
        try:
            return int(content_range.split("/")[1])
        except (ValueError, IndexError):
            pass

    # Try response body if it's a list
    try:
        data = response.json()
        if isinstance(data, list):
            return len(data)
    except Exception:
        pass

    return 0
