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


# Maximum retry attempts for failed hypotheses
MAX_HYPOTHESIS_RETRIES = 3

# Minimum hours between retries
RETRY_COOLDOWN_HOURS = 1


@activity.defn
async def retry_failed_hypotheses(max_retries: int = MAX_HYPOTHESIS_RETRIES) -> Dict[str, int]:
    """
    Retry delivery of failed hypotheses.

    Finds hypotheses with status='failed' and retry_count < max_retries,
    attempts to resend via Telegram, and updates status.

    Issue: #313 - Failed hypothesis retry mechanism

    Args:
        max_retries: Maximum retry attempts per hypothesis

    Returns:
        Dict with retry stats (retried, succeeded, failed, skipped)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)
    write_headers = _get_headers(supabase_key, for_write=True)

    stats = {"retried": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    # Get failed hypotheses eligible for retry
    cooldown = datetime.utcnow() - timedelta(hours=RETRY_COOLDOWN_HOURS)
    cooldown_iso = cooldown.isoformat()

    activity.logger.info(f"Looking for failed hypotheses to retry (max_retries={max_retries})")

    async with httpx.AsyncClient() as client:
        # Find failed hypotheses that haven't exceeded retry limit
        # and either never retried or last retry was before cooldown
        response = await client.get(
            f"{rest_url}/hypotheses"
            f"?status=eq.failed"
            f"&retry_count=lt.{max_retries}"
            f"&or=(last_retry_at.is.null,last_retry_at.lt.{cooldown_iso})"
            f"&select=id,idea_id,content,buyer_id,retry_count"
            f"&limit=10",  # Process max 10 per run
            headers=headers,
        )

        if response.status_code != 200:
            activity.logger.warning(f"Error fetching failed hypotheses: {response.text}")
            return stats

        failed_hypotheses = response.json()

        if not failed_hypotheses:
            activity.logger.info("No failed hypotheses eligible for retry")
            return stats

        activity.logger.info(f"Found {len(failed_hypotheses)} hypotheses to retry")

        # Get Telegram bot token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            activity.logger.error("TELEGRAM_BOT_TOKEN not configured, skipping retries")
            stats["skipped"] = len(failed_hypotheses)
            return stats

        for hypothesis in failed_hypotheses:
            hypothesis_id = hypothesis["id"]
            buyer_id = hypothesis.get("buyer_id")
            content = hypothesis.get("content", "")

            if not buyer_id or not content:
                activity.logger.warning(f"Hypothesis {hypothesis_id} missing buyer_id or content")
                stats["skipped"] += 1
                continue

            # Get buyer's chat_id
            buyer_response = await client.get(
                f"{rest_url}/buyers?id=eq.{buyer_id}&select=telegram_id",
                headers=headers,
            )

            if buyer_response.status_code != 200:
                activity.logger.warning(f"Error fetching buyer {buyer_id}")
                stats["skipped"] += 1
                continue

            buyers = buyer_response.json()
            if not buyers or not buyers[0].get("telegram_id"):
                activity.logger.warning(f"Buyer {buyer_id} has no telegram_id")
                stats["skipped"] += 1
                continue

            chat_id = buyers[0]["telegram_id"]
            stats["retried"] += 1

            # Attempt delivery
            try:
                telegram_response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"<b>Hypothesis (Retry)</b>\n\n{content}",
                        "parse_mode": "HTML",
                    },
                    timeout=30.0,
                )

                tg_data = telegram_response.json()

                if tg_data.get("ok"):
                    # Success - update hypothesis
                    await client.patch(
                        f"{rest_url}/hypotheses?id=eq.{hypothesis_id}",
                        headers=write_headers,
                        json={
                            "status": "delivered",
                            "retry_count": hypothesis["retry_count"] + 1,
                            "last_retry_at": datetime.utcnow().isoformat(),
                            "last_error": None,
                        },
                    )
                    stats["succeeded"] += 1
                    activity.logger.info(f"Retry succeeded for hypothesis {hypothesis_id}")
                else:
                    # Telegram error
                    error_msg = tg_data.get("description", "Unknown Telegram error")
                    await client.patch(
                        f"{rest_url}/hypotheses?id=eq.{hypothesis_id}",
                        headers=write_headers,
                        json={
                            "retry_count": hypothesis["retry_count"] + 1,
                            "last_retry_at": datetime.utcnow().isoformat(),
                            "last_error": error_msg,
                        },
                    )
                    stats["failed"] += 1
                    activity.logger.warning(f"Retry failed for {hypothesis_id}: {error_msg}")

            except Exception as e:
                # Network error
                await client.patch(
                    f"{rest_url}/hypotheses?id=eq.{hypothesis_id}",
                    headers=write_headers,
                    json={
                        "retry_count": hypothesis["retry_count"] + 1,
                        "last_retry_at": datetime.utcnow().isoformat(),
                        "last_error": str(e),
                    },
                )
                stats["failed"] += 1
                activity.logger.warning(f"Retry error for {hypothesis_id}: {e}")

    total = stats["succeeded"] + stats["failed"] + stats["skipped"]
    activity.logger.info(
        f"Hypothesis retry complete: {stats['succeeded']} succeeded, "
        f"{stats['failed']} failed, {stats['skipped']} skipped (total: {total})"
    )

    return stats


@activity.defn
async def cleanup_exhausted_hypotheses(retention_days: int = 7) -> int:
    """
    Mark hypotheses that exhausted retries as 'abandoned'.

    These hypotheses failed delivery 3+ times and are past retention.

    Args:
        retention_days: Days after which exhausted hypotheses are marked abandoned

    Returns:
        Number of hypotheses marked as abandoned
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_iso = cutoff.isoformat()

    activity.logger.info(f"Marking exhausted hypotheses older than {cutoff_iso} as abandoned")

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/hypotheses"
            f"?status=eq.failed"
            f"&retry_count=gte.{MAX_HYPOTHESIS_RETRIES}"
            f"&created_at=lt.{cutoff_iso}",
            headers=headers,
            json={"status": "abandoned"},
        )

        if response.status_code not in (200, 204):
            activity.logger.warning(f"Error marking hypotheses abandoned: {response.text}")
            return 0

        count = _extract_delete_count(response)
        if count > 0:
            activity.logger.info(f"Marked {count} exhausted hypotheses as abandoned")
        return count
