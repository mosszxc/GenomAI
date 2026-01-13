"""
Telegram Webhook Router

Handles incoming Telegram messages and routes them to appropriate workflows.

Routes:
    /start → Start BuyerOnboardingWorkflow
    /stats → Direct stats response
    /help → Help message
    Video/URL → CreativeRegistrationWorkflow or signal to active onboarding
"""

from __future__ import annotations

import os
import re
import logging
import asyncio
import uuid
from datetime import datetime
from html import escape as html_escape
from typing import Any, Optional
import secrets
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.utils.parsing import safe_float
from temporal.models.buyer import VALID_GEOS
from src.core.http_client import get_http_client
from src.core.supabase import get_supabase
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


# Webhook error tracking for monitoring
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


# Callback data validation constants
CALLBACK_DATA_MAX_LENGTH = 64  # Telegram limit
CALLBACK_DATA_PATTERN = re.compile(r"^[a-z_]+_[a-zA-Z0-9\-]+$")

# Input length validation constants
MAX_FEEDBACK_LENGTH = 500  # Max chars for /feedback text


class CallbackDataError(ValueError):
    """Raised when callback_data validation fails."""

    pass


def parse_callback_data(data: str) -> tuple[str, str]:
    """Parse and validate callback_data from Telegram inline button.

    Expected formats:
    - ke_approve_{uuid}
    - ke_reject_{uuid}
    - ke_skip_{uuid}
    - chat_{telegram_id}

    Args:
        data: Raw callback_data string from Telegram

    Returns:
        Tuple of (action, id) where action is the prefix and id is the identifier

    Raises:
        CallbackDataError: If validation fails
    """
    if not data:
        raise CallbackDataError("Empty callback data")

    if len(data) > CALLBACK_DATA_MAX_LENGTH:
        raise CallbackDataError(f"Callback data exceeds {CALLBACK_DATA_MAX_LENGTH} chars")

    if not CALLBACK_DATA_PATTERN.match(data):
        raise CallbackDataError("Invalid callback data format")

    # Split on last underscore to get action and id
    last_underscore = data.rfind("_")
    if last_underscore == -1:
        raise CallbackDataError("Invalid callback format: missing underscore")

    action = data[:last_underscore]
    identifier = data[last_underscore + 1 :]

    if not action or not identifier:
        raise CallbackDataError("Empty action or identifier")

    # Strict type validation based on action
    if action in ("ke_approve", "ke_reject", "ke_skip"):
        try:
            uuid.UUID(identifier)
        except ValueError:
            raise CallbackDataError(
                f"Invalid UUID format for {action}: {identifier[:20]}"
            ) from None
    elif action == "chat":
        if not identifier.isdigit():
            raise CallbackDataError(f"Invalid telegram_id format: {identifier[:20]}")

    return action, identifier


class TelegramUpdate(BaseModel):
    """Telegram webhook update model."""

    update_id: int
    message: Optional[dict] = None


class TelegramMessage(BaseModel):
    """Parsed Telegram message."""

    message_id: int
    chat_id: str
    user_id: str
    username: Optional[str]
    text: Optional[str]
    video: Optional[dict] = None
    document: Optional[dict] = None


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
        video=message.get("video"),
        document=message.get("document"),
    )


async def get_temporal_client():
    """Get Temporal client."""
    from temporal.client import get_temporal_client as get_client

    return await get_client()


def _should_retry(status_code: int, error_code: int | None = None) -> bool:
    """Check if request should be retried based on status code."""
    # Retry on rate limit (429) or server errors (5xx)
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False


