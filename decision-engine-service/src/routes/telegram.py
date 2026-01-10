"""
Telegram Webhook Router

Handles incoming Telegram messages and routes them to appropriate workflows.

Routes:
    /start → Start BuyerOnboardingWorkflow
    /stats → Direct stats response
    /help → Help message
    Video/URL → CreativeRegistrationWorkflow or signal to active onboarding
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


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


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message to Telegram chat."""
    import httpx

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=30.0,
        )

        data = response.json()
        if not data.get("ok"):
            logger.error(f"Telegram error: {data.get('description')}")
            return False

        return True


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
        except Exception:
            # Workflow doesn't exist or completed
            pass

        return None
    except Exception as e:
        logger.error(f"Error checking active onboarding: {e}")
        return None


def extract_video_url(text: str) -> Optional[str]:
    """Extract video URL from text."""
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
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    # Check if entire text is a URL
    if text.startswith("http://") or text.startswith("https://"):
        return text.strip()

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
            "You already have an active registration in progress.\n"
            "Please complete it or wait for timeout.",
        )

    except Exception as e:
        logger.error(f"Failed to start onboarding: {e}")
        await send_telegram_message(
            message.chat_id,
            "Failed to start registration. Please try again later.",
        )


async def log_buyer_interaction(
    telegram_id: str,
    direction: str,
    message_type: str,
    content: str,
    context: Optional[dict] = None,
) -> None:
    """Log interaction to buyer_interactions table."""
    import httpx

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Profile": "genomai",
        "Prefer": "return=minimal",
    }

    try:
        logger.info(f"Logging buyer interaction: {direction} {message_type}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{supabase_url}/rest/v1/buyer_interactions",
                headers=headers,
                json={
                    "telegram_id": telegram_id,
                    "direction": direction,
                    "message_type": message_type,
                    "content": content,
                    "context": context,
                },
                timeout=10.0,
            )
            if response.status_code >= 400:
                logger.error(f"Supabase error {response.status_code}: {response.text}")
            else:
                logger.info(f"Logged interaction: {direction} {message_type}")
    except Exception as e:
        logger.error(f"Failed to log buyer interaction: {e}")


