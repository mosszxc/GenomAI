"""
Circuit Breaker for Keitaro API

Implements circuit breaker pattern to handle Keitaro API failures gracefully:
- CLOSED: Normal operation, requests pass through
- OPEN: After N consecutive failures, reject requests immediately
- HALF_OPEN: After recovery_timeout, allow one test request

State is persisted in Supabase config table for cross-restart persistence.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from temporalio import activity

from temporal.config import settings


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerState:
    """Circuit breaker state stored in Supabase"""

    state: CircuitState
    failure_count: int
    last_failure_at: Optional[datetime]
    last_success_at: Optional[datetime]
    opened_at: Optional[datetime]
    half_open_at: Optional[datetime]

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_at": (self.last_failure_at.isoformat() if self.last_failure_at else None),
            "last_success_at": (self.last_success_at.isoformat() if self.last_success_at else None),
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "half_open_at": (self.half_open_at.isoformat() if self.half_open_at else None),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitBreakerState":
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val)

        return cls(
            state=CircuitState(data.get("state", "closed")),
            failure_count=data.get("failure_count", 0),
            last_failure_at=parse_dt(data.get("last_failure_at")),
            last_success_at=parse_dt(data.get("last_success_at")),
            opened_at=parse_dt(data.get("opened_at")),
            half_open_at=parse_dt(data.get("half_open_at")),
        )

    @classmethod
    def default(cls) -> "CircuitBreakerState":
        return cls(
            state=CircuitState.CLOSED,
            failure_count=0,
            last_failure_at=None,
            last_success_at=None,
            opened_at=None,
            half_open_at=None,
        )


# Circuit breaker configuration
FAILURE_THRESHOLD = 3  # Number of consecutive failures before opening
RECOVERY_TIMEOUT_MINUTES = 5  # Time before attempting recovery (half-open)
CONFIG_KEY = "keitaro_circuit_breaker"


def _get_supabase_client():
    """Get Supabase client for circuit breaker state storage"""
    from supabase import create_client

    return create_client(settings.supabase.url, settings.supabase.service_role_key)


async def get_circuit_state() -> CircuitBreakerState:
    """
    Get current circuit breaker state from Supabase.

    Returns default (closed) state if no state exists.
    """
    try:
        client = _get_supabase_client()
        result = (
            client.schema("genomai")
            .table("config")
            .select("value")
            .eq("key", CONFIG_KEY)
            .maybe_single()
            .execute()
        )

        if result.data:
            return CircuitBreakerState.from_dict(result.data["value"])

        return CircuitBreakerState.default()
    except Exception:
        # On error, assume closed (fail-open for availability)
        return CircuitBreakerState.default()


async def save_circuit_state(state: CircuitBreakerState) -> None:
    """Save circuit breaker state to Supabase"""
    try:
        client = _get_supabase_client()
        client.schema("genomai").table("config").upsert(
            {"key": CONFIG_KEY, "value": state.to_dict()},
            on_conflict="key",
        ).execute()
    except Exception as e:
        # Log but don't fail - state will be recalculated on next run
        activity.logger.warning(f"Failed to save circuit breaker state: {e}")


async def record_success() -> CircuitBreakerState:
    """
    Record a successful Keitaro API call.

    Resets failure count and closes circuit if open.
    """
    state = await get_circuit_state()
    now = datetime.utcnow()

    state.failure_count = 0
    state.last_success_at = now
    state.state = CircuitState.CLOSED
    state.half_open_at = None

    await save_circuit_state(state)
    return state


async def record_failure(error_message: str = "") -> CircuitBreakerState:
    """
    Record a failed Keitaro API call.

    Increments failure count and opens circuit if threshold reached.
    """
    state = await get_circuit_state()
    now = datetime.utcnow()

    state.failure_count += 1
    state.last_failure_at = now

    if state.failure_count >= FAILURE_THRESHOLD:
        if state.state != CircuitState.OPEN:
            state.state = CircuitState.OPEN
            state.opened_at = now
            activity.logger.warning(
                f"Circuit breaker OPENED after {state.failure_count} failures. "
                f"Last error: {error_message}"
            )

    await save_circuit_state(state)
    return state


async def should_allow_request() -> tuple[bool, CircuitBreakerState]:
    """
    Check if request should be allowed based on circuit state.

    Returns:
        (allow, state) - whether to allow request and current state
    """
    state = await get_circuit_state()
    now = datetime.utcnow()

    if state.state == CircuitState.CLOSED:
        return True, state

    if state.state == CircuitState.OPEN:
        # Check if recovery timeout has passed
        if state.opened_at:
            recovery_time = state.opened_at + timedelta(minutes=RECOVERY_TIMEOUT_MINUTES)
            if now >= recovery_time:
                # Transition to half-open, allow one test request
                state.state = CircuitState.HALF_OPEN
                state.half_open_at = now
                await save_circuit_state(state)
                activity.logger.info("Circuit breaker transitioning to HALF_OPEN for test request")
                return True, state

        return False, state

    if state.state == CircuitState.HALF_OPEN:
        # In half-open, allow the request (it's a test)
        return True, state

    return True, state


async def get_metrics_staleness() -> dict:
    """
    Get metrics staleness information for health check.

    Returns:
        dict with staleness info and circuit breaker state
    """
    try:
        client = _get_supabase_client()

        # Get latest metrics timestamp
        result = (
            client.schema("genomai")
            .table("raw_metrics_current")
            .select("updated_at")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        cb_state = await get_circuit_state()
        now = datetime.utcnow()

        if result.data:
            latest_update = datetime.fromisoformat(
                result.data[0]["updated_at"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
            staleness_minutes = (now - latest_update).total_seconds() / 60
            is_stale = staleness_minutes > 30
        else:
            staleness_minutes = None
            is_stale = True

        return {
            "metrics_staleness_minutes": staleness_minutes,
            "is_stale": is_stale,
            "stale_threshold_minutes": 30,
            "circuit_breaker": {
                "state": cb_state.state.value,
                "failure_count": cb_state.failure_count,
                "last_failure_at": (
                    cb_state.last_failure_at.isoformat() if cb_state.last_failure_at else None
                ),
                "last_success_at": (
                    cb_state.last_success_at.isoformat() if cb_state.last_success_at else None
                ),
            },
            "status": "degraded"
            if (is_stale or cb_state.state != CircuitState.CLOSED)
            else "healthy",
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
        }


# Activities for Temporal workflow integration


@dataclass
class CheckCircuitInput:
    """Input for check_circuit activity"""

    pass


@dataclass
class CheckCircuitOutput:
    """Output from check_circuit activity"""

    allow_request: bool
    state: str
    failure_count: int
    is_degraded: bool


@activity.defn
async def check_circuit(input: CheckCircuitInput) -> CheckCircuitOutput:
    """
    Temporal activity to check circuit breaker state.

    Use this at the start of KeitaroPollerWorkflow to decide
    whether to proceed with API calls or use cached data.
    """
    allow, state = await should_allow_request()

    return CheckCircuitOutput(
        allow_request=allow,
        state=state.state.value,
        failure_count=state.failure_count,
        is_degraded=state.state != CircuitState.CLOSED,
    )


@dataclass
class RecordOutcomeInput:
    """Input for record_outcome activity"""

    success: bool
    error_message: str = ""


@dataclass
class RecordOutcomeOutput:
    """Output from record_outcome activity"""

    state: str
    failure_count: int


@activity.defn
async def record_circuit_outcome(input: RecordOutcomeInput) -> RecordOutcomeOutput:
    """
    Temporal activity to record API call outcome.

    Call this after Keitaro API calls to update circuit breaker state.
    """
    if input.success:
        state = await record_success()
    else:
        state = await record_failure(input.error_message)

    return RecordOutcomeOutput(
        state=state.state.value,
        failure_count=state.failure_count,
    )