def _get_retry_delay(attempt: int, retry_after: int | None = None) -> float:
    """Calculate delay before next retry with exponential backoff."""
    if retry_after:
        return float(min(float(retry_after), TELEGRAM_MAX_DELAY))
    # Exponential backoff: 1s, 2s, 4s, ...
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

            data = response.json()

            if data.get("ok"):
                return True

            # Check if we should retry
            error_code = data.get("error_code")
            if _should_retry(response.status_code, error_code):
                # Get retry delay (respect Retry-After for 429)
                retry_after = data.get("parameters", {}).get("retry_after")
                delay = _get_retry_delay(attempt, retry_after)

                logger.warning(
                    f"Telegram sendMessage failed (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                    f"status={response.status_code}, error={data.get('description')}. "
                    f"Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue

            # Non-retryable error
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
            # Unexpected error - don't retry
            logger.error(f"Telegram sendMessage unexpected error: chat_id={chat_id}, error={e}")
            return False

    # All retries exhausted
    logger.error(
        f"Telegram sendMessage failed after {TELEGRAM_MAX_RETRIES} attempts: "
        f"chat_id={chat_id}, last_error={last_error}"
    )
    return False


async def send_telegram_photo(chat_id: str, photo_url: str, caption: str = "") -> bool:
    """
    Send a photo to Telegram chat by URL with retry on transient errors.

    Retries on:
    - 429 (rate limit) - respects Retry-After header
    - 5xx (server errors) - exponential backoff

    Max 3 attempts with exponential backoff (1s, 2s, 4s).
    """

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    last_error = None

    for attempt in range(TELEGRAM_MAX_RETRIES):
        try:
            client = get_http_client()
            response = await client.post(url, json=payload, timeout=30.0)

            data = response.json()

            if data.get("ok"):
                return True

            # Check if we should retry
            error_code = data.get("error_code")
            if _should_retry(response.status_code, error_code):
                # Get retry delay (respect Retry-After for 429)
                retry_after = data.get("parameters", {}).get("retry_after")
                delay = _get_retry_delay(attempt, retry_after)

                logger.warning(
                    f"Telegram sendPhoto failed (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                    f"status={response.status_code}, error={data.get('description')}. "
                    f"Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue

            # Non-retryable error
            logger.error(
                f"Telegram sendPhoto failed (non-retryable): "
                f"chat_id={chat_id}, error={data.get('description')}"
            )
            return False

        except httpx.TimeoutException as e:
            last_error = str(e)
            delay = _get_retry_delay(attempt)
            logger.warning(
                f"Telegram sendPhoto timeout (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                f"chat_id={chat_id}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except httpx.HTTPError as e:
            last_error = str(e)
            delay = _get_retry_delay(attempt)
            logger.warning(
                f"Telegram sendPhoto HTTP error (attempt {attempt + 1}/{TELEGRAM_MAX_RETRIES}): "
                f"chat_id={chat_id}, error={e}. Retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except Exception as e:
            # Unexpected error - don't retry
            logger.error(f"Telegram sendPhoto unexpected error: chat_id={chat_id}, error={e}")
            return False

    # All retries exhausted
    logger.error(
        f"Telegram sendPhoto failed after {TELEGRAM_MAX_RETRIES} attempts: "
        f"chat_id={chat_id}, last_error={last_error}"
    )
    return False


async def check_active_onboarding(telegram_id: str) -> Optional[str]:
    """
    Check if user has active onboarding workflow.

    Returns workflow ID if found.
    """
    try:
        client = await get_temporal_client()

        # Try to query the workflow
        workflow_id = f"onboarding-{telegram_id}"

        try:
            handle = client.get_workflow_handle(workflow_id)
            state = await handle.query("get_state")

            # If state is not completed/cancelled/timed_out, workflow is active
            if state not in ["COMPLETED", "CANCELLED", "TIMED_OUT"]:
                return workflow_id
        except RPCError as e:
            if e.status == RPCStatusCode.NOT_FOUND:
                # Expected - workflow doesn't exist or completed
                pass
            else:
                # Unexpected RPC error - log but assume workflow inactive to avoid deadlock
                logger.warning(f"RPC error querying workflow {workflow_id}: {e}")
        except Exception as e:
            # Unexpected error - log but assume workflow inactive to avoid deadlock
            logger.error(f"Unexpected error querying workflow {workflow_id}: {e}")

        return None
    except Exception as e:
        logger.error(f"Error checking active onboarding: {e}")
        return None


# Maximum input length for regex operations (ReDoS protection)
MAX_INPUT_LENGTH = 2048


def extract_video_url(text: str) -> Optional[str]:
    """
    Extract video URL from text.

    Includes input length limit to prevent ReDoS attacks.
    """
    if not text:
        return None

    # ReDoS protection: limit input length
    safe_text = text[:MAX_INPUT_LENGTH]

    # Common video URL patterns
    patterns = [
        r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+",
        r"https?://(?:www\.)?vimeo\.com/\S+",
        r"https?://\S+\.mp4",
        r"https?://\S+\.mov",
        r"https?://\S+\.webm",
        r"https?://\S+/video\S*",
    ]

    for pattern in patterns:
        match = re.search(pattern, safe_text, re.IGNORECASE)
        if match:
            return match.group(0)

    # Check if entire text is a URL
    if safe_text.startswith("http://") or safe_text.startswith("https://"):
        return safe_text.strip()

    return None


async def handle_start_command(message: TelegramMessage) -> None:
    """Handle /start command - start onboarding workflow."""
    from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow
    from temporal.models.buyer import BuyerOnboardingInput
    from temporalio.common import WorkflowIDReusePolicy, WorkflowIDConflictPolicy
    from temporalio.exceptions import WorkflowAlreadyStartedError

    try:
        client = await get_temporal_client()

        # Start new onboarding workflow
        # Uses ALLOW_DUPLICATE to restart after timeout/completion
        # Uses FAIL conflict policy to detect if workflow is already running
        workflow_id = f"onboarding-{message.user_id}"

        await client.start_workflow(
            BuyerOnboardingWorkflow.run,
            BuyerOnboardingInput(
                telegram_id=message.user_id,
                telegram_username=message.username,
                chat_id=message.chat_id,
            ),
            id=workflow_id,
            task_queue="telegram",
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
        )

        logger.info(f"Started onboarding workflow: {workflow_id}")

    except WorkflowAlreadyStartedError:
        # Workflow is already running (not completed/cancelled/timed_out)
        logger.info(f"Workflow already running for user: {message.user_id}")
        await send_telegram_message(
            message.chat_id,
            "У вас уже есть активная регистрация.\nЗавершите её или дождитесь таймаута.",
        )

    except Exception as e:
        logger.error(f"Failed to start onboarding: {e}")
        await send_telegram_message(
            message.chat_id,
            "Не удалось начать регистрацию. Попробуйте позже.",
        )


async def log_buyer_interaction(
    telegram_id: str,
    direction: str,
    message_type: str,
    content: str,
    context: Optional[dict] = None,
    buyer_id: Optional[str] = None,
) -> None:
    """Log interaction to buyer_interactions table.

    Args:
        telegram_id: Telegram ID of the message sender/receiver
        direction: 'in' for incoming, 'out' for outgoing
        message_type: Type of message (command, text, system, etc.)
        content: Message content
        context: Optional context dict
        buyer_id: Optional buyer UUID to associate system messages with a buyer
    """
    try:
        sb = get_supabase()
    except RuntimeError:
        return

    headers = sb.get_headers(for_write=True)
    headers["Prefer"] = "return=minimal"

    payload = {
        "telegram_id": telegram_id,
        "direction": direction,
        "message_type": message_type,
        "content": content,
        "context": context,
    }
    if buyer_id:
        payload["buyer_id"] = buyer_id

    try:
        client = get_http_client()
        await client.post(
            f"{sb.rest_url}/buyer_interactions",
            headers=headers,
            json=payload,
            timeout=10.0,
        )
    except Exception as e:
        logger.error(f"Failed to log buyer interaction: {e}")


async def handle_stats_command(message: TelegramMessage) -> None:
    """Handle /stats command - show user stats."""

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content="/stats",
    )

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Статистика временно недоступна.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get buyer
        buyer_resp = await client.get(
            f"{sb.rest_url}/buyers?telegram_id=eq.{message.user_id}&select=id,name,geos,verticals",
            headers=headers,
        )
        buyers = buyer_resp.json()

        if not buyers:
            await send_telegram_message(
                message.chat_id,
                "Вы ещё не зарегистрированы. Отправьте /start для начала.",
            )
            return

        buyer = buyers[0]
        buyer_id = buyer["id"]

        # Get creatives with test results and tracker_ids
        creatives_resp = await client.get(
            f"{sb.rest_url}/creatives"
            f"?buyer_id=eq.{buyer_id}"
            f"&select=id,status,test_result,tracking_status,tracker_id",
            headers=headers,
        )
        creatives = creatives_resp.json()

        total = len(creatives)
        wins = len([c for c in creatives if c.get("test_result") == "win"])
        losses = len([c for c in creatives if c.get("test_result") == "loss"])
        testing = len([c for c in creatives if c.get("tracking_status") == "tracking"])

        # Calculate win rate
        concluded = wins + losses
        win_rate = (wins / concluded * 100) if concluded > 0 else 0

        # Get spend/revenue from metrics
        tracker_ids = [c.get("tracker_id") for c in creatives if c.get("tracker_id")]
        total_spend = 0.0
        total_revenue = 0.0

        if tracker_ids:
            # Fetch metrics for all tracker_ids
            tracker_list = ",".join(tracker_ids)
            metrics_resp = await client.get(
                f"{sb.rest_url}/raw_metrics_current?tracker_id=in.({tracker_list})&select=metrics",
                headers=headers,
            )
            metrics_rows = metrics_resp.json()

            if isinstance(metrics_rows, list):
                for row in metrics_rows:
                    metrics = row.get("metrics") or {}
                    total_spend += safe_float(metrics.get("spend", 0))
                    total_revenue += safe_float(metrics.get("revenue", 0))

        # Calculate ROI
        roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
        roi_sign = "+" if roi >= 0 else ""

        stats_message = (
            f"📊 <b>Твоя статистика:</b>\n\n"
            f"Креативов: {total}\n"
            f"✅ Побед: {wins} ({win_rate:.0f}%)\n"
            f"❌ Поражений: {losses}\n"
            f"⏳ Тестируется: {testing}\n\n"
            f"ROI: {roi_sign}{roi:.1f}%\n"
            f"Расход: ${total_spend:.0f}\n"
            f"Доход: ${total_revenue:.0f}"
        )

        await send_telegram_message(message.chat_id, stats_message)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=stats_message,
            context={
                "total": total,
                "wins": wins,
                "losses": losses,
                "testing": testing,
                "spend": total_spend,
                "revenue": total_revenue,
                "roi": roi,
            },
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить статистику.")


async def handle_help_command(message: TelegramMessage) -> None:
    """Handle /help command - different output for admin vs buyer."""
    if is_admin(message.user_id):
        help_message = (
            "<b>ADMIN PANEL</b>\n\n"
            "📊 <b>АНАЛИТИКА</b>\n"
            "/genome - Матрица компонентов\n"
            "/confidence - Доверительные интервалы\n"
            "/correlations - Синергии компонентов\n"
            "/trends - Графики трендов\n"
            "/drift - Обнаружение дрифта\n\n"
            "🤖 <b>ИНСТРУМЕНТЫ</b>\n"
            "/simulate X + Y + Z - What-If симулятор\n"
            "/recommend - Лучшая комбинация дня\n"
            "/knowledge - Извлечение знаний\n\n"
            "👥 <b>МОНИТОРИНГ</b>\n"
            "/buyers - Список баеров\n"
            "/activity - Последние действия\n"
            "/decisions - Решения Decision Engine\n"
            "/creatives - Все креативы\n\n"
            "⚙️ <b>СИСТЕМА</b>\n"
            "/status - Статус workflows\n"
            "/errors - Последние ошибки\n\n"
            "📋 <b>MODULAR REVIEW</b>\n"
            "/pending - Гипотезы на ревью\n"
            "/approve &lt;id&gt; - Одобрить\n"
            "/reject &lt;id&gt; - Отклонить"
        )
    else:
        help_message = (
            "<b>Команды GenomAI</b>\n\n"
            "/start - Начать регистрацию\n"
            "/stats - Посмотреть статистику\n"
            "/feedback - Оставить отзыв\n"
            "/help - Показать справку\n\n"
            "<b>Регистрация креатива:</b>\n"
            "Просто отправьте ссылку на видео.\n\n"
            "<i>Example: https://example.com/video.mp4</i>"
        )

    await send_telegram_message(message.chat_id, help_message)


async def handle_genome_command(message: TelegramMessage) -> None:
    """
    Handle /genome command - show component performance heatmap or segmented analysis.

    Usage:
        /genome - Show emotion_primary heatmap (default)
        /genome angle_type - Show specific component type heatmap
        /genome fear --by geo - Segment analysis by geography
        /genome hope --by avatar - Segment analysis by avatar
        /genome curiosity --by week - Segment analysis by week
    """
    from src.services.genome_heatmap import (
        get_heatmap_data,
        format_heatmap_telegram,
        get_available_component_types,
        get_segmented_analysis,
        format_segmented_telegram,
    )

    # Parse command arguments
    text = message.text or ""
    parts = text.split()

    # Check for --by flag
    segment_by = None
    component_value = None
    component_type = "emotion_primary"

    if "--by" in parts:
        by_index = parts.index("--by")
        if by_index + 1 >= len(parts):
            await send_telegram_message(
                message.chat_id,
                "Укажите тип сегментации после --by.\n\n"
                "Usage: /genome fear --by <geo|avatar|week>\n\n"
                "Примеры:\n"
                "  /genome fear --by geo\n"
                "  /genome hope --by avatar\n"
                "  /genome curiosity --by week",
            )
            return
        segment_by = parts[by_index + 1].lower()
        # Everything before --by is the component value
        if by_index > 1:
            component_value = parts[1]

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    try:
        # Segmented analysis mode
        if segment_by:
            valid_segments = ["geo", "avatar", "week"]
            if segment_by not in valid_segments:
                await send_telegram_message(
                    message.chat_id,
                    f"Неверный тип сегментации: <code>{segment_by}</code>\n\n"
                    f"Доступные: <code>geo</code>, <code>avatar</code>, <code>week</code>\n\n"
                    f"Пример: /genome fear --by geo",
                )
                return

            if not component_value:
                await send_telegram_message(
                    message.chat_id,
                    "Укажите значение компонента.\n\n"
                    "Пример: /genome fear --by geo\n"
                    "       /genome hope --by avatar\n"
                    "       /genome curiosity --by week",
                )
                return

            # Get segmented analysis
            data = await get_segmented_analysis(
                component_value=component_value,
                segment_by=segment_by,
                component_type=component_type,
            )
            result_text = format_segmented_telegram(data)

            await send_telegram_message(message.chat_id, result_text)

            # Log outgoing response
            await log_buyer_interaction(
                telegram_id=message.user_id,
                direction="out",
                message_type="system",
                content=result_text,
                context={
                    "component_value": component_value,
                    "segment_by": segment_by,
                },
            )
            return

        # Heatmap mode (default)
        component_type = parts[1] if len(parts) > 1 else "emotion_primary"

        # Get available types for validation
        available_types = await get_available_component_types()

        if component_type not in available_types and available_types:
            # Show available types
            types_list = ", ".join(available_types[:10])
            await send_telegram_message(
                message.chat_id,
                f"Неизвестный тип компонента: <code>{component_type}</code>\n\n"
                f"Доступные типы:\n<code>{types_list}</code>\n\n"
                f"Usage:\n"
                f"  /genome [component_type] - heatmap\n"
                f"  /genome fear --by geo - segment analysis",
            )
            return

        # Get and format heatmap
        data = await get_heatmap_data(component_type=component_type)
        heatmap_text = format_heatmap_telegram(data)

        await send_telegram_message(message.chat_id, heatmap_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=heatmap_text,
            context={"component_type": component_type},
        )

    except Exception as e:
        logger.error(f"Failed to generate genome heatmap: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось сгенерировать матрицу: {str(e)[:100]}",
        )


async def handle_confidence_command(message: TelegramMessage) -> None:
    """
    Handle /confidence command - show win rate confidence intervals.

    Usage:
        /confidence - Show all components with CI
        /confidence emotion_primary - Show specific component type
    """
    from src.services.confidence import (
        get_component_confidence_data,
        format_confidence_telegram,
        get_available_component_types,
    )

    # Parse component type from command
    text = message.text or ""
    parts = text.split()
    component_type = parts[1] if len(parts) > 1 else None

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    try:
        # Validate component type if specified
        if component_type:
            available_types = await get_available_component_types()
            if component_type not in available_types and available_types:
                types_list = ", ".join(available_types[:10])
                await send_telegram_message(
                    message.chat_id,
                    f"Неизвестный тип компонента: <code>{component_type}</code>\n\n"
                    f"Доступные типы:\n<code>{types_list}</code>\n\n"
                    f"Usage: /confidence [component_type]",
                )
                return

        # Get and format confidence data
        data = await get_component_confidence_data(component_type=component_type)
        confidence_text = format_confidence_telegram(data)

        await send_telegram_message(message.chat_id, confidence_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=confidence_text,
            context={"component_type": component_type},
        )

    except Exception as e:
        logger.error(f"Не удалось рассчитать доверительные интервалы: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось рассчитать доверительные интервалы: {str(e)[:100]}",
        )


async def handle_trends_command(message: TelegramMessage) -> None:
    """Handle /trends command - show win rate trends chart."""
    from src.services.charts import generate_win_rate_chart_url

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        # Generate emotion win rate chart
        # Note: charts.py still uses old signature
        chart_url = await generate_win_rate_chart_url(
            supabase_url=sb.base_url,
            supabase_key=sb.service_key,
            chart_type="emotions",
            days=7,
        )

        if not chart_url:
            await send_telegram_message(
                message.chat_id,
                "Данных пока нет.\nТренды появятся после тестирования креативов.",
            )
            return

        # Send chart as photo
        caption = (
            "<b>Тренды конверсии (7 дней)</b>\n\n"
            "Показывает динамику эмоций.\n"
            "Выше = лучше конверсия."
        )

        success = await send_telegram_photo(message.chat_id, chart_url, caption)

        if not success:
            # Fallback to text if photo fails
            await send_telegram_message(
                message.chat_id,
                f"График создан, но не удалось отправить картинку.\nСсылка: {chart_url[:100]}...",
            )

    except Exception as e:
        logger.error(f"Failed to generate trends chart: {e}")
        await send_telegram_message(message.chat_id, "Не удалось создать график.")


async def handle_simulate_command(message: TelegramMessage) -> None:
    """
    Handle /simulate command - predict win rate for component combinations.

    Usage:
        /simulate fear + question + ugc
        /simulate hope, curiosity, testimonial
        /simulate fear question ugc --geo US
    """
    from src.services.what_if_simulator import (
        parse_components,
        simulate_combination,
        format_simulation_telegram,
    )

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    # Parse command
    text = message.text or ""

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    # Check for --geo flag
    geo = None
    if "--geo" in text:
        parts = text.split("--geo")
        text = parts[0]
        if len(parts) > 1:
            geo_part = parts[1].strip().split()[0] if parts[1].strip() else None
            geo = geo_part.upper() if geo_part else None

    # Validate geo against allowed values
    if geo and geo not in VALID_GEOS:
        sample_geos = ", ".join(VALID_GEOS[:10])
        await send_telegram_message(
            message.chat_id,
            f"❌ Неизвестный geo-код: <code>{geo}</code>\n\n"
            f"Доступные geo: {sample_geos}...\n\n"
            "Пример: <code>/simulate fear --geo US</code>",
        )
        return

    # Parse components
    components = parse_components(text)

    if not components:
        await send_telegram_message(
            message.chat_id,
            "🧪 <b>What-If Симулятор</b>\n\n"
            "Предсказание конверсии для комбинаций компонентов.\n\n"
            "<b>Использование:</b>\n"
            "<code>/simulate fear + question + ugc</code>\n"
            "<code>/simulate hope curiosity testimonial</code>\n"
            "<code>/simulate fear question --geo US</code>\n\n"
            "Компоненты разделяются +, запятой или пробелом.",
        )
        return

    try:
        # Run simulation
        result = await simulate_combination(components, geo)
        response_text = format_simulation_telegram(result)

        await send_telegram_message(message.chat_id, response_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=response_text,
            context={
                "components": components,
                "geo": geo,
                "predicted_win_rate": result.get("predicted_win_rate"),
                "confidence_level": result.get("confidence_level"),
            },
        )

    except Exception as e:
        logger.error(f"Не удалось запустить симуляцию: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось запустить симуляцию: {str(e)[:100]}",
        )


async def handle_drift_command(message: TelegramMessage) -> None:
    """
    Handle /drift command - detect performance drift in components.

    Usage:
        /drift - Show all components with drift (medium+ severity)
        /drift emotion_primary - Filter by component type
    """
    from src.services.drift_detection import (
        detect_drift,
        format_drift_telegram,
        get_available_component_types,
    )

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    # Parse component type from command
    text = message.text or ""
    parts = text.split()
    component_type = parts[1] if len(parts) > 1 else None

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    try:
        # Validate component type if specified
        if component_type:
            available_types = await get_available_component_types()
            if component_type not in available_types and available_types:
                types_list = ", ".join(available_types[:10])
                await send_telegram_message(
                    message.chat_id,
                    f"Неизвестный тип компонента: <code>{component_type}</code>\n\n"
                    f"Доступные типы:\n<code>{types_list}</code>\n\n"
                    f"Usage: /drift [component_type]",
                )
                return

        # Detect drift
        results = await detect_drift(
            component_type=component_type,
            min_severity="medium",
        )

        drift_text = format_drift_telegram(results)
        await send_telegram_message(message.chat_id, drift_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=drift_text,
            context={
                "component_type": component_type,
                "drift_count": len(results),
            },
        )

    except Exception as e:
        logger.error(f"Не удалось обнаружить дрифт: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось обнаружить дрифт: {str(e)[:100]}",
        )


async def handle_correlations_command(message: TelegramMessage) -> None:
    """
    Handle /correlations command - discover component synergies and conflicts.

    Usage:
        /correlations - Show discovered correlations
    """
    from src.services.correlation_discovery import (
        discover_correlations,
        format_correlations_telegram,
    )

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=message.text or "/correlations",
    )

    try:
        # Discover correlations
        correlations = await discover_correlations(limit=20)

        # Format for Telegram
        result_text = format_correlations_telegram(correlations)

        await send_telegram_message(message.chat_id, result_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=result_text,
            context={
                "correlation_count": len(correlations),
                "positive": len([c for c in correlations if c.correlation_type == "positive"]),
                "negative": len([c for c in correlations if c.correlation_type == "negative"]),
            },
        )

    except Exception as e:
        logger.error(f"Не удалось найти корреляции: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось найти корреляции: {str(e)[:100]}",
        )


async def handle_recommend_command(message: TelegramMessage) -> None:
    """
    Handle /recommend command - show today's best component combination.

    Usage:
        /recommend - Show best bet recommendation

    Shows optimal component combination based on:
    - Current win rates from learnings
    - Discovered correlations (synergies/conflicts)
    - Component freshness (fatigue proxy)
    """
    from src.services.auto_recommend import (
        generate_best_bet,
        format_best_bet_telegram,
    )

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=message.text or "/recommend",
    )

    try:
        # Generate best bet recommendation
        recommendation = await generate_best_bet()

        # Format for Telegram
        result_text = format_best_bet_telegram(recommendation)

        await send_telegram_message(message.chat_id, result_text)

        # Log outgoing response
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="out",
            message_type="system",
            content=result_text,
            context={
                "component_count": len(recommendation.components),
                "expected_win_rate": recommendation.expected_win_rate,
                "confidence": recommendation.overall_confidence,
                "synergies_count": len(recommendation.synergies_applied),
                "conflicts_avoided": len(recommendation.conflicts_avoided),
            },
        )

    except Exception as e:
        logger.error(f"Не удалось сгенерировать рекомендацию: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось сгенерировать рекомендацию: {str(e)[:100]}",
        )


