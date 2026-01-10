"""
Buyer Onboarding Workflow

Multi-step Telegram-based buyer registration workflow.
Uses Temporal signals for user input and state machine for flow control.

States:
    AWAITING_NAME → AWAITING_GEO → AWAITING_VERTICAL → AWAITING_KEITARO → LOADING_HISTORY → COMPLETED

Replaces n8n workflows:
    - BuyQncnHNb7ulL6z (Telegram Router)
    - hgTozRQFwh4GLM0z (Buyer Onboarding)
"""

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
    )


# Onboarding messages
MESSAGES = {
    "welcome": (
        "<b>Welcome to GenomAI!</b>\n\n"
        "I'll help you set up your account. Let's start with your name.\n\n"
        "<i>Please enter your name or company name:</i>"
    ),
    "ask_geo": (
        "Great, <b>{name}</b>!\n\n"
        "Now, which GEOs do you work with?\n"
        "Enter comma-separated country codes (e.g., US, UK, DE):\n\n"
        "<i>Available: US, UK, DE, FR, IT, ES, NL, AU, CA, BR, MX, IN, ID, etc.</i>"
    ),
    "ask_vertical": (
        "GEOs saved: <b>{geos}</b>\n\n"
        "What verticals do you work in?\n"
        "Enter comma-separated (e.g., gambling, nutra, crypto):\n\n"
        "<i>Available: gambling, nutra, crypto, dating, ecommerce, finance, gaming, sweepstakes</i>"
    ),
    "ask_keitaro": (
        "Verticals saved: <b>{verticals}</b>\n\n"
        "Finally, what's your Keitaro source/affiliate parameter?\n"
        "This is used to load your historical campaigns.\n\n"
        "<i>Enter your source identifier (e.g., 'buyer_john', 'affiliate_123'):</i>"
    ),
    "loading_history": (
        "Setting up your account...\n\n"
        "Loading your historical campaigns from Keitaro.\n"
        "This may take a few minutes.\n\n"
        "<i>Source: {keitaro_source}</i>"
    ),
    "completed": (
        "Your account is ready!\n\n"
        "<b>Name:</b> {name}\n"
        "<b>GEOs:</b> {geos}\n"
        "<b>Verticals:</b> {verticals}\n"
        "<b>Keitaro Source:</b> {keitaro_source}\n\n"
        "Loaded <b>{campaigns_count}</b> historical campaigns.\n\n"
        "You can now:\n"
        "- Send video URLs to register new creatives\n"
        "- Use /stats to view your performance\n"
        "- Use /help for more commands"
    ),
    "timeout": ("Session timed out due to inactivity.\n\nSend /start to begin again."),
    "invalid_geo": (
        "Invalid GEO codes. Please use valid country codes.\n"
        "Examples: US, UK, DE, FR, IT, ES\n\n"
        "<i>Try again:</i>"
    ),
    "invalid_vertical": (
        "Invalid verticals. Please use valid vertical names.\n"
        "Examples: gambling, nutra, crypto, dating\n\n"
        "<i>Try again:</i>"
    ),
}


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
            workflow.logger.info(
                f"Waiting for user input with timeout: {step_timeout.total_seconds()} seconds"
            )
            workflow.logger.info(f"_pending_message before wait: {self._pending_message}")

            condition_result = await workflow.wait_condition(
                lambda: self._pending_message is not None,
                timeout=step_timeout,
            )

            workflow.logger.info(f"wait_condition returned: {condition_result}")
            workflow.logger.info(f"_pending_message after wait: {self._pending_message}")

            if not condition_result:
                workflow.logger.warning("wait_condition timed out unexpectedly!")
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
                if not await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                ):
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
                if not await workflow.wait_condition(
                    lambda: self._pending_message is not None,
                    timeout=step_timeout,
                ):
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
            if not await workflow.wait_condition(
                lambda: self._pending_message is not None,
                timeout=step_timeout,
            ):
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

            # Step 6: Completed
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
