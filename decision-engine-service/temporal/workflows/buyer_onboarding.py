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
from dataclasses import dataclass, field
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
        log_buyer_interaction,
        LogInteractionInput,
    )
    from temporal.activities.keitaro import (
        get_campaigns_by_source,
        GetCampaignsBySourceInput,
    )


# Maximum retry attempts for sub10 validation
MAX_SUB10_RETRY_ATTEMPTS = 3


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
    "timeout": ("⏰ Сессия истекла.\n\nОтправь /start чтобы начать заново."),
    "invalid_name": ("❌ Имя должно быть не менее 2 символов.\n\n<i>Попробуй ещё раз:</i>"),
    "invalid_geo": (
        "❌ Неверные коды стран.\nПримеры: US, UK, DE, FR, IT, ES\n\n<i>Попробуй ещё раз:</i>"
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
    "video_received": ("✅ Видео получено, запускаю анализ..."),
    "no_campaigns": (
        "📭 Кампаний для привязки видео не найдено.\n"
        "Можешь скидывать видео позже через обычные сообщения."
    ),
    "invalid_video_url": ("❌ Не распознал ссылку на видео.\nОтправь URL (YouTube, .mp4 и т.д.)"),
    "validating_sub10": ("🔍 Проверяю sub10 <code>{sub10}</code> в Keitaro..."),
    "sub10_found": (
        "✅ Найдено <b>{count}</b> кампаний с sub10='{sub10}'\n\nПродолжаю настройку..."
    ),
    "sub10_not_found": (
        "❌ Кампаний с sub10='{sub10}' не найдено.\n\n"
        "Проверь правильность написания и попробуй ещё раз.\n"
        "<i>Осталось попыток: {remaining}</i>"
    ),
    "sub10_retries_exhausted": (
        "❌ Исчерпаны попытки ввода sub10.\n\n"
        "Напиши в поддержку @genomai_support или отправь /start чтобы начать заново."
    ),
}

# Maximum input length for regex operations (ReDoS protection)
MAX_INPUT_LENGTH = 2048

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
    """
    Check if text contains a video URL.

    Includes input length limit to prevent ReDoS attacks.
    """
    if not text:
        return False
    # ReDoS protection: limit input length
    safe_text = text[:MAX_INPUT_LENGTH].lower()
    return any(re.search(pattern, safe_text) for pattern in VIDEO_URL_PATTERNS)