# =============================================================================
# ADMIN MONITORING COMMANDS
# =============================================================================


async def handle_buyers_command(message: TelegramMessage) -> None:
    """Handle /buyers command - list all buyers with stats."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get all buyers
        buyers_resp = await client.get(
            f"{sb.rest_url}/buyers"
            f"?select=id,telegram_id,name,telegram_username,geos,verticals,status,created_at"
            f"&order=created_at.desc&limit=10",
            headers=headers,
        )
        buyers = buyers_resp.json()

        if not buyers:
            await send_telegram_message(message.chat_id, "Баеров пока нет.")
            return

        # Get creative counts for each buyer
        buyer_ids = [b["id"] for b in buyers]
        creatives_resp = await client.get(
            f"{sb.rest_url}/creatives"
            f"?buyer_id=in.({','.join(buyer_ids)})"
            f"&select=buyer_id,test_result",
            headers=headers,
        )
        creatives = creatives_resp.json()

        # Aggregate stats per buyer
        buyer_stats = {}
        for c in creatives:
            bid = c["buyer_id"]
            if bid not in buyer_stats:
                buyer_stats[bid] = {"total": 0, "wins": 0, "losses": 0}
            buyer_stats[bid]["total"] += 1
            if c.get("test_result") == "win":
                buyer_stats[bid]["wins"] += 1
            elif c.get("test_result") == "loss":
                buyer_stats[bid]["losses"] += 1

        # Format response
        lines = [f"👥 <b>Баеры ({len(buyers)})</b>\n"]

        for i, b in enumerate(buyers, 1):
            name = b.get("name") or "Без имени"
            username = f"@{b['telegram_username']}" if b.get("telegram_username") else ""
            geos = ", ".join(b.get("geos") or []) or "—"
            verticals = ", ".join(b.get("verticals") or []) or "—"

            stats = buyer_stats.get(b["id"], {"total": 0, "wins": 0, "losses": 0})
            total = stats["total"]
            wins = stats["wins"]
            concluded = wins + stats["losses"]
            win_rate = f"{wins / concluded * 100:.0f}%" if concluded > 0 else "—"

            lines.append(
                f"{i}. <b>{name}</b> {username}\n"
                f"   Geo: {geos} | Verticals: {verticals}\n"
                f"   Креативов: {total} | Win rate: {win_rate}\n"
            )

        # Build inline keyboard with chat buttons for each buyer
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": f"💬 {b.get('name') or 'Чат'}",
                        "callback_data": f"chat_{b['telegram_id']}",
                    }
                ]
                for b in buyers
            ]
        }

        await send_telegram_message(message.chat_id, "\n".join(lines), keyboard)

    except Exception as e:
        logger.error(f"Failed to get buyers: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить баеров.")


async def handle_activity_command(message: TelegramMessage) -> None:
    """Handle /activity command - show recent buyer interactions."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get recent interactions
        response = await client.get(
            f"{sb.rest_url}/buyer_interactions"
            f"?select=telegram_id,direction,message_type,content,created_at"
            f"&order=created_at.desc&limit=15",
            headers=headers,
        )
        interactions = response.json()

        if not interactions:
            await send_telegram_message(message.chat_id, "Активности пока нет.")
            return

        # Get buyer names for telegram_ids
        telegram_ids = list(set(i["telegram_id"] for i in interactions))
        buyers_resp = await client.get(
            f"{sb.rest_url}/buyers"
            f"?telegram_id=in.({','.join(telegram_ids)})"
            f"&select=telegram_id,telegram_username,name",
            headers=headers,
        )
        buyers = {b["telegram_id"]: b for b in buyers_resp.json()}

        # Format response
        lines = ["📋 <b>Активность (последние 15)</b>\n"]

        for i in interactions:
            tid = i["telegram_id"]
            buyer = buyers.get(tid, {})
            username = (
                f"@{buyer.get('telegram_username')}" if buyer.get("telegram_username") else tid
            )

            direction = "→" if i["direction"] == "in" else "←"
            content = (i.get("content") or "")[:50]
            if len(i.get("content") or "") > 50:
                content += "..."

            # Parse timestamp
            created_at = i.get("created_at", "")
            time_str = created_at[11:16] if len(created_at) > 16 else ""

            lines.append(f"{time_str} {username} {direction} {content}")

        await send_telegram_message(message.chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить активность.")


async def handle_chat_history(chat_id: str, buyer_telegram_id: str) -> None:
    """Show last 20 messages with a specific buyer.

    Searches by both:
    - telegram_id: Direct messages from/to buyer
    - buyer_id: System messages associated with buyer (creatives, hypotheses, etc.)
    """
    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get buyer info including id for buyer_id search
        buyer_resp = await client.get(
            f"{sb.rest_url}/buyers"
            f"?telegram_id=eq.{buyer_telegram_id}"
            f"&select=id,name,telegram_username"
            f"&limit=1",
            headers=headers,
        )
        buyers = buyer_resp.json()
        buyer = buyers[0] if buyers else {}
        buyer_uuid = buyer.get("id")

        # Get last 20 messages by telegram_id OR buyer_id
        # This captures both direct messages and system notifications about buyer
        if buyer_uuid:
            # Search by both telegram_id and buyer_id
            response = await client.get(
                f"{sb.rest_url}/buyer_interactions"
                f"?or=(telegram_id.eq.{buyer_telegram_id},buyer_id.eq.{buyer_uuid})"
                f"&select=direction,message_type,content,created_at"
                f"&order=created_at.desc&limit=20",
                headers=headers,
            )
        else:
            # Fallback: search only by telegram_id
            response = await client.get(
                f"{sb.rest_url}/buyer_interactions"
                f"?telegram_id=eq.{buyer_telegram_id}"
                f"&select=direction,message_type,content,created_at"
                f"&order=created_at.desc&limit=20",
                headers=headers,
            )
        interactions = response.json()

        if not interactions:
            await send_telegram_message(chat_id, "Сообщений с этим байером нет.")
            return

        # Format header
        username = (
            f"@{buyer.get('telegram_username')}"
            if buyer.get("telegram_username")
            else buyer.get("name", buyer_telegram_id)
        )
        lines = [f"💬 <b>Переписка с {username}</b>\n"]

        # Reverse to show oldest first (chronological order)
        for i in reversed(interactions):
            direction = "→" if i["direction"] == "in" else "←"
            content = (i.get("content") or "")[:80]
            if len(i.get("content") or "") > 80:
                content += "..."

            # Parse timestamp
            created_at = i.get("created_at", "")
            time_str = created_at[11:16] if len(created_at) > 16 else ""

            lines.append(f"{time_str} {direction} {content}")

        await send_telegram_message(chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        await send_telegram_message(chat_id, "Не удалось загрузить переписку.")


async def handle_decisions_command(message: TelegramMessage) -> None:
    """Handle /decisions command - show Decision Engine stats."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get decisions from last 24 hours
        response = await client.get(
            f"{sb.rest_url}/decisions"
            f"?select=id,decision,created_at"
            f"&created_at=gte.{datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()}"
            f"&order=created_at.desc&limit=50",
            headers=headers,
        )
        decisions = response.json()

        # Count by decision type
        counts = {"approve": 0, "reject": 0, "defer": 0}
        for d in decisions:
            decision = d.get("decision", "").lower()
            if decision in counts:
                counts[decision] += 1

        total = sum(counts.values())

        # Format response
        lines = [
            "⚖️ <b>Решения DE (24ч)</b>\n",
            f"✅ APPROVE: {counts['approve']}",
            f"❌ REJECT: {counts['reject']}",
            f"⏸️ DEFER: {counts['defer']}",
            f"\nВсего: {total}",
        ]

        if decisions:
            lines.append("\n<b>Последние:</b>")
            for d in decisions[:5]:
                decision = d.get("decision", "").upper()
                created_at = d.get("created_at", "")
                time_str = created_at[11:16] if len(created_at) > 16 else ""
                emoji = {"APPROVE": "✅", "REJECT": "❌", "DEFER": "⏸️"}.get(decision, "❓")
                lines.append(f"• {time_str} {emoji} {decision}")

        await send_telegram_message(message.chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get decisions: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить решения.")


async def handle_creatives_command(message: TelegramMessage) -> None:
    """Handle /creatives command - list all creatives."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get recent creatives with buyer info
        response = await client.get(
            f"{sb.rest_url}/creatives"
            f"?select=id,buyer_id,status,tracking_status,test_result,created_at,"
            f"buyers(name,telegram_username)"
            f"&order=created_at.desc&limit=10",
            headers=headers,
        )
        creatives = response.json()

        if not creatives:
            await send_telegram_message(message.chat_id, "Креативов пока нет.")
            return

        # Format response
        lines = [f"🎬 <b>Креативы ({len(creatives)})</b>\n"]

        for c in creatives:
            buyer = c.get("buyers") or {}
            buyer_name = buyer.get("name") or buyer.get("telegram_username") or "?"

            status = c.get("status") or "?"
            tracking = c.get("tracking_status") or "?"
            result = c.get("test_result")

            result_emoji = ""
            if result == "win":
                result_emoji = " ✅"
            elif result == "loss":
                result_emoji = " ❌"

            created_at = c.get("created_at", "")
            date_str = created_at[:10] if len(created_at) >= 10 else ""

            lines.append(
                f"• {date_str} | {buyer_name}\n"
                f"  Status: {status} | Tracking: {tracking}{result_emoji}"
            )

        await send_telegram_message(message.chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get creatives: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить креативы.")


async def handle_status_command(message: TelegramMessage) -> None:
    """Handle /status command - show system status."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get counts from various tables
        buyers_resp = await client.get(
            f"{sb.rest_url}/buyers?select=id",
            headers={**headers, "Prefer": "count=exact"},
        )
        buyers_count = buyers_resp.headers.get("content-range", "0").split("/")[-1]

        creatives_resp = await client.get(
            f"{sb.rest_url}/creatives?select=id",
            headers={**headers, "Prefer": "count=exact"},
        )
        creatives_count = creatives_resp.headers.get("content-range", "0").split("/")[-1]

        decisions_resp = await client.get(
            f"{sb.rest_url}/decisions?select=id",
            headers={**headers, "Prefer": "count=exact"},
        )
        decisions_count = decisions_resp.headers.get("content-range", "0").split("/")[-1]

        # Get pending hypotheses
        hypotheses_resp = await client.get(
            f"{sb.rest_url}/hypotheses?status=is.null&select=id",
            headers={**headers, "Prefer": "count=exact"},
        )
        pending_hypotheses = hypotheses_resp.headers.get("content-range", "0").split("/")[-1]

        # Format response
        status_message = (
            "⚙️ <b>Статус системы</b>\n\n"
            f"👥 Баеров: {buyers_count}\n"
            f"🎬 Креативов: {creatives_count}\n"
            f"⚖️ Решений DE: {decisions_count}\n"
            f"📨 Гипотез в очереди: {pending_hypotheses}\n\n"
            f"<i>Обновлено: {datetime.utcnow().strftime('%H:%M:%S')} UTC</i>"
        )

        await send_telegram_message(message.chat_id, status_message)

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить статус.")


async def handle_errors_command(message: TelegramMessage) -> None:
    """Handle /errors command - show recent errors."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get failed hypotheses (with retry errors)
        response = await client.get(
            f"{sb.rest_url}/hypotheses"
            f"?status=eq.failed&select=id,last_error,retry_count,last_retry_at"
            f"&order=last_retry_at.desc&limit=10",
            headers=headers,
        )
        failed = response.json()

        if not failed:
            await send_telegram_message(
                message.chat_id,
                "❌ <b>Ошибки</b>\n\nОшибок не найдено! Всё работает.",
            )
            return

        # Format response
        lines = [f"❌ <b>Ошибки ({len(failed)})</b>\n"]

        for f in failed:
            error = (f.get("last_error") or "Unknown error")[:80]
            retry_count = f.get("retry_count") or 0
            last_retry = f.get("last_retry_at", "")
            time_str = last_retry[11:16] if len(last_retry) > 16 else "?"

            lines.append(f"• {time_str} (retry: {retry_count})\n  {error}")

        await send_telegram_message(message.chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get errors: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить ошибки.")


# =============================================================================
# MODULAR HYPOTHESIS REVIEW COMMANDS
# =============================================================================


async def get_pending_modular_hypotheses() -> list[dict]:
    """Get modular hypotheses awaiting human review."""
    try:
        sb = get_supabase()
    except RuntimeError:
        return []

    headers = sb.get_headers()

    client = get_http_client()
    # Get pending review hypotheses with module info
    response = await client.get(
        f"{sb.rest_url}/hypotheses"
        f"?generation_mode=eq.modular&review_status=eq.pending"
        f"&select=id,content,created_at,"
        f"hook_module:module_bank!hook_module_id(text_content),"
        f"promise_module:module_bank!promise_module_id(text_content),"
        f"proof_module:module_bank!proof_module_id(text_content)"
        f"&order=created_at.desc&limit=10",
        headers=headers,
    )
    return response.json() if response.status_code == 200 else []


async def update_hypothesis_review_status(hypothesis_id: str, review_status: str) -> bool:
    """Update hypothesis review status (approved/rejected)."""
    try:
        sb = get_supabase()
    except RuntimeError:
        return False

    headers = sb.get_headers(for_write=True)

    update_data = {
        "review_status": review_status,
    }

    # If approved, also update main status to ready for delivery
    if review_status == "approved":
        update_data["status"] = "generated"

    # If rejected, mark as rejected
    if review_status == "rejected":
        update_data["status"] = "rejected"

    client = get_http_client()
    response = await client.patch(
        f"{sb.rest_url}/hypotheses?id=eq.{hypothesis_id}",
        headers=headers,
        json=update_data,
    )
    return response.status_code in [200, 204]


async def handle_pending_command(message: TelegramMessage) -> None:
    """Handle /pending command - show modular hypotheses awaiting review."""
    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content="/pending",
    )

    try:
        hypotheses = await get_pending_modular_hypotheses()

        if not hypotheses:
            await send_telegram_message(
                message.chat_id,
                "📋 <b>Modular Review</b>\n\nНет гипотез на ревью.",
            )
            return

        lines = [f"📋 <b>Modular Review</b> ({len(hypotheses)})\n"]

        for h in hypotheses:
            short_id = str(h["id"])[:8]
            created = h.get("created_at", "")[:10]

            # Get module texts
            hook_text = ""
            promise_text = ""
            proof_text = ""

            if h.get("hook_module"):
                hook_text = (h["hook_module"].get("text_content") or "")[:50]
            if h.get("promise_module"):
                promise_text = (h["promise_module"].get("text_content") or "")[:50]
            if h.get("proof_module"):
                proof_text = (h["proof_module"].get("text_content") or "")[:50]

            lines.append(f"<b>#{short_id}</b> ({created})")
            if hook_text:
                lines.append(f"  🎣 {hook_text}...")
            if promise_text:
                lines.append(f"  💎 {promise_text}...")
            if proof_text:
                lines.append(f"  ✅ {proof_text}...")
            lines.append("")

        lines.append("<i>/approve &lt;id&gt; - одобрить</i>")
        lines.append("<i>/reject &lt;id&gt; - отклонить</i>")

        await send_telegram_message(message.chat_id, "\n".join(lines))

    except Exception as e:
        logger.error(f"Failed to get pending hypotheses: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить гипотезы на ревью.")


async def handle_approve_command(message: TelegramMessage) -> None:
    """Handle /approve <id> command - approve modular hypothesis."""
    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    text = message.text or ""
    # Filter empty parts to handle multiple whitespace (issue #543)
    parts = [p for p in text.strip().split() if p]

    if len(parts) < 2:
        await send_telegram_message(
            message.chat_id,
            "Использование: /approve &lt;id&gt;\nПример: /approve a1b2c3d4",
        )
        return

    hypothesis_id_prefix = parts[1].lower()

    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    try:
        # Find hypothesis by prefix
        hypotheses = await get_pending_modular_hypotheses()
        matching = [h for h in hypotheses if str(h["id"]).lower().startswith(hypothesis_id_prefix)]

        if not matching:
            await send_telegram_message(
                message.chat_id,
                f"Гипотеза {hypothesis_id_prefix} не найдена среди pending.",
            )
            return

        if len(matching) > 1:
            await send_telegram_message(
                message.chat_id,
                f"Найдено {len(matching)} гипотез с префиксом {hypothesis_id_prefix}. "
                "Укажите более длинный ID.",
            )
            return

        hypothesis = matching[0]
        hypothesis_id = str(hypothesis["id"])

        success = await update_hypothesis_review_status(hypothesis_id, "approved")

        if success:
            await send_telegram_message(
                message.chat_id,
                f"✅ Гипотеза <code>{hypothesis_id[:8]}</code> одобрена.\n"
                "Статус: ready for delivery.",
            )
            logger.info(f"Hypothesis {hypothesis_id} approved by {message.user_id}")
        else:
            await send_telegram_message(message.chat_id, "Ошибка при обновлении статуса.")

    except Exception as e:
        logger.error(f"Failed to approve hypothesis: {e}")
        await send_telegram_message(message.chat_id, f"Ошибка: {str(e)[:100]}")


async def handle_reject_command(message: TelegramMessage) -> None:
    """Handle /reject <id> command - reject modular hypothesis."""
    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    text = message.text or ""
    # Filter empty parts to handle multiple whitespace (issue #543)
    parts = [p for p in text.strip().split() if p]

    if len(parts) < 2:
        await send_telegram_message(
            message.chat_id,
            "Использование: /reject &lt;id&gt;\nПример: /reject a1b2c3d4",
        )
        return

    hypothesis_id_prefix = parts[1].lower()

    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content=text,
    )

    try:
        # Find hypothesis by prefix
        hypotheses = await get_pending_modular_hypotheses()
        matching = [h for h in hypotheses if str(h["id"]).lower().startswith(hypothesis_id_prefix)]

        if not matching:
            await send_telegram_message(
                message.chat_id,
                f"Гипотеза {hypothesis_id_prefix} не найдена среди pending.",
            )
            return

        if len(matching) > 1:
            await send_telegram_message(
                message.chat_id,
                f"Найдено {len(matching)} гипотез с префиксом {hypothesis_id_prefix}. "
                "Укажите более длинный ID.",
            )
            return

        hypothesis = matching[0]
        hypothesis_id = str(hypothesis["id"])

        success = await update_hypothesis_review_status(hypothesis_id, "rejected")

        if success:
            await send_telegram_message(
                message.chat_id,
                f"❌ Гипотеза <code>{hypothesis_id[:8]}</code> отклонена.",
            )
            logger.info(f"Hypothesis {hypothesis_id} rejected by {message.user_id}")
        else:
            await send_telegram_message(message.chat_id, "Ошибка при обновлении статуса.")

    except Exception as e:
        logger.error(f"Failed to reject hypothesis: {e}")
        await send_telegram_message(message.chat_id, f"Ошибка: {str(e)[:100]}")


# =============================================================================
# ADMIN PUSH NOTIFICATIONS
# =============================================================================


async def notify_admin(event_type: str, data: dict) -> None:
    """
    Send push notification to all admins.

    Event types:
    - new_buyer: New buyer registered
    - creative_win: Creative got WIN result
    - creative_loss: Creative got LOSS result
    - error: Error in command or workflow
    - workflow_stuck: Workflow running too long
    """
    message = format_admin_notification(event_type, data)
    if not message:
        return

    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            await send_telegram_message(admin_id, message)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


def format_admin_notification(event_type: str, data: dict) -> str:
    """Format admin notification message."""
    if event_type == "new_buyer":
        name = data.get("name") or "Без имени"
        username = f"@{data['username']}" if data.get("username") else ""
        return f"👤 <b>Новый баер:</b> {name} {username}"

    elif event_type == "creative_win":
        username = f"@{data['username']}" if data.get("username") else data.get("buyer_name", "?")
        roi = data.get("roi")
        roi_str = f" (ROI {roi:+.0f}%)" if roi is not None else ""
        return f"🎉 <b>WIN:</b> креатив от {username}{roi_str}"

    elif event_type == "creative_loss":
        username = f"@{data['username']}" if data.get("username") else data.get("buyer_name", "?")
        return f"📉 <b>LOSS:</b> креатив от {username}"

    elif event_type == "error":
        command = data.get("command", "?")
        username = f"@{data['username']}" if data.get("username") else data.get("telegram_id", "?")
        error = data.get("error", "Unknown error")[:100]
        return f"❌ <b>Ошибка {command}</b> для {username}:\n{error}"

    elif event_type == "workflow_stuck":
        workflow_id = data.get("workflow_id", "?")
        minutes = data.get("minutes", "?")
        return f"⚠️ <b>Workflow завис:</b> {workflow_id} ({minutes} мин)"

    return ""


# Admin telegram IDs (from environment variable)
ADMIN_TELEGRAM_IDS = [
    aid.strip() for aid in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",") if aid.strip()
]


def is_admin(telegram_id: str) -> bool:
    """Check if user is admin."""
    return bool(telegram_id and telegram_id in ADMIN_TELEGRAM_IDS)


async def handle_knowledge_command(message: TelegramMessage) -> None:
    """Handle /knowledge command - show pending extractions."""

    if not is_admin(message.user_id):
        await send_telegram_message(message.chat_id, "Эта команда доступна только администраторам.")
        return

    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        client = get_http_client()
        # Get pending extractions
        response = await client.get(
            f"{sb.rest_url}/knowledge_extractions?status=eq.pending&order=created_at.asc&limit=5",
            headers=headers,
        )
        extractions = response.json()

        if not extractions:
            await send_telegram_message(
                message.chat_id,
                "Нет ожидающих извлечений знаний.\n\n"
                "Загрузите .txt или .md файл с транскриптом для извлечения.",
            )
            return

        # Send first pending extraction for review
        ext = extractions[0]
        await send_extraction_review_card(message.chat_id, ext)

        if len(extractions) > 1:
            await send_telegram_message(
                message.chat_id,
                f"<i>+{len(extractions) - 1} ещё ожидают</i>",
            )

    except Exception as e:
        logger.error(f"Failed to get knowledge extractions: {e}")
        await send_telegram_message(message.chat_id, "Не удалось загрузить извлечения.")


async def send_extraction_review_card(chat_id: str, extraction: dict) -> None:
    """Send extraction review card with inline buttons."""

    emoji_map = {
        "premise": "📖",
        "creative_attribute": "🏷️",
        "process_rule": "📋",
        "component_weight": "⚖️",
    }

    knowledge_type = extraction.get("knowledge_type", "unknown")
    emoji = emoji_map.get(knowledge_type, "📦")
    confidence = extraction.get("confidence_score")
    confidence_str = f"{confidence:.0%}" if confidence else "N/A"

    # Format payload preview
    payload = extraction.get("payload", {})
    payload_preview = str(payload)[:300]
    if len(str(payload)) > 300:
        payload_preview += "..."

    # Format supporting quote
    quotes = extraction.get("supporting_quotes", [])
    quote_str = f'"{quotes[0][:150]}..."' if quotes else "No quotes"

    card = (
        f"{emoji} <b>Извлечение знаний</b>\n\n"
        f"<b>Тип:</b> {knowledge_type}\n"
        f"<b>Название:</b> {extraction.get('name')}\n"
        f"<b>Уверенность:</b> {confidence_str}\n\n"
        f"<b>Описание:</b>\n{extraction.get('description', 'N/A')[:200]}\n\n"
        f"<b>Цитата:</b>\n<i>{quote_str}</i>\n\n"
        f"<b>Данные:</b>\n<code>{payload_preview}</code>"
    )

    extraction_id = extraction.get("id")

    # Send with inline keyboard
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Одобрить", "callback_data": f"ke_approve_{extraction_id}"},
                {"text": "❌ Отклонить", "callback_data": f"ke_reject_{extraction_id}"},
            ],
            [
                {"text": "⏭️ Пропустить", "callback_data": f"ke_skip_{extraction_id}"},
            ],
        ]
    }

    client = get_http_client()
    await client.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": card,
            "parse_mode": "HTML",
            "reply_markup": keyboard,
        },
        timeout=30.0,
    )


