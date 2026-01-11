"""
Hygiene Health Activities

Temporal activities for health monitoring and alerting.
Part of Hygiene Agent system.

Health checks:
- Supabase connection
- Temporal connection (implicit - if activity runs, temporal works)
- Table sizes
- Pending counts
- Admin alerts via Telegram
"""

import os
import time
import uuid
from datetime import datetime
from typing import Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx


SCHEMA = "genomai"

# Admin chat ID for alerts (mosszxc)
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "291678304")

# Tables to monitor for sizes
MONITORED_TABLES = [
    "creatives",
    "ideas",
    "decisions",
    "hypotheses",
    "transcripts",
    "decomposed_creatives",
    "outcome_aggregates",
    "event_log",
]

# Tables/columns to check for pending items
PENDING_CHECKS = {
    "historical_import_queue": {
        "column": "status",
        "values": ["pending", "pending_video"],
    },
    "knowledge_extractions": {"column": "status", "values": ["pending"]},
    "creatives": {"column": "status", "values": ["registered"]},
    "hypotheses": {"column": "status", "values": ["generated"]},
}


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
        headers["Prefer"] = "return=representation"
    return headers


@activity.defn
async def check_supabase_connection() -> Dict:
    """
    Check Supabase connection and measure latency.

    Returns:
        Dict with connected status and latency_ms
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{rest_url}/buyers?select=id&limit=1",
                headers=headers,
            )

            latency_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                activity.logger.info(f"Supabase connected, latency: {latency_ms:.0f}ms")
                return {"connected": True, "latency_ms": latency_ms}
            else:
                activity.logger.warning(f"Supabase returned {response.status_code}")
                return {
                    "connected": False,
                    "latency_ms": latency_ms,
                    "error": response.text,
                }

    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        activity.logger.error(f"Supabase connection failed: {e}")
        return {"connected": False, "latency_ms": latency_ms, "error": str(e)}


@activity.defn
async def get_table_sizes() -> Dict[str, int]:
    """
    Get row counts for monitored tables.

    Returns:
        Dict mapping table name to row count
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)
    headers["Prefer"] = "count=exact"

    sizes = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in MONITORED_TABLES:
            try:
                response = await client.head(
                    f"{rest_url}/{table}?select=id",
                    headers=headers,
                )

                # Extract count from content-range header
                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    try:
                        count = int(content_range.split("/")[1])
                        sizes[table] = count
                    except (ValueError, IndexError):
                        sizes[table] = -1
                else:
                    sizes[table] = -1

            except Exception as e:
                activity.logger.warning(f"Could not get size for {table}: {e}")
                sizes[table] = -1

    activity.logger.info(f"Table sizes: {sizes}")
    return sizes


@activity.defn
async def get_pending_counts() -> Dict[str, int]:
    """
    Get counts of pending items in various tables.

    Returns:
        Dict mapping table name to pending count
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)
    headers["Prefer"] = "count=exact"

    counts = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for table, check in PENDING_CHECKS.items():
            try:
                # Build filter for pending values
                values_filter = ",".join(check["values"])
                response = await client.head(
                    f"{rest_url}/{table}?{check['column']}=in.({values_filter})",
                    headers=headers,
                )

                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    try:
                        count = int(content_range.split("/")[1])
                        counts[table] = count
                    except (ValueError, IndexError):
                        counts[table] = 0
                else:
                    counts[table] = 0

            except Exception as e:
                activity.logger.warning(f"Could not get pending for {table}: {e}")
                counts[table] = 0

    activity.logger.info(f"Pending counts: {counts}")
    return counts


@activity.defn
async def send_admin_alert(
    severity: str,
    title: str,
    body: str,
) -> bool:
    """
    Send alert to admin via Telegram.

    Args:
        severity: critical, warning, or info
        title: Alert title
        body: Alert body text

    Returns:
        True if sent successfully
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        activity.logger.warning("TELEGRAM_BOT_TOKEN not configured, skipping alert")
        return False

    chat_id = ADMIN_CHAT_ID
    if not chat_id:
        activity.logger.warning("TELEGRAM_ADMIN_CHAT_ID not configured")
        return False

    # Format message with emoji based on severity
    emoji = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "📊",
    }.get(severity, "📋")

    severity_label = {
        "critical": "CRITICAL",
        "warning": "WARNING",
        "info": "INFO",
    }.get(severity, severity.upper())

    message = f"{emoji} <b>{severity_label}: {title}</b>\n\n{body}\n\n<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"

    activity.logger.info(f"Sending {severity} alert to admin: {title}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )

            data = response.json()

            if data.get("ok"):
                activity.logger.info(
                    f"Alert sent: message_id={data['result']['message_id']}"
                )
                return True
            else:
                activity.logger.error(f"Telegram error: {data.get('description')}")
                return False

        except Exception as e:
            activity.logger.error(f"Failed to send alert: {e}")
            return False


@activity.defn
async def save_hygiene_report(report: Dict) -> str:
    """
    Save hygiene report to database.

    Args:
        report: Report data dict

    Returns:
        Report ID
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    report_id = str(uuid.uuid4())
    report["id"] = report_id
    report["created_at"] = datetime.utcnow().isoformat()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{rest_url}/hygiene_reports",
            headers=headers,
            json=report,
        )

        if response.status_code not in (200, 201):
            activity.logger.error(f"Failed to save report: {response.text}")
            raise ApplicationError(f"Failed to save hygiene report: {response.text}")

        activity.logger.info(f"Saved hygiene report: {report_id}")
        return report_id


# ─────────────────────────────────────────────────────────────────────────────
# Alert Formatters
# ─────────────────────────────────────────────────────────────────────────────


def format_health_alert(
    health_score: float,
    supabase_ok: bool,
    temporal_ok: bool,
    issues: List[str],
) -> str:
    """Format health check alert body."""
    lines = []

    # Connection status
    sb_status = "✅" if supabase_ok else "❌"
    tp_status = "✅" if temporal_ok else "❌"
    lines.append(f"Supabase: {sb_status}")
    lines.append(f"Temporal: {tp_status}")
    lines.append(f"Health Score: {health_score:.2f}")

    if issues:
        lines.append("")
        lines.append("<b>Issues:</b>")
        for issue in issues[:5]:  # Limit to 5
            lines.append(f"• {issue}")

    return "\n".join(lines)


def format_cleanup_alert(cleanup_stats: Dict[str, int]) -> str:
    """Format cleanup stats for alert."""
    lines = ["<b>Cleanup Stats:</b>"]

    total = 0
    for table, count in cleanup_stats.items():
        if count > 0:
            lines.append(f"• {table}: {count} deleted")
            total += count

    if total == 0:
        lines.append("• No records to clean")

    lines.append(f"\n<b>Total:</b> {total} records")
    return "\n".join(lines)


def format_integrity_alert(issues: List[Dict]) -> str:
    """Format integrity issues for alert."""
    if not issues:
        return "No integrity issues found ✅"

    lines = ["<b>Integrity Issues:</b>"]

    for issue in issues[:10]:  # Limit to 10
        severity_emoji = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }.get(issue.get("severity", "info"), "⚪")

        lines.append(
            f"{severity_emoji} {issue.get('table')}: "
            f"{issue.get('count')} {issue.get('issue_type')}"
        )

    return "\n".join(lines)
