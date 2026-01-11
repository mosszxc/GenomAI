"""
Buyer Onboarding Workflow

Multi-step Telegram-based buyer registration workflow.
Uses Temporal signals for user input and state machine for flow control.

States:
    AWAITING_NAME → AWAITING_GEO → AWAITING_VERTICAL → AWAITING_KEITARO
    → LOADING_HISTORY → AWAITING_VIDEOS → COMPLETED

Replaces n8n workflows:
    - BuyQncnHNb7ulL6z (Telegram Router)
    - hgTozRQFwh4GLM0z (Buyer Onboarding)
"""

import re
from datetime import timedelta
from typing import Optional, List
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import models and activities (pass-through for workflow sandbox)
with workflow.unsafe.imports_passed_through():
    from temporal.models.buyer import (
        OnboardingState,
        BuyerOnboardingInput,
        BuyerOnboardingResult,
        BuyerMessage,
        HistoricalImportInput,
        VALID_GEOS,
        VALID_VERTICALS,
        CreateBuyerInput,
    )
    from temporal.activities.buyer import (
        create_buyer,
        load_buyer_by_telegram_id,
        send_telegram_message,
        get_pending_video_campaigns,
        UpdateImportVideoInput,
        update_import_with_video,
    )


# Onboarding messages (Russian, friendly tone)
MESSAGES = {
    "welcome": (
        "👋 <b>Привет! Добро пожаловать в GenomAI</b>\n\n"
        "Давай настроим твой профиль.\n\n"
        "🏷️ <i>Как тебя зовут?</i>"
    ),
    "ask_geo": (
        "✨ Отлично, <b>{name}</b>!\n\n"
        "🗺️ С какими гео ты работаешь?\n"
        "Введи коды стран через запятую (например: US, UK, DE):\n\n"
        "<i>Доступные: US, UK, DE, FR, IT, ES, NL, AU, CA, BR, MX, IN, ID...</i>"
    ),
    "ask_vertical": (
        "🗺️ Гео: <b>{geos}</b>\n\n"
        "💊 Какие вертикали льёшь?\n"
        "Введи через запятую (например: потенция, простатит):\n\n"
        "<i>Доступные: потенция, простатит, цистит, грибок, давление, диабет, зрение, суставы, похудение</i>"
    ),
    "ask_keitaro": (
        "💊 Вертикали: <b>{verticals}</b>\n\n"
        "🔑 Последний шаг — укажи свой <b>sub10</b> из Keitaro.\n"
        "Это нужно для загрузки твоей истории.\n\n"
        "<i>Введи значение sub10 (например: 'moss', 'trubew'):</i>"
    ),
    "loading_history": (
        "⏳ <b>Настраиваю профиль...</b>\n\n"
        "📜 Загружаю твою историю из Keitaro.\n"
        "Это займёт пару минут.\n\n"
        "<i>sub10: {keitaro_source}</i>"
    ),
    "completed": (
        "🎉 <b>Готово!</b>\n\n"
        "🏷️ <b>Имя:</b> {name}\n"
        "🗺️ <b>Гео:</b> {geos}\n"
        "💊 <b>Вертикали:</b> {verticals}\n"
        "🔑 <b>sub10:</b> {keitaro_source}\n\n"
        "📊 Загружено <b>{campaigns_count}</b> кампаний.\n"
        "📹 Видео на анализе: <b>{videos_count}</b>\n\n"
        "🚀 <b>Теперь можешь:</b>\n"
        "• Кинуть URL видео для регистрации креатива\n"
        "• /stats — твоя статистика\n"
        "• /help — список команд"
    ),
    "timeout": (
        "⏰ Сессия истекла.\n\n"
        "Отправь /start чтобы начать заново."
    ),
    "invalid_geo": (
        "❌ Неверные коды стран.\n"
        "Примеры: US, UK, DE, FR, IT, ES\n\n"
        "<i>Попробуй ещё раз:</i>"
    ),
    "invalid_vertical": (
        "❌ Неверные вертикали.\n"
        "Примеры: потенция, простатит, цистит, грибок\n\n"
        "<i>Попробуй ещё раз:</i>"
    ),
    "ask_videos_intro": (
        "📹 <b>Загружено {total} кампаний без видео</b>\n\n"
        "Сейчас покажу каждую — скинь ссылку на креатив."
    ),
    "ask_campaign_video": (
        "{num}️⃣ <b>Кампания:</b> {name}\n"
        "🆔 ID: <code>{campaign_id}</code>\n"
        "📊 Клики: {clicks} | Конверсии: {conversions}\n\n"
        "<i>Скинь URL видео:</i>"
    ),
    "video_received": (
        "✅ Видео получено, запускаю анализ..."
    ),
    "no_campaigns": (
        "📭 Кампаний для привязки видео не найдено.\n"
        "Можешь скидывать видео позже через обычные сообщения."
    ),
    "invalid_video_url": (
        "❌ Не распознал ссылку на видео.\n"
        "Отправь URL (YouTube, .mp4 и т.д.)"
    ),
}