async def handle_feedback_command(message: TelegramMessage) -> None:
    """
    Handle /feedback command - create GitHub issue from buyer feedback.

    Usage: /feedback текст проблемы или предложения
    """
    from src.services.github_issue import create_feedback_issue

    # Extract text after /feedback
    text = message.text or ""
    feedback_text = text.replace("/feedback", "", 1).strip()

    if not feedback_text:
        await send_telegram_message(
            message.chat_id,
            "Напишите текст отзыва после команды.\n\n"
            "Пример: <code>/feedback Не работает загрузка видео</code>",
        )
        return

    if len(feedback_text) < 10:
        await send_telegram_message(
            message.chat_id,
            "Текст слишком короткий (минимум 10 символов).",
        )
        return

    if len(feedback_text) > MAX_FEEDBACK_LENGTH:
        await send_telegram_message(
            message.chat_id,
            f"❌ Текст слишком длинный (максимум {MAX_FEEDBACK_LENGTH} символов).",
        )
        return

    # Get buyer name if available
    buyer_name = await get_buyer_name(message.user_id)

    # Create GitHub issue
    result = await create_feedback_issue(
        text=feedback_text,
        telegram_id=message.user_id,
        buyer_name=buyer_name,
    )

    if result.success:
        await send_telegram_message(
            message.chat_id,
            f"✅ Заявка #{result.issue_number} принята!\n\nСпасибо за обратную связь.",
        )

        # Log interaction
        await log_buyer_interaction(
            telegram_id=message.user_id,
            direction="in",
            message_type="feedback",
            content=feedback_text,
            context={"issue_number": result.issue_number},
        )
    else:
        await send_telegram_message(
            message.chat_id,
            "Не удалось отправить отзыв. Попробуйте позже.",
        )
        logger.error(f"Feedback issue creation failed: {result.error}")


