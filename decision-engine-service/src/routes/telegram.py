"""
Telegram Webhook Router

Notification-only bot. Handles:
    /start → Check pending verification or redirect to Cockpit
    /help → Minimal help message
    All other commands → Silently ignored (200 OK)

Outgoing notifications:
    - Verification codes (via #750)
    - Creative reminders
"""

from __future__ import annotations

import os
import logging
import asyncio
import secrets
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.core.http_client import get_http_client
from temporalio.service import RPCError, RPCStatusCode
import httpx


logger = logging.getLogger(__name__)

# Retry configuration for Telegram API
TELEGRAM_MAX_RETRIES = 3
TELEGRAM_BASE_DELAY = 1.0  # seconds
TELEGRAM_MAX_DELAY = 10.0  # seconds

router = APIRouter()

# Telegram webhook security header
TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def verify_webhook_secret(request: Request) -> None:
    """Verify Telegram webhook secret token.

    Telegram sends secret_token in X-Telegram-Bot-Api-Secret-Token header
    when configured via setWebhook API with secret_token parameter.

    Raises:
        HTTPException: 401 if secret is configured but not provided/invalid
    """
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not webhook_secret:
        # Secret not configured - skip verification (backwards compatible)
        return

    provided_secret = request.headers.get(TELEGRAM_SECRET_HEADER, "")
    if not provided_secret:
        logger.warning("Telegram webhook request missing secret token")
        raise HTTPException(status_code=401, detail="Missing webhook secret")

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(webhook_secret, provided_secret):
        logger.warning("Telegram webhook request with invalid secret token")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


class WebhookErrorStats:
    """Simple in-memory counter for webhook errors."""

    def __init__(self):
        self.total_errors = 0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None
        self.error_types: dict[str, int] = {}

    def record_error(self, error: Exception) -> None:
        """Record a webhook error."""
        self.total_errors += 1
        self.last_error = str(error)
        self.last_error_time = datetime.utcnow()
        error_type = type(error).__name__
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

    def get_stats(self) -> dict:
        """Get error statistics."""
        return {
            "total_errors": self.total_errors,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "error_types": self.error_types,
        }


webhook_error_stats = WebhookErrorStats()


def safe_json_response(
    response: httpx.Response,
    context: str = "API call",
    default: Any = None,
) -> Any:
    """Safely extract JSON from HTTP response with status check."""
    if response.status_code != 200:
        logger.error(f"{context} failed: status={response.status_code}, body={response.text[:200]}")
        return default
    try:
        return response.json()
    except Exception as e:
        logger.error(f"{context} JSON parse error: {e}, body={response.text[:200]}")
        return default


class TelegramMessage(BaseModel):
    """Parsed Telegram message."""

    message_id: int
    chat_id: str
    user_id: str
    username: Optional[str]
    text: Optional[str]


def parse_update(update: dict) -> Optional[TelegramMessage]:
    """Parse Telegram update into structured message."""
    message = update.get("message")
    if not message:
        return None

    chat = message.get("chat", {})
    from_user = message.get("from", {})

    return TelegramMessage(
        message_id=message.get("message_id", 0),
        chat_id=str(chat.get("id", "")),
        user_id=str(from_user.get("id", "")),
        username=from_user.get("username"),
        text=message.get("text"),
    )


async def get_temporal_client():
    """Get Temporal client."""
    from temporal.client import get_temporal_client as get_client

    return await get_client()


def _should_retry(status_code: int, error_code: int | None = None) -> bool:
    """Check if request should be retried based on status code."""
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False


def _get_retry_delay(attempt: int, retry_after: int | None = None) -> float:
    """Calculate delay before next retry with exponential backoff."""
    if retry_after:
        return float(min(float(retry_after), TELEGRAM_MAX_DELAY))
    delay = TELEGRAM_BASE_DELAY * (2**attempt)
    return float(min(delay, TELEGRAM_MAX_DELAY))