@dataclass(frozen=True)
class WorkflowStateSnapshot:
    """
    Immutable state snapshot for thread-safe query access.

    Signal handlers create new snapshot instances atomically.
    Query handlers read current snapshot without race conditions.
    frozen=True ensures immutability after creation.
    """

    state: str
    telegram_id: str = ""
    buyer_id: Optional[str] = None
    name: Optional[str] = None
    geos: tuple = field(default_factory=tuple)  # Immutable tuple instead of list
    verticals: tuple = field(default_factory=tuple)
    keitaro_source: Optional[str] = None
    campaigns_count: int = 0
    videos_count: int = 0
    error: Optional[str] = None
    pending_message_exists: bool = False


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

        # Message deduplication to prevent race conditions (fix #537)
        # Tracks last processed message_id to avoid reprocessing signals
        # that arrive after wait_condition timeout
        self._last_processed_message_id: Optional[int] = None

        # Immutable snapshot for thread-safe query access (fixes race condition #483)
        self._snapshot = WorkflowStateSnapshot(state=OnboardingState.AWAITING_NAME.value)

    def _update_snapshot(self) -> None:
        """
        Create new immutable snapshot atomically.

        This is the ONLY place where _snapshot is modified.
        Single assignment = atomic operation in Python.
        Query handlers read _snapshot safely without locks.
        """
        self._snapshot = WorkflowStateSnapshot(
            state=self._state.value,
            telegram_id=self._telegram_id,
            buyer_id=self._buyer_id,
            name=self._name,
            geos=tuple(self._geos),
            verticals=tuple(self._verticals),
            keitaro_source=self._keitaro_source,
            campaigns_count=self._campaigns_count,
            videos_count=self._videos_count,
            error=self._error,
            pending_message_exists=self._pending_message is not None,
        )

    def _set_state(self, new_state: OnboardingState) -> None:
        """
        Set workflow state with atomic snapshot update.

        All state transitions MUST go through this method
        to ensure query handlers see consistent state.
        """
        self._state = new_state
        self._update_snapshot()

    def _consume_message(self) -> Optional[str]:
        """
        Consume pending message with deduplication (fix #537).

        This method handles race conditions where a signal arrives
        after wait_condition timeout. It checks:
        1. If _pending_message is None → genuine timeout
        2. If message_id matches _last_processed_message_id → duplicate
        3. Otherwise → valid new message

        Returns:
            Message text if valid new message, None if timeout or duplicate.
            Caller should continue waiting loop if None is returned.
        """
        if self._pending_message is None:
            return None

        # Check for duplicate message (race condition protection)
        current_message_id = self._pending_message.message_id
        if current_message_id is not None and current_message_id == self._last_processed_message_id:
            # Duplicate message - signal arrived after timeout
            workflow.logger.info(
                f"Skipping duplicate message_id={current_message_id}, already processed"
            )
            self._pending_message = None
            self._update_snapshot()
            return None

        # Valid new message - extract text and update tracking
        message_text = self._pending_message.text
        if current_message_id is not None:
            self._last_processed_message_id = current_message_id

        self._pending_message = None
        self._update_snapshot()
        return message_text

    async def _log_outgoing(self, message: str, step: str) -> None:
        """Log outgoing bot message."""
        await workflow.execute_activity(
            log_buyer_interaction,
            LogInteractionInput(
                telegram_id=self._telegram_id,
                direction="out",
                message_type="bot",
                content=message,
                context={"step": step, "state": self._state.value},
                buyer_id=self._buyer_id,
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

    async def _log_incoming(self, message: str, step: str) -> None:
        """Log incoming user message."""
        await workflow.execute_activity(
            log_buyer_interaction,
            LogInteractionInput(
                telegram_id=self._telegram_id,
                direction="in",
                message_type="user",
                content=message,
                context={"step": step, "state": self._state.value},
                buyer_id=self._buyer_id,
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

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
                self._set_state(OnboardingState.COMPLETED)

                welcome_back_msg = (
                    f"Welcome back, <b>{self._name}</b>!\n\nYour account is already set up."
                )
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, welcome_back_msg],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                await self._log_outgoing(welcome_back_msg, "welcome_back")

                return self._build_result()

            # Step 1: Send welcome message and wait for name
            self._set_state(OnboardingState.AWAITING_NAME)
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, MESSAGES["welcome"]],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(MESSAGES["welcome"], "welcome")

            # Wait for valid name (min 2 characters)
            # Uses _consume_message() for race condition protection (fix #537)
            while True:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )

                msg_text = self._consume_message()
                if msg_text is None:
                    # Genuine timeout or duplicate message
                    if self._pending_message is None:
                        return await self._handle_timeout()
                    continue  # Duplicate, keep waiting

                name_input = msg_text.strip()
                await self._log_incoming(name_input, "name_input")

                # Validate name length (min 2 characters)
                if len(name_input) >= 2:
                    self._name = name_input
                    break

                # Invalid name, ask again
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, MESSAGES["invalid_name"]],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                await self._log_outgoing(MESSAGES["invalid_name"], "invalid_name")

            # Step 2: Ask for GEOs
            self._set_state(OnboardingState.AWAITING_GEO)
            ask_geo_msg = MESSAGES["ask_geo"].format(name=self._name)
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, ask_geo_msg],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(ask_geo_msg, "ask_geo")

            # Wait for valid GEOs (fix #537: race condition protection)
            while True:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )

                msg_text = self._consume_message()
                if msg_text is None:
                    if self._pending_message is None:
                        return await self._handle_timeout()
                    continue  # Duplicate, keep waiting

                await self._log_incoming(msg_text, "geo_input")
                # Filter empty strings after split (fix #534)
                geos_input = [g for g in msg_text.upper().replace(" ", "").split(",") if g]

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
                await self._log_outgoing(MESSAGES["invalid_geo"], "invalid_geo")

            # Step 3: Ask for verticals
            self._set_state(OnboardingState.AWAITING_VERTICAL)
            ask_vertical_msg = MESSAGES["ask_vertical"].format(geos=", ".join(self._geos))
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, ask_vertical_msg],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(ask_vertical_msg, "ask_vertical")

            # Wait for valid verticals (fix #537: race condition protection)
            while True:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )

                msg_text = self._consume_message()
                if msg_text is None:
                    if self._pending_message is None:
                        return await self._handle_timeout()
                    continue  # Duplicate, keep waiting

                await self._log_incoming(msg_text, "vertical_input")
                # Filter empty strings after split (fix #534)
                verticals_input = [v for v in msg_text.lower().replace(" ", "").split(",") if v]

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
                await self._log_outgoing(MESSAGES["invalid_vertical"], "invalid_vertical")

            # Step 4: Ask for Keitaro source with validation
            self._set_state(OnboardingState.AWAITING_KEITARO)
            ask_keitaro_msg = MESSAGES["ask_keitaro"].format(verticals=", ".join(self._verticals))
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, ask_keitaro_msg],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(ask_keitaro_msg, "ask_keitaro")

            # Wait for valid Keitaro source (with retry, fix #537)
            sub10_attempts = 0
            while sub10_attempts < MAX_SUB10_RETRY_ATTEMPTS:
                await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                )

                msg_text = self._consume_message()
                if msg_text is None:
                    if self._pending_message is None:
                        return await self._handle_timeout()
                    continue  # Duplicate, keep waiting

                sub10_input = msg_text.strip()
                await self._log_incoming(sub10_input, "sub10_input")

                # Validate sub10 by checking campaigns in Keitaro
                validating_msg = MESSAGES["validating_sub10"].format(sub10=sub10_input)
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, validating_msg],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                await self._log_outgoing(validating_msg, "validating_sub10")

                campaigns_result = await workflow.execute_activity(
                    get_campaigns_by_source,
                    GetCampaignsBySourceInput(source=sub10_input),
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=default_retry,
                )

                if campaigns_result.total > 0:
                    # Valid sub10 found
                    self._keitaro_source = sub10_input
                    sub10_found_msg = MESSAGES["sub10_found"].format(
                        count=campaigns_result.total,
                        sub10=sub10_input,
                    )
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[self._chat_id, sub10_found_msg],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )
                    await self._log_outgoing(sub10_found_msg, "sub10_found")
                    break

                # Invalid sub10, ask again
                sub10_attempts += 1
                remaining = MAX_SUB10_RETRY_ATTEMPTS - sub10_attempts

                if remaining > 0:
                    sub10_not_found_msg = MESSAGES["sub10_not_found"].format(
                        sub10=sub10_input,
                        remaining=remaining,
                    )
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[self._chat_id, sub10_not_found_msg],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )
                    await self._log_outgoing(sub10_not_found_msg, "sub10_not_found")
                else:
                    # Retries exhausted
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[self._chat_id, MESSAGES["sub10_retries_exhausted"]],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )
                    await self._log_outgoing(
                        MESSAGES["sub10_retries_exhausted"], "sub10_retries_exhausted"
                    )
                    self._error = "sub10 validation failed after max retries"
                    self._set_state(OnboardingState.CANCELLED)
                    return self._build_result()

            # Step 5: Create buyer and load history
            self._set_state(OnboardingState.LOADING_HISTORY)
            loading_msg = MESSAGES["loading_history"].format(keitaro_source=self._keitaro_source)
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, loading_msg],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(loading_msg, "loading_history")

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
                parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
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
                self._set_state(OnboardingState.AWAITING_VIDEOS)
                total_campaigns = len(pending_campaigns)

                # Send intro message
                ask_videos_intro_msg = MESSAGES["ask_videos_intro"].format(total=total_campaigns)
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, ask_videos_intro_msg],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                await self._log_outgoing(ask_videos_intro_msg, "ask_videos_intro")

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
                    ask_video_msg = MESSAGES["ask_campaign_video"].format(
                        num=i,
                        name=campaign_name,
                        campaign_id=campaign["campaign_id"],
                        clicks=clicks,
                        conversions=conversions,
                    )
                    await workflow.execute_activity(
                        send_telegram_message,
                        args=[self._chat_id, ask_video_msg],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=default_retry,
                    )
                    await self._log_outgoing(ask_video_msg, f"ask_campaign_video_{i}")

                    # Wait for valid video URL (fix #537: race condition protection)
                    while True:
                        await workflow.wait_condition(
                            lambda: self._pending_message is not None,
                            timeout=step_timeout,
                        )

                        msg_text = self._consume_message()
                        if msg_text is None:
                            if self._pending_message is None:
                                return await self._handle_timeout()
                            continue  # Duplicate, keep waiting

                        text = msg_text.strip()
                        await self._log_incoming(text, f"video_input_{i}")

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
                                args=[
                                    self._buyer_id,
                                    text,
                                    campaign["campaign_id"],
                                    None,
                                ],
                                id=f"onboarding-video-{self._buyer_id}-{campaign['campaign_id']}",
                                task_queue="telegram",
                                parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
                            )

                            self._videos_count += 1

                            # Send confirmation
                            await workflow.execute_activity(
                                send_telegram_message,
                                args=[self._chat_id, MESSAGES["video_received"]],
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=default_retry,
                            )
                            await self._log_outgoing(
                                MESSAGES["video_received"], f"video_received_{i}"
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
                            await self._log_outgoing(
                                MESSAGES["invalid_video_url"], f"invalid_video_url_{i}"
                            )
            else:
                # No campaigns to process
                await workflow.execute_activity(
                    send_telegram_message,
                    args=[self._chat_id, MESSAGES["no_campaigns"]],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=default_retry,
                )
                await self._log_outgoing(MESSAGES["no_campaigns"], "no_campaigns")

            # Step 7: Completed
            self._set_state(OnboardingState.COMPLETED)
            completed_msg = MESSAGES["completed"].format(
                name=self._name,
                geos=", ".join(self._geos),
                verticals=", ".join(self._verticals),
                keitaro_source=self._keitaro_source,
                campaigns_count=self._campaigns_count,
                videos_count=self._videos_count,
            )
            await workflow.execute_activity(
                send_telegram_message,
                args=[self._chat_id, completed_msg],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=default_retry,
            )
            await self._log_outgoing(completed_msg, "completed")

            return self._build_result()

        except Exception as e:
            self._error = str(e)
            self._set_state(OnboardingState.CANCELLED)
            return self._build_result()

    async def _handle_timeout(self) -> BuyerOnboardingResult:
        """Handle step timeout."""
        self._error = "Session timed out"
        self._set_state(OnboardingState.TIMED_OUT)

        await workflow.execute_activity(
            send_telegram_message,
            args=[self._chat_id, MESSAGES["timeout"]],
            start_to_close_timeout=timedelta(seconds=30),
        )
        await self._log_outgoing(MESSAGES["timeout"], "timeout")

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
        Updates snapshot atomically after state change.

        Args:
            message: BuyerMessage with text and metadata
        """
        # Security: validate telegram_id matches workflow owner
        if message.telegram_id != self._telegram_id:
            workflow.logger.warning(
                f"Ignoring message from wrong user: {message.telegram_id}, "
                f"expected: {self._telegram_id}"
            )
            return
        self._pending_message = message
        self._update_snapshot()  # Atomic snapshot update

    @workflow.signal
    async def cancel(self) -> None:
        """
        Cancel the onboarding workflow.

        Uses _set_state for atomic snapshot update.
        """
        self._set_state(OnboardingState.CANCELLED)

    @workflow.query
    def get_state(self) -> str:
        """
        Query current onboarding state.

        Reads from immutable snapshot for thread-safe access.
        No locks needed - snapshot is replaced atomically.
        """
        return self._snapshot.state

    @workflow.query
    def get_progress(self) -> dict:
        """
        Query workflow progress details.

        Reads from immutable snapshot for thread-safe access.
        Snapshot is frozen dataclass - no mutation possible.
        Lists converted to tuples in snapshot, converted back here.
        """
        snapshot = self._snapshot  # Single read - atomic
        return {
            "state": snapshot.state,
            "telegram_id": snapshot.telegram_id,
            "buyer_id": snapshot.buyer_id,
            "name": snapshot.name,
            "geos": list(snapshot.geos),  # Convert tuple back to list for API compat
            "verticals": list(snapshot.verticals),
            "keitaro_source": snapshot.keitaro_source,
            "campaigns_count": snapshot.campaigns_count,
            "error": snapshot.error,
        }