async def get_buyer_name(telegram_id: str) -> str | None:
    """Get buyer name by Telegram ID."""
    try:
        sb = get_supabase()
    except RuntimeError:
        return None

    headers = sb.get_headers()

    try:
        client = get_http_client()
        response = await client.get(
            f"{sb.rest_url}/buyers?telegram_id=eq.{telegram_id}&select=name",
            headers=headers,
        )
        buyers = response.json()
        return buyers[0].get("name") if buyers else None
    except httpx.HTTPStatusError as e:
        logger.debug(f"HTTP error getting buyer name for telegram_id={telegram_id}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error getting buyer name for telegram_id={telegram_id}: {e}")
        return None


async def handle_document_upload(message: TelegramMessage) -> None:
    """Handle document upload - start knowledge extraction for .txt/.md files."""

    if not is_admin(message.user_id):
        await send_telegram_message(
            message.chat_id,
            "Извлечение знаний доступно только администраторам.",
        )
        return

    document = message.document
    if not document:
        return

    file_name = document.get("file_name", "")

    # Check file extension
    if not (file_name.endswith(".txt") or file_name.endswith(".md")):
        await send_telegram_message(
            message.chat_id,
            "Загрузите .txt или .md файл с транскриптом.",
        )
        return

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        await send_telegram_message(message.chat_id, "Бот не настроен.")
        return

    try:
        client = get_http_client()
        # Get file info
        file_id = document.get("file_id")
        file_resp = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id},
            timeout=30.0,
        )
        file_data = file_resp.json()

        if not file_data.get("ok"):
            await send_telegram_message(message.chat_id, "Не удалось получить файл.")
            return

        file_path = file_data["result"]["file_path"]

        # Download file content
        content_resp = await client.get(
            f"https://api.telegram.org/file/bot{bot_token}/{file_path}",
            timeout=60.0,
        )
        content = content_resp.text

        await send_telegram_message(
            message.chat_id,
            f"📄 <b>Файл получен:</b> {file_name}\n"
            f"📏 Размер: {len(content)} символов\n\n"
            f"Запускаю извлечение знаний...",
        )

        # Start ingestion workflow
        from temporal.models.knowledge import KnowledgeSourceInput

        temporal_client = await get_temporal_client()

        input_data = KnowledgeSourceInput(
            title=file_name,
            content=content,
            source_type="file",
            url=None,
            created_by=message.user_id,
        )

        import uuid

        workflow_id = f"knowledge-ingest-{uuid.uuid4().hex[:8]}"

        await temporal_client.start_workflow(
            "KnowledgeIngestionWorkflow",
            input_data,
            id=workflow_id,
            task_queue="knowledge",
        )

        logger.info(f"Started knowledge ingestion: {workflow_id}")

    except Exception as e:
        logger.error(f"Failed to process document: {e}")
        await send_telegram_message(
            message.chat_id,
            f"Не удалось обработать файл: {str(e)[:100]}",
        )