async def send_telegram_message(chat_id: str, text: str, reply_markup: dict | None = None) -> bool:
    """
    Send a message to Telegram chat with retry on transient errors.

    Retries on:
    - 429 (rate limit) - respects Retry-After header
    - 5xx (server errors) - exponential backoff

    Max 3 attempts with exponential backoff (1s, 2s, 4s).
    """

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    last_error = None

    for attempt in range(TELEGRAM_MAX_RETRIES):
        try:
            client = get_http_client()
            response = await client.post(url, json=payload, timeout=30.0)

            data = safe_json_response(response, "Telegram sendMessage", {})

            if data.get("ok"):
                return True

            error_code = data.get("error_code")
            if _should_retry(response.status_code, error_code):
                retry_after = data.get("parameters", {}).get("retry_after")
                delay = _get_retry_delay(attempt, retry_after)

                logger.warning(
                    f"Telegram sendMessage failed (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                    f"status={response.status_code}, error={data.get('description')}. "
                    f"Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue

            logger.error(
                f"Telegram sendMessage failed (non-retryable): "
                f"chat_id={chat_id}, error={data.get('description')}"
            )
            return False

        except httpx.TimeoutException as e:
            last_error = str(e)
            delay = _get_retry_delay(attempt)
            logger.warning(
                f"Telegram sendMessage timeout (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                f"chat_id={chat_id}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except httpx.HTTPError as e:
            last_error = str(e)
            delay = _get_retry_delay(attempt)
            logger.warning(
                f"Telegram sendMessage HTTP error (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                f"chat_id={chat_id}, error={e}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except Exception as e:
            logger.error(f"Telegram sendMessage unexpected error: chat_id={chat_id}, error={e}")
            return False

    logger.error(
        f"Telegram sendMessage failed after {TELEGRAM_MAX_RETRIES} attempts: "
        f"chat_id={chat_id}, last_error={last_error}"
    )
    return False


async def check_active_onboarding(telegram_id: str) -> Optional[str]:
    """
    Check if user has active onboarding workflow.

    Returns workflow ID if found, None if not found or workflow was terminated
    due to nondeterminism error (fix #694).
    """
    try:
        client = await get_temporal_client()
        workflow_id = f"onboarding-{telegram_id}"

        try:
            handle = client.get_workflow_handle(workflow_id)
            desc = await handle.describe()
            status = desc.status

            if status.name != "RUNNING":
                return None

            state = await handle.query("get_state")
            if state not in ["COMPLETED", "CANCELLED", "TIMED_OUT"]:
                return workflow_id

        except RPCError as e:
            if e.status == RPCStatusCode.NOT_FOUND:
                pass
            else:
                logger.warning(f"RPC error querying workflow {workflow_id}, terminating: {e}")
                await _terminate_stale_workflow(client, workflow_id, str(e))
        except Exception as e:
            error_msg = str(e)
            if "nondeterminism" in error_msg.lower() or "does not handle" in error_msg.lower():
                logger.warning(
                    f"Nondeterminism detected in workflow {workflow_id}, terminating: {e}"
                )
                await _terminate_stale_workflow(client, workflow_id, error_msg)
            else:
                logger.error(f"Unexpected error querying workflow {workflow_id}: {e}")

        return None
    except Exception as e:
        logger.error(f"Error checking active onboarding: {e}")
        return None


async def _terminate_stale_workflow(client, workflow_id: str, reason: str) -> None:
    """Terminate a stale workflow that has nondeterminism or other unrecoverable errors."""
    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.terminate(reason=f"Auto-terminated: {reason[:200]}")
        logger.info(f"Terminated stale workflow {workflow_id}")
    except RPCError as e:
        if e.status == RPCStatusCode.NOT_FOUND:
            pass
        else:
            logger.error(f"Failed to terminate workflow {workflow_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to terminate workflow {workflow_id}: {e}")


async def handle_start_command(message: TelegramMessage) -> None:
    """Handle /start command - redirect to Cockpit website for onboarding."""
    COCKPIT_ONBOARDING_URL = "https://cockpit.genomai.com/onboarding"

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Начать регистрацию",
                    "url": COCKPIT_ONBOARDING_URL,
                }
            ]
        ]
    }

    await send_telegram_message(
        message.chat_id,
        "Добро пожаловать в GenomAI!\n\n"
        "Для регистрации перейдите на сайт:\n"
        f"{COCKPIT_ONBOARDING_URL}",
        reply_markup=keyboard,
    )

    logger.info(f"Sent onboarding redirect to user: {message.user_id}")


