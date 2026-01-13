"""
Telegram Delivery Activity

Temporal activity for sending hypotheses to Telegram.
Delivers generated hypotheses to buyers via Telegram Bot API.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional
from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx
from src.core.http_client import get_http_client

# Telegram API base URL
TELEGRAM_API_BASE = "https://api.telegram.org"

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 10.0  # seconds


def _should_retry(status_code: int, error_code: Optional[int] = None) -> bool:
    """Check if request should be retried based on status code."""
    # Retry on rate limit (429) or server errors (5xx)
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False


def _get_retry_delay(attempt: int, retry_after: Optional[int] = None) -> float:
    """Calculate delay before next retry with exponential backoff."""
    if retry_after:
        return float(min(float(retry_after), MAX_DELAY))
    # Exponential backoff: 1s, 2s, 4s, ...
    delay = BASE_DELAY * (2**attempt)
    return float(min(delay, MAX_DELAY))


@activity.defn
async def send_hypothesis_to_telegram(
    hypothesis_id: str,
    hypothesis_content: str,
    chat_id: str,
    idea_id: Optional[str] = None,
) -> dict:
    """
    Send hypothesis text to Telegram chat.

    Args:
        hypothesis_id: Hypothesis UUID
        hypothesis_content: Text content to send
        chat_id: Telegram chat ID (buyer's chat)
        idea_id: Optional idea ID for context

    Returns:
        dict with message_id, status, and timestamp

    Raises:
        ApplicationError: If Telegram API fails
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ApplicationError("TELEGRAM_BOT_TOKEN not configured")

    activity.logger.info(f"Sending hypothesis {hypothesis_id} to chat {chat_id}")

    # Format message
    message_text = _format_hypothesis_message(hypothesis_content, idea_id)
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML",
    }

    last_error: Optional[str] = None

    for attempt in range(MAX_RETRIES):
        try:
            client = get_http_client()
            response = await client.post(url, json=payload, timeout=30.0)

            data = response.json()

            if data.get("ok"):
                result = data.get("result", {})
                message_id = result.get("message_id")
                activity.logger.info(f"Hypothesis sent successfully: message_id={message_id}")
                return {
                    "hypothesis_id": hypothesis_id,
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "status": "delivered",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Check if we should retry
            error_code = data.get("error_code")
            error_desc = data.get("description", "Unknown Telegram error")

            if _should_retry(response.status_code, error_code):
                retry_after = data.get("parameters", {}).get("retry_after")
                delay = _get_retry_delay(attempt, retry_after)
                activity.logger.warning(
                    f"Telegram API failed (attempt {attempt + 1}/{MAX_RETRIES}): "
                    f"status={response.status_code}, error={error_desc}. "
                    f"Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue

            # Non-retryable error
            activity.logger.error(f"Telegram API error (non-retryable): {error_desc}")
            raise ApplicationError(
                f"Telegram API error: {error_desc}",
                type="TELEGRAM_ERROR",
            )

        except httpx.TimeoutException:
            last_error = "Telegram API timeout"
            delay = _get_retry_delay(attempt)
            activity.logger.warning(
                f"Telegram timeout (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"hypothesis={hypothesis_id}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except httpx.HTTPError as e:
            last_error = str(e)
            delay = _get_retry_delay(attempt)
            activity.logger.warning(
                f"Telegram HTTP error (attempt {attempt + 1}/{MAX_RETRIES}): "
                f"hypothesis={hypothesis_id}, error={e}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

    # All retries exhausted
    activity.logger.error(
        f"Telegram send failed after {MAX_RETRIES} attempts: "
        f"hypothesis={hypothesis_id}, last_error={last_error}"
    )
    raise ApplicationError(
        f"Telegram API failed after {MAX_RETRIES} retries: {last_error}",
        type="TELEGRAM_RETRY_EXHAUSTED",
    )


def _format_hypothesis_message(content: str, idea_id: Optional[str] = None) -> str:
    """Format hypothesis content for Telegram message."""
    lines = [
        "<b>Новая гипотеза</b>",
        "",
        content,
    ]

    if idea_id:
        lines.extend(
            [
                "",
                f"<i>Идея: {idea_id[:8]}...</i>",
            ]
        )

    return "\n".join(lines)


@activity.defn
async def get_buyer_chat_id(buyer_id: str) -> Optional[str]:
    """
    Get Telegram chat ID for a buyer.

    Args:
        buyer_id: Buyer UUID

    Returns:
        Telegram chat ID or None if not found
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/buyers?id=eq.{buyer_id}&select=telegram_id",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        return None

    return data[0].get("telegram_id")


@activity.defn
async def update_hypothesis_delivery_status(
    hypothesis_id: str,
    status: str,
    message_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Update hypothesis delivery status in Supabase.

    Args:
        hypothesis_id: Hypothesis UUID
        status: Delivery status (delivered/failed)
        message_id: Telegram message ID if delivered
        error: Error message if failed
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
    }

    update_data = {
        "delivery_status": status,
        "delivered_at": datetime.utcnow().isoformat() if status == "delivered" else None,
    }

    if message_id:
        update_data["telegram_message_id"] = message_id

    if error:
        update_data["delivery_error"] = error

    client = get_http_client()
    await client.patch(
        f"{rest_url}/hypotheses?id=eq.{hypothesis_id}",
        headers=headers,
        json=update_data,
    )

    activity.logger.info(f"Updated hypothesis delivery status: {hypothesis_id} -> {status}")


@activity.defn
async def emit_delivery_event(
    hypothesis_id: str,
    idea_id: str,
    status: str,
    error: Optional[str] = None,
) -> dict:
    """
    Emit delivery event to event log.

    Args:
        hypothesis_id: Hypothesis UUID
        idea_id: Idea UUID
        status: Delivery status
        error: Optional error message

    Returns:
        Created event dict
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    event_type = "HypothesisDelivered" if status == "delivered" else "DeliveryFailed"

    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": "hypothesis",
        "entity_id": hypothesis_id,
        "payload": {
            "hypothesis_id": hypothesis_id,
            "idea_id": idea_id,
            "status": status,
            "error": error,
        },
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