async def handle_callback_query(update: dict) -> None:
    """Handle callback query from inline buttons."""

    callback_query = update.get("callback_query")
    if not callback_query:
        return

    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    user_id = str(callback_query.get("from", {}).get("id", ""))
    chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id", ""))
    message_id = callback_query.get("message", {}).get("message_id")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    # Answer callback to remove loading state
    client = get_http_client()
    await client.post(
        f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
        json={"callback_query_id": callback_id},
        timeout=10.0,
    )

    # Check admin permission
    if not is_admin(user_id):
        return

    # Parse and validate callback data
    try:
        action, identifier = parse_callback_data(data)
    except CallbackDataError as e:
        logger.warning(f"Invalid callback_data from user {user_id}: {e}")
        return

    # Route to appropriate handler
    if action == "ke_approve":
        await handle_extraction_approve(chat_id, message_id, identifier, user_id)
    elif action == "ke_reject":
        await handle_extraction_reject(chat_id, message_id, identifier, user_id)
    elif action == "ke_skip":
        await send_telegram_message(chat_id, "Пропущено. Используйте /knowledge для следующего.")
    elif action == "chat":
        await handle_chat_history(chat_id, identifier)
    else:
        logger.warning(f"Unknown callback action: {action}")


async def handle_extraction_approve(
    chat_id: str, message_id: int, extraction_id: str, user_id: str
) -> None:
    """Handle extraction approval."""

    try:
        # Start application workflow
        from temporal.models.knowledge import ApplyKnowledgeInput

        temporal_client = await get_temporal_client()

        input_data = ApplyKnowledgeInput(
            extraction_id=extraction_id,
            reviewed_by=user_id,
        )

        workflow_id = f"knowledge-apply-{extraction_id[:8]}"

        await temporal_client.start_workflow(
            "KnowledgeApplicationWorkflow",
            input_data,
            id=workflow_id,
            task_queue="knowledge",
        )

        # Update message
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            client = get_http_client()
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": "✅ <b>Одобрено</b>\n\nПрименяю знания...",
                    "parse_mode": "HTML",
                },
                timeout=10.0,
            )

        logger.info(f"Started knowledge application: {workflow_id}")

    except Exception as e:
        logger.error(f"Failed to approve extraction: {e}")
        await send_telegram_message(chat_id, f"Не удалось одобрить: {str(e)[:100]}")