async def handle_help_command(message: TelegramMessage) -> None:
    """Handle /help command - minimal help."""
    help_message = (
        "<b>GenomAI Bot</b>\n\n"
        "/start - Регистрация\n"
        "/help - Справка\n\n"
        "Все остальные функции доступны в Cockpit:\n"
        "https://cockpit.genomai.com"
    )

    await send_telegram_message(message.chat_id, help_message)


async def process_telegram_update(update: dict) -> None:
    """Process incoming Telegram update."""
    try:
        await _process_telegram_update_inner(update)
    except Exception as e:
        logger.exception(f"Failed to process Telegram update {update.get('update_id')}: {e}")
        webhook_error_stats.record_error(e)


async def _process_telegram_update_inner(update: dict) -> None:
    """Inner function for processing Telegram updates.

    Only handles /start and /help commands.
    All other messages are silently ignored (200 OK, no response).
    """
    # Callback queries - silently ignore
    if "callback_query" in update:
        return

    message = parse_update(update)
    if not message:
        return

    logger.info(
        f"Telegram message from {message.user_id}: {repr(message.text)[:100] if message.text else '[media]'}"
    )

    # Handle commands
    if message.text:
        text = message.text.strip()

        if text == "/start" or text.startswith("/start "):
            await handle_start_command(message)
        elif text == "/help":
            await handle_help_command(message)
        # All other commands and messages - silently ignore


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook endpoint.

    Receives updates from Telegram Bot API and processes them asynchronously.
    Verifies X-Telegram-Bot-Api-Secret-Token header if TELEGRAM_WEBHOOK_SECRET is set.
    """
    verify_webhook_secret(request)

    try:
        update = await request.json()
        logger.debug(f"Received Telegram update: {update.get('update_id')}")

        # Process in background to respond quickly
        background_tasks.add_task(process_telegram_update, update)

        return {"ok": True}

    except Exception as e:
        logger.exception(f"Telegram webhook error: {e}")
        webhook_error_stats.record_error(e)
        # Return 200 to prevent Telegram from retrying endlessly
        return {"ok": True, "error": str(e)}


@router.get("/webhook/telegram/status")
async def telegram_webhook_status():
    """Check Telegram webhook configuration status."""

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {
            "status": "not_configured",
            "error": "TELEGRAM_BOT_TOKEN not set",
        }

    try:
        client = get_http_client()
        response = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getWebhookInfo",
            timeout=10.0,
        )
        data = safe_json_response(response, "Telegram getWebhookInfo", {})

        if data.get("ok"):
            result = data.get("result", {})
            return {
                "status": "configured" if result.get("url") else "not_set",
                "url": result.get("url"),
                "pending_update_count": result.get("pending_update_count", 0),
                "last_error_date": result.get("last_error_date"),
                "last_error_message": result.get("last_error_message"),
            }

        return {"status": "error", "error": data.get("description")}

    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/webhook/telegram/errors")
async def telegram_webhook_errors():
    """
    Get webhook error statistics for monitoring.

    Returns:
        - total_errors: Total number of webhook errors since service start
        - last_error: Last error message
        - last_error_time: Timestamp of last error
        - error_types: Breakdown by exception type
    """
    return webhook_error_stats.get_stats()