async def handle_stats_command(message: TelegramMessage) -> None:
    """Handle /stats command - show user stats."""
    import httpx

    # Log incoming command
    await log_buyer_interaction(
        telegram_id=message.user_id,
        direction="in",
        message_type="command",
        content="/stats",
    )

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        await send_telegram_message(message.chat_id, "Stats temporarily unavailable.")
        return

    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept-Profile": "genomai",
        }

        async with httpx.AsyncClient() as client:
            # Get buyer
            buyer_resp = await client.get(
                f"{supabase_url}/rest/v1/buyers"
                f"?telegram_id=eq.{message.user_id}"
                f"&select=id,name,geos,verticals",
                headers=headers,
            )
            buyers = buyer_resp.json()

            if not buyers:
                await send_telegram_message(
                    message.chat_id,
                    "You're not registered yet. Send /start to begin.",
                )
                return

            buyer = buyers[0]
            buyer_id = buyer["id"]

            # Get creatives with test results and tracker_ids
            creatives_resp = await client.get(
                f"{supabase_url}/rest/v1/creatives"
                f"?buyer_id=eq.{buyer_id}"
                f"&select=id,status,test_result,tracking_status,tracker_id",
                headers=headers,
            )
            creatives = creatives_resp.json()

            total = len(creatives)
            wins = len([c for c in creatives if c.get("test_result") == "win"])
            losses = len([c for c in creatives if c.get("test_result") == "loss"])
            testing = len(
                [c for c in creatives if c.get("tracking_status") == "tracking"]
            )

            # Calculate win rate
            concluded = wins + losses
            win_rate = (wins / concluded * 100) if concluded > 0 else 0

            # Get spend/revenue from metrics
            tracker_ids = [
                c.get("tracker_id") for c in creatives if c.get("tracker_id")
            ]
            total_spend = 0.0
            total_revenue = 0.0

            if tracker_ids:
                # Fetch metrics for all tracker_ids
                tracker_list = ",".join(tracker_ids)
                metrics_resp = await client.get(
                    f"{supabase_url}/rest/v1/raw_metrics_current"
                    f"?tracker_id=in.({tracker_list})"
                    f"&select=metrics",
                    headers=headers,
                )
                metrics_rows = metrics_resp.json()

                if isinstance(metrics_rows, list):
                    for row in metrics_rows:
                        metrics = row.get("metrics") or {}
                        total_spend += float(metrics.get("spend", 0) or 0)
                        total_revenue += float(metrics.get("revenue", 0) or 0)

            # Calculate ROI
            roi = (
                ((total_revenue - total_spend) / total_spend * 100)
                if total_spend > 0
                else 0
            )
            roi_sign = "+" if roi >= 0 else ""

            stats_message = (
                f"📊 <b>Твоя статистика:</b>\n\n"
                f"Креативов: {total}\n"
                f"✅ Wins: {wins} ({win_rate:.0f}%)\n"
                f"❌ Losses: {losses}\n"
                f"⏳ Testing: {testing}\n\n"
                f"ROI: {roi_sign}{roi:.1f}%\n"
                f"Spend: ${total_spend:.0f}\n"
                f"Revenue: ${total_revenue:.0f}"
            )

            await send_telegram_message(message.chat_id, stats_message)

            # Log outgoing response
            logger.info(f"Stats calculated for {message.user_id}: {total} creatives")
            await log_buyer_interaction(
                telegram_id=message.user_id,
                direction="out",
                message_type="stats_response",
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
        await send_telegram_message(message.chat_id, "Failed to load stats.")


async def handle_help_command(message: TelegramMessage) -> None:
    """Handle /help command."""
    help_message = (
        "<b>GenomAI Bot Commands</b>\n\n"
        "/start - Start registration\n"
        "/stats - View your statistics\n"
        "/help - Show this help\n\n"
        "<b>To register a creative:</b>\n"
        "Just send a video URL and we'll process it for you.\n\n"
        "<i>Example: https://example.com/video.mp4</i>"
    )

    await send_telegram_message(message.chat_id, help_message)


async def handle_video_url(message: TelegramMessage, video_url: str) -> None:
    """Handle video URL - start creative registration."""
    import httpx
    from temporal.workflows.historical_import import CreativeRegistrationWorkflow

    # Check if user is registered
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        await send_telegram_message(message.chat_id, "Service temporarily unavailable.")
        return

    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept-Profile": "genomai",
        }

        async with httpx.AsyncClient() as http_client:
            buyer_resp = await http_client.get(
                f"{supabase_url}/rest/v1/buyers"
                f"?telegram_id=eq.{message.user_id}"
                f"&select=id",
                headers=headers,
            )
            buyers = buyer_resp.json()

            if not buyers:
                await send_telegram_message(
                    message.chat_id,
                    "You need to register first. Send /start to begin.",
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
            f"Video received!\n\n"
            f"<i>URL: {video_url[:50]}...</i>\n\n"
            f"Processing will begin shortly. You'll be notified when done.",
        )

        logger.info(f"Started creative registration: {workflow_id}")

    except Exception as e:
        logger.error(f"Failed to register creative: {e}")
        await send_telegram_message(
            message.chat_id, "Failed to process video. Please try again."
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
        "I don't understand that command.\nSend /help to see available commands.",
    )


async def process_telegram_update(update: dict) -> None:
    """Process incoming Telegram update."""
    message = parse_update(update)
    if not message:
        return

    logger.info(f"Telegram message from {message.user_id}: {message.text or '[media]'}")

    # Handle commands
    if message.text:
        text = message.text.strip()

        if text == "/start":
            await handle_start_command(message)
        elif text == "/stats":
            await handle_stats_command(message)
        elif text == "/help":
            await handle_help_command(message)
        elif text.startswith("/"):
            # Unknown command
            await send_telegram_message(
                message.chat_id,
                f"Unknown command: {text}\nSend /help for available commands.",
            )
        else:
            # Regular message
            await handle_user_message(message)

    elif message.video or message.document:
        # Handle video/document (future: extract URL and process)
        await send_telegram_message(
            message.chat_id,
            "Please send a video URL instead of uploading directly.\n"
            "Example: https://example.com/video.mp4",
        )


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram webhook endpoint.

    Receives updates from Telegram Bot API and processes them asynchronously.
    """
    try:
        update = await request.json()
        logger.debug(f"Received Telegram update: {update.get('update_id')}")

        # Process in background to respond quickly
        background_tasks.add_task(process_telegram_update, update)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        # Still return 200 to prevent Telegram from retrying
        return {"ok": True, "error": str(e)}


@router.get("/webhook/telegram/status")
async def telegram_webhook_status():
    """Check Telegram webhook configuration status."""
    import httpx

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {
            "status": "not_configured",
            "error": "TELEGRAM_BOT_TOKEN not set",
        }

    try:
        async with httpx.AsyncClient() as client:
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