async def handle_extraction_reject(
    chat_id: str, message_id: int, extraction_id: str, user_id: str
) -> None:
    """Handle extraction rejection."""
    from datetime import datetime

    try:
        sb = get_supabase()
    except RuntimeError:
        return

    try:
        headers = sb.get_headers(for_write=True)
        headers["Prefer"] = "return=minimal"

        client = get_http_client()
        await client.patch(
            f"{sb.rest_url}/knowledge_extractions?id=eq.{extraction_id}",
            headers=headers,
            json={
                "status": "rejected",
                "reviewed_by": user_id,
                "reviewed_at": datetime.utcnow().isoformat(),
            },
            timeout=10.0,
        )

        # Update message
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            client = get_http_client()
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": "❌ <b>Отклонено</b>",
                    "parse_mode": "HTML",
                },
                timeout=10.0,
            )

        logger.info(f"Rejected extraction: {extraction_id}")

    except Exception as e:
        logger.error(f"Failed to reject extraction: {e}")
        await send_telegram_message(chat_id, f"Не удалось отклонить: {str(e)[:100]}")


async def handle_video_url(message: TelegramMessage, video_url: str) -> None:
    """Handle video URL - start creative registration."""
    from temporal.workflows.historical_import import CreativeRegistrationWorkflow

    # Check if user is registered
    try:
        sb = get_supabase()
    except RuntimeError:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = sb.get_headers()

        http_client = get_http_client()
        buyer_resp = await http_client.get(
            f"{sb.rest_url}/buyers?telegram_id=eq.{message.user_id}&select=id",
            headers=headers,
        )
        buyers = buyer_resp.json()

        if not buyers:
            await send_telegram_message(
                message.chat_id,
                "Сначала нужно зарегистрироваться. Отправьте /start.",
            )
            return

        buyer_id = buyers[0]["id"]

        # Start creative registration workflow
        client = await get_temporal_client()

        import uuid

        workflow_id = f"creative-reg-{uuid.uuid4().hex[:8]}"

        await client.start_workflow(
            CreativeRegistrationWorkflow.run,
            args=[buyer_id, video_url, None, None],
            id=workflow_id,
            task_queue="telegram",
        )

        await send_telegram_message(
            message.chat_id,
            f"Видео получено!\n\n"
            f"<i>URL: {html_escape(video_url[:50])}...</i>\n\n"
            f"Обработка скоро начнётся. Уведомлю когда будет готово.",
        )

        logger.info(f"Started creative registration: {workflow_id}")

    except Exception as e:
        logger.error(f"Failed to register creative: {e}")
        await send_telegram_message(
            message.chat_id, "Не удалось обработать видео. Попробуйте снова."
        )