# Video URL patterns
VIDEO_URL_PATTERNS = [
    r"youtube\.com/watch",
    r"youtu\.be/",
    r"vimeo\.com/",
    r"drive\.google\.com/file",
    r"\.mp4",
    r"\.mov",
    r"\.webm",
    r"\.avi",
    r"/video",
]


def is_video_url(text: str) -> bool:
    """Check if text contains a video URL."""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in VIDEO_URL_PATTERNS)


@workflow.defn
class BuyerOnboardingWorkflow:
    """
    Buyer onboarding workflow with state machine.

    Guides user through registration steps via Telegram messages.
    Uses signals for user input and queries for state inspection.
    """

    def __init__(self):
        self._state = OnboardingState.AWAITING_NAME
        self._telegram_id: str = ""
        self._telegram_username: Optional[str] = None
        self._chat_id: str = ""
        self._buyer_id: Optional[str] = None

        # Collected data
        self._name: Optional[str] = None
        self._geos: List[str] = []
        self._verticals: List[str] = []
        self._keitaro_source: Optional[str] = None

        # Message queue for user input
        self._pending_message: Optional[BuyerMessage] = None
        self._campaigns_count: int = 0
        self._videos_count: int = 0
        self._error: Optional[str] = None

    @workflow.run
    async def run(self, input: BuyerOnboardingInput) -> BuyerOnboardingResult:
        """
        Execute the onboarding workflow.

        Args:
            input: BuyerOnboardingInput with telegram_id

        Returns:
            BuyerOnboardingResult with buyer_id and status
        """
        self._telegram_id = input.telegram_id
        self._telegram_username = input.telegram_username
        self._chat_id = input.chat_id or input.telegram_id

        # Default retry policy
        default_retry = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        # Step timeout (60 minutes per step)
        step_timeout = timedelta(minutes=60)

        try:
            # Check if buyer already exists
            existing_buyer = await workflow.execute_activity(
                load_buyer_by_telegram_id,
                self._telegram_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            if existing_buyer:
                # Buyer exists, return completed
                # Handle both dict and object responses
                if isinstance(existing_buyer, dict):
                    self._buyer_id = existing_buyer["id"]
                    self._name = existing_buyer.get("name")
                    self._geos = existing_buyer.get("geos") or []
                    self._verticals = existing_buyer.get("verticals") or []
                    self._keitaro_source = existing_buyer.get("keitaro_source")
                else:
                    self._buyer_id = existing_buyer.id
                    self._name = existing_buyer.name
                    self._geos = existing_buyer.geos or []
                    self._verticals = existing_buyer.verticals or []
                    self._keitaro_source = existing_buyer.keitaro_source
                self._state = OnboardingState.COMPLETED

                await workflow.execute_activity(
                    send_telegram_message,
                    args=[
                        self._chat_id,
                        f"Welcome back, <b>{self._name}</b>!\n\nYour account is already set up.",
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

                return self._build_result()

            # Step 1: Send welcome message and wait for name
            self._state = OnboardingState.AWAITING_NAME
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, MESSAGES["welcome"]],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Wait for name
            # Note: wait_condition may return None when signal arrives during wait,
            # so we check the actual _pending_message state instead of the return value
            await workflow.wait_condition(
                lambda: self._pending_message is not None,
                timeout=step_timeout,
            )

            if self._pending_message is None:
                # Genuine timeout - no message received
                return await self._handle_timeout()

            self._name = self._pending_message.text.strip()
            self._pending_message = None

            # Step 2: Ask for GEOs
            self._state = OnboardingState.AWAITING_GEO
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, MESSAGES["ask_geo"].format(name=self._name)],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Wait for valid GEOs
            while True:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )
                if self._pending_message is None:
                    return await self._handle_timeout()

                geos_input = (
                    self._pending_message.text.upper().replace(" ", "").split(",")
                )
                self._pending_message = None

                # Validate GEOs
                valid_geos = [g for g in geos_input if g in VALID_GEOS]
                if valid_geos:
                    self._geos = valid_geos
                    break

                # Invalid, ask again
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, MESSAGES["invalid_geo"]],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

            # Step 3: Ask for verticals
            self._state = OnboardingState.AWAITING_VERTICAL
            await workflow.execute_activity(
                send_telegram_message,
                args=[
                    self._chat_id,
                    MESSAGES["ask_vertical"].format(geos=", ".join(self._geos)),
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Wait for valid verticals
            while True:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )
                if self._pending_message is None:
                    return await self._handle_timeout()

                verticals_input = (
                    self._pending_message.text.lower().replace(" ", "").split(",")
                )
                self._pending_message = None

                # Validate verticals
                valid_verticals = [v for v in verticals_input if v in VALID_VERTICALS]
                if valid_verticals:
                    self._verticals = valid_verticals
                    break

                # Invalid, ask again
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, MESSAGES["invalid_vertical"]],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

            # Step 4: Ask for Keitaro source
            self._state = OnboardingState.AWAITING_KEITARO
            await workflow.execute_activity(
                send_telegram_message,
                args=[
                    self._chat_id,
                    MESSAGES["ask_keitaro"].format(
                        verticals=", ".join(self._verticals)
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Wait for Keitaro source
            await workflow.wait_condition(
                lambda: self._pending_message is not None,
                timeout=step_timeout,
            )
            if self._pending_message is None:
                return await self._handle_timeout()

            self._keitaro_source = self._pending_message.text.strip()
            self._pending_message = None

            # Step 5: Create buyer and load history
            self._state = OnboardingState.LOADING_HISTORY
            await workflow.execute_activity(
                send_telegram_message,
                args=[
                    self._chat_id,
                    MESSAGES["loading_history"].format(
                        keitaro_source=self._keitaro_source
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            # Create buyer record
            buyer = await workflow.execute_activity(
                create_buyer,
                CreateBuyerInput(
                    telegram_id=self._telegram_id,
                    telegram_username=self._telegram_username,
                    name=self._name,
                    geos=self._geos,
                    verticals=self._verticals,
                    keitaro_source=self._keitaro_source,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            self._buyer_id = buyer["id"] if isinstance(buyer, dict) else buyer.id

            # Start historical import as child workflow
            with workflow.unsafe.imports_passed_through():
                from temporal.workflows.historical_import import (
                    HistoricalImportWorkflow,
                )

            import_result = await workflow.execute_child_workflow(
                HistoricalImportWorkflow.run,
                HistoricalImportInput(
                    buyer_id=self._buyer_id,
                    keitaro_source=self._keitaro_source,
                ),
                id=f"historical-import-{self._buyer_id}",
                task_queue="telegram",
                execution_timeout=timedelta(hours=2),
            )

            self._campaigns_count = (
                import_result["total_campaigns"]
                if isinstance(import_result, dict)
                else import_result.total_campaigns
            )

            # Step 6: Ask for videos for each campaign
            # Get campaigns waiting for video
            pending_campaigns = await workflow.execute_activity(
                get_pending_video_campaigns,
                self._buyer_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            if pending_campaigns:
                self._state = OnboardingState.AWAITING_VIDEOS
                total_campaigns = len(pending_campaigns)

                # Send intro message
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[
                        self._chat_id,
                        MESSAGES["ask_videos_intro"].format(total=total_campaigns),
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

                # Import CreativeRegistrationWorkflow for video processing
                with workflow.unsafe.imports_passed_through():
                    from temporal.workflows.historical_import import (
                        CreativeRegistrationWorkflow,
                    )

                # Iterate through each campaign
                for i, campaign in enumerate(pending_campaigns, 1):
                    metrics = campaign.get("metrics", {})
                    campaign_name = metrics.get("name", f"Campaign {campaign['campaign_id']}")
                    clicks = metrics.get("clicks", 0)
                    conversions = metrics.get("conversions", 0)

                    # Ask for video for this campaign
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[
                            self._chat_id,
                            MESSAGES["ask_campaign_video"].format(
                                num=i,
                                name=campaign_name,
                                campaign_id=campaign["campaign_id"],
                                clicks=clicks,
                                conversions=conversions,
                            ),
                        ],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )

                    # Wait for valid video URL
                    while True:
                        await workflow.wait_condition(
                            lambda: self._pending_message is not None,
                            timeout=step_timeout,
                        )
                        if self._pending_message is None:
                            return await self._handle_timeout()

                        text = self._pending_message.text.strip()
                        self._pending_message = None

                        if is_video_url(text):
                            # Update import record with video URL
                            await workflow.execute_activity(
                                update_import_with_video,
                                UpdateImportVideoInput(
                                    import_id=campaign["id"],
                                    video_url=text,
                                    status="ready",
                                ),
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=default_retry,
                            )

                            # Start creative processing workflow
                            await workflow.start_child_workflow(
                                CreativeRegistrationWorkflow.run,
                                args=[self._buyer_id, text, campaign["campaign_id"], None],
                                id=f"onboarding-video-{self._buyer_id}-{campaign['campaign_id']}",
                                task_queue="telegram",
                            )

                            self._videos_count += 1

                            # Send confirmation
                            await workflow.execute_activity(
                                send_telegram_message,
                                args=[self._chat_id, MESSAGES["video_received"]],
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=default_retry,
                            )
                            break  # Move to next campaign
                        else:
                            # Invalid URL, ask again
                            await workflow.execute_activity(
                                send_telegram_message,
                                args=[self._chat_id, MESSAGES["invalid_video_url"]],
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=default_retry,
                            )
            else:
                # No campaigns to process
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, MESSAGES["no_campaigns"]],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )

            # Step 7: Completed
            self._state = OnboardingState.COMPLETED
            await workflow.execute_activity(
                send_telegram_message,
                args=[
                    self._chat_id,
                    MESSAGES["completed"].format(
                        name=self._name,
                        geos=", ".join(self._geos),
                        verticals=", ".join(self._verticals),
                        keitaro_source=self._keitaro_source,
                        campaigns_count=self._campaigns_count,
                        videos_count=self._videos_count,
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )

            return self._build_result()

        except Exception as e:
            self._error = str(e)
            self._state = OnboardingState.CANCELLED
            return self._build_result()

    async def _handle_timeout(self) -> BuyerOnboardingResult:
        """Handle step timeout."""
        self._state = OnboardingState.TIMED_OUT
        self._error = "Session timed out"

        await workflow.execute_activity(
            send_telegram_message,
            args=[self._chat_id, MESSAGES["timeout"]],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return self._build_result()

    def _build_result(self) -> BuyerOnboardingResult:
        """Build result object."""
        return BuyerOnboardingResult(
            buyer_id=self._buyer_id,
            state=self._state.value,
            completed=self._state == OnboardingState.COMPLETED,
            error=self._error,
            historical_import_started=self._state == OnboardingState.LOADING_HISTORY
            or self._state == OnboardingState.COMPLETED,
            campaigns_count=self._campaigns_count,
        )

    @workflow.signal
    async def user_message(self, message: BuyerMessage) -> None:
        """
        Signal handler for user messages.

        Called by Telegram webhook when user sends a message.

        Args:
            message: BuyerMessage with text and metadata
        """
        self._pending_message = message

    @workflow.signal
    async def cancel(self) -> None:
        """Cancel the onboarding workflow."""
        self._state = OnboardingState.CANCELLED

    @workflow.query
    def get_state(self) -> str:
        """Query current onboarding state."""
        return self._state.value

    @workflow.query
    def get_progress(self) -> dict:
        """Query workflow progress details."""
        return {
            "state": self._state.value,
            "telegram_id": self._telegram_id,
            "buyer_id": self._buyer_id,
            "name": self._name,
            "geos": self._geos,
            "verticals": self._verticals,
            "keitaro_source": self._keitaro_source,
            "campaigns_count": self._campaigns_count,
            "error": self._error,
        }
