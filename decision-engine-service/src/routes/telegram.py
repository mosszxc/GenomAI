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


async def send_telegram_photo(chat_id: str, photo_url: str, caption: str = "") -> bool:
    """Send a photo to Telegram chat by URL."""
    import httpx

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            json={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML",
            },
            timeout=30.0,
        )

        data = response.json()
        if not data.get("ok"):
            logger.error(f"Telegram sendPhoto error: {data.get('description')}")
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
            "У вас уже есть активная регистрация.\n"
            "Завершите её или дождитесь таймаута.",
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
        async with httpx.AsyncClient() as client:
            await client.post(
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
        await send_telegram_message(message.chat_id, "Статистика временно недоступна.")
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
                    "Вы ещё не зарегистрированы. Отправьте /start для начала.",
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
    """Handle /help command."""
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
        if by_index + 1 < len(parts):
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
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
        return

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        # Generate emotion win rate chart
        chart_url = await generate_win_rate_chart_url(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
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
                f"График создан, но не удалось отправить картинку.\n"
                f"Ссылка: {chart_url[:100]}...",
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
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
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
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
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
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
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
                "positive": len(
                    [c for c in correlations if c.correlation_type == "positive"]
                ),
                "negative": len(
                    [c for c in correlations if c.correlation_type == "negative"]
                ),
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
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
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


# Admin telegram IDs (for knowledge extraction)
ADMIN_TELEGRAM_IDS = ["291678304"]


def is_admin(telegram_id: str) -> bool:
    """Check if user is admin."""
    return telegram_id in ADMIN_TELEGRAM_IDS


async def handle_knowledge_command(message: TelegramMessage) -> None:
    """Handle /knowledge command - show pending extractions."""
    import httpx

    if not is_admin(message.user_id):
        await send_telegram_message(
            message.chat_id, "Эта команда доступна только администраторам."
        )
        return

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
        return

    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept-Profile": "genomai",
        }

        async with httpx.AsyncClient() as client:
            # Get pending extractions
            response = await client.get(
                f"{supabase_url}/rest/v1/knowledge_extractions"
                f"?status=eq.pending&order=created_at.asc&limit=5",
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
    import httpx

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

    async with httpx.AsyncClient() as client:
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
    import httpx

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return None

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/buyers"
                f"?telegram_id=eq.{telegram_id}"
                f"&select=name",
                headers=headers,
            )
            buyers = response.json()
            return buyers[0].get("name") if buyers else None
    except Exception:
        return None


async def handle_document_upload(message: TelegramMessage) -> None:
    """Handle document upload - start knowledge extraction for .txt/.md files."""
    import httpx

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
        async with httpx.AsyncClient() as client:
            # Get file info
            file_id = document.get("file_id")
            file_resp = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getFile",
                params={"file_id": file_id},
                timeout=30.0,
            )
            file_data = file_resp.json()

            if not file_data.get("ok"):
                await send_telegram_message(
                    message.chat_id, "Не удалось получить файл."
                )
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
    import httpx

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
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=10.0,
        )

    # Check admin permission
    if not is_admin(user_id):
        return

    # Parse callback data
    if data.startswith("ke_approve_"):
        extraction_id = data.replace("ke_approve_", "")
        await handle_extraction_approve(chat_id, message_id, extraction_id, user_id)

    elif data.startswith("ke_reject_"):
        extraction_id = data.replace("ke_reject_", "")
        await handle_extraction_reject(chat_id, message_id, extraction_id, user_id)

    elif data.startswith("ke_skip_"):
        # Just show next extraction
        await send_telegram_message(
            chat_id, "Пропущено. Используйте /knowledge для следующего."
        )


async def handle_extraction_approve(
    chat_id: str, message_id: int, extraction_id: str, user_id: str
) -> None:
    """Handle extraction approval."""
    import httpx

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
            async with httpx.AsyncClient() as client:
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
    import httpx
    from datetime import datetime

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return

    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Profile": "genomai",
            "Prefer": "return=minimal",
        }

        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{supabase_url}/rest/v1/knowledge_extractions?id=eq.{extraction_id}",
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
            async with httpx.AsyncClient() as client:
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
    import httpx
    from temporal.workflows.historical_import import CreativeRegistrationWorkflow

    # Check if user is registered
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        await send_telegram_message(message.chat_id, "Сервис временно недоступен.")
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
            f"<i>URL: {video_url[:50]}...</i>\n\n"
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
    # Handle callback queries (inline button presses)
    if "callback_query" in update:
        await handle_callback_query(update)
        return

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