async def handle_user_message(message: TelegramMessage) -> None:
    """Handle regular user message - signal to active workflow."""
    from temporal.models.buyer import BuyerMessage

    # Check for active onboarding workflow
    active_workflow = await check_active_onboarding(message.user_id)

    if active_workflow:
        try:
            client = await get_temporal_client()
            handle = client.get_workflow_handle(active_workflow)

            # Send signal to workflow
            await handle.signal(
                "user_message",
                BuyerMessage(
                    text=message.text or "",
                    telegram_id=str(message.user_id),
                    message_id=message.message_id,
                    timestamp=datetime.utcnow(),
                ),
            )

            logger.info(f"Sent signal to workflow: {active_workflow}")
            return

        except Exception as e:
            logger.error(f"Failed to signal workflow: {e}")

    # No active workflow - check if it's a video URL
    if message.text:
        video_url = extract_video_url(message.text)
        if video_url:
            await handle_video_url(message, video_url)
            return

    # Unknown message
    await send_telegram_message(
        message.chat_id,
        "Не понимаю эту команду.\nОтправьте /help для списка команд.",
    )


async def process_telegram_update(update: dict) -> None:
    """Process incoming Telegram update."""
    try:
        await _process_telegram_update_inner(update)
    except Exception as e:
        # Log with full traceback - critical for debugging background task failures
        logger.exception(f"Failed to process Telegram update {update.get('update_id')}: {e}")
        # Track error for monitoring
        webhook_error_stats.record_error(e)


async def _process_telegram_update_inner(update: dict) -> None:
    """Inner function for processing Telegram updates."""
    # Handle callback queries (inline button presses)
    if "callback_query" in update:
        await handle_callback_query(update)
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

        if text == "/start":
            await handle_start_command(message)
        elif text == "/stats":
            await handle_stats_command(message)
        elif text == "/help":
            await handle_help_command(message)
        elif text == "/knowledge":
            await handle_knowledge_command(message)
        elif text.startswith("/genome"):
            await handle_genome_command(message)
        elif text.startswith("/confidence"):
            await handle_confidence_command(message)
        elif text.startswith("/trends"):
            await handle_trends_command(message)
        elif text.startswith("/drift"):
            await handle_drift_command(message)
        elif text.startswith("/correlations"):
            await handle_correlations_command(message)
        elif text.startswith("/recommend"):
            await handle_recommend_command(message)
        elif text.startswith("/simulate"):
            await handle_simulate_command(message)
        elif text.startswith("/feedback"):
            await handle_feedback_command(message)
        # Admin monitoring commands
        elif text == "/buyers":
            await handle_buyers_command(message)
        elif text == "/activity":
            await handle_activity_command(message)
        elif text == "/decisions":
            await handle_decisions_command(message)
        elif text == "/creatives":
            await handle_creatives_command(message)
        elif text == "/status":
            await handle_status_command(message)
        elif text == "/errors":
            await handle_errors_command(message)
        # Modular hypothesis review commands
        elif text == "/pending":
            await handle_pending_command(message)
        elif text.startswith("/approve"):
            await handle_approve_command(message)
        elif text.startswith("/reject"):
            await handle_reject_command(message)
        elif text.startswith("/"):
            # Unknown command
            await send_telegram_message(
                message.chat_id,
                f"Неизвестная команда: {text}\nОтправьте /help для списка команд.",
            )
        else:
            # Regular message
            await handle_user_message(message)

    elif message.document:
        # Handle document upload (for knowledge extraction)
        await handle_document_upload(message)

    elif message.video:
        # Handle video
        await send_telegram_message(
            message.chat_id,
            "Отправьте ссылку на видео вместо загрузки файла.\n"
            "Example: https://example.com/video.mp4",
        )


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook endpoint.

    Receives updates from Telegram Bot API and processes them asynchronously.
    Verifies X-Telegram-Bot-Api-Secret-Token header if TELEGRAM_WEBHOOK_SECRET is set.
    """
    # Verify webhook secret before processing
    verify_webhook_secret(request)

    try:
        update = await request.json()
        logger.debug(f"Received Telegram update: {update.get('update_id')}")

        # Process in background to respond quickly
        background_tasks.add_task(process_telegram_update, update)

        return {"ok": True}

    except Exception as e:
        # Log with full traceback for debugging
        logger.exception(f"Telegram webhook error: {e}")
        # Track error for monitoring (GET /webhook/telegram/errors)
        webhook_error_stats.record_error(e)
        # Return 200 to prevent Telegram from retrying endlessly
        # (Telegram retries on non-2xx, which can cause infinite loops on persistent errors)
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
        data = response.json()

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
