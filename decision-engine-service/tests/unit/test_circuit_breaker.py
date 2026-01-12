"""
Tests for circuit_breaker.py (Issue #474)

Tests circuit breaker state transitions and graceful degradation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from temporal.circuit_breaker import (
    CircuitState,
    CircuitBreakerState,
    FAILURE_THRESHOLD,
    RECOVERY_TIMEOUT_MINUTES,
    record_success,
    record_failure,
    should_allow_request,
    get_metrics_staleness,
)


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState dataclass"""

    def test_default_state_is_closed(self):
        """Default state should be CLOSED"""
        state = CircuitBreakerState.default()
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.last_failure_at is None
        assert state.last_success_at is None

    def test_to_dict_serialization(self):
        """State should serialize to dict correctly"""
        now = datetime.utcnow()
        state = CircuitBreakerState(
            state=CircuitState.OPEN,
            failure_count=3,
            last_failure_at=now,
            last_success_at=None,
            opened_at=now,
            half_open_at=None,
        )
        data = state.to_dict()

        assert data["state"] == "open"
        assert data["failure_count"] == 3
        assert data["last_failure_at"] == now.isoformat()
        assert data["opened_at"] == now.isoformat()
        assert data["last_success_at"] is None

    def test_from_dict_deserialization(self):
        """State should deserialize from dict correctly"""
        now = datetime.utcnow()
        data = {
            "state": "open",
            "failure_count": 5,
            "last_failure_at": now.isoformat(),
            "last_success_at": None,
            "opened_at": now.isoformat(),
            "half_open_at": None,
        }
        state = CircuitBreakerState.from_dict(data)

        assert state.state == CircuitState.OPEN
        assert state.failure_count == 5
        assert state.last_failure_at is not None
        assert state.last_success_at is None

    def test_from_dict_with_missing_fields(self):
        """Should handle missing fields with defaults"""
        data = {}
        state = CircuitBreakerState.from_dict(data)

        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0


class TestCircuitBreakerTransitions:
    """Tests for circuit breaker state transitions"""

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Recording success should reset failure count"""
        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": 2}}
        )
        mock_client.schema.return_value.table.return_value.upsert.return_value.execute.return_value = None

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            state = await record_success()

        assert state.failure_count == 0
        assert state.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_increments_count(self):
        """Recording failure should increment failure count"""
        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": 0}}
        )
        mock_client.schema.return_value.table.return_value.upsert.return_value.execute.return_value = None

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            state = await record_failure("Test error")

        assert state.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Circuit should open after FAILURE_THRESHOLD failures"""
        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": FAILURE_THRESHOLD - 1}}
        )
        mock_client.schema.return_value.table.return_value.upsert.return_value.execute.return_value = None

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            state = await record_failure("Final error")

        assert state.failure_count == FAILURE_THRESHOLD
        assert state.state == CircuitState.OPEN
        assert state.opened_at is not None


class TestCircuitBreakerRequests:
    """Tests for request allowance logic"""

    @pytest.mark.asyncio
    async def test_closed_circuit_allows_requests(self):
        """CLOSED circuit should allow requests"""
        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": 0}}
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            allow, state = await should_allow_request()

        assert allow is True
        assert state.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_requests(self):
        """OPEN circuit should block requests before recovery timeout"""
        now = datetime.utcnow()
        opened_at = now - timedelta(minutes=1)  # Opened 1 minute ago

        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "value": {
                    "state": "open",
                    "failure_count": 3,
                    "opened_at": opened_at.isoformat(),
                }
            }
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            allow, state = await should_allow_request()

        assert allow is False
        assert state.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_transitions_to_half_open_after_timeout(self):
        """OPEN circuit should transition to HALF_OPEN after recovery timeout"""
        now = datetime.utcnow()
        # Opened more than RECOVERY_TIMEOUT_MINUTES ago
        opened_at = now - timedelta(minutes=RECOVERY_TIMEOUT_MINUTES + 1)

        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "value": {
                    "state": "open",
                    "failure_count": 3,
                    "opened_at": opened_at.isoformat(),
                }
            }
        )
        mock_client.schema.return_value.table.return_value.upsert.return_value.execute.return_value = None

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            allow, state = await should_allow_request()

        assert allow is True
        assert state.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_allows_test_request(self):
        """HALF_OPEN circuit should allow test request"""
        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "value": {
                    "state": "half_open",
                    "failure_count": 3,
                }
            }
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            allow, state = await should_allow_request()

        assert allow is True
        assert state.state == CircuitState.HALF_OPEN


class TestMetricsStaleness:
    """Tests for metrics staleness check"""

    @pytest.mark.asyncio
    async def test_fresh_metrics_healthy_status(self):
        """Fresh metrics with closed circuit should be healthy"""
        now = datetime.utcnow()
        recent_update = now - timedelta(minutes=5)

        mock_client = MagicMock()
        # For raw_metrics_current query
        mock_client.schema.return_value.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"updated_at": recent_update.isoformat()}]
        )
        # For circuit breaker state query
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": 0}}
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            result = await get_metrics_staleness()

        assert result["status"] == "healthy"
        assert result["is_stale"] is False
        assert result["circuit_breaker"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_stale_metrics_degraded_status(self):
        """Stale metrics (>30 min) should be degraded"""
        now = datetime.utcnow()
        old_update = now - timedelta(minutes=45)

        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"updated_at": old_update.isoformat()}]
        )
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"value": {"state": "closed", "failure_count": 0}}
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            result = await get_metrics_staleness()

        assert result["status"] == "degraded"
        assert result["is_stale"] is True

    @pytest.mark.asyncio
    async def test_open_circuit_degraded_status(self):
        """Open circuit should result in degraded status"""
        now = datetime.utcnow()
        recent_update = now - timedelta(minutes=5)

        mock_client = MagicMock()
        mock_client.schema.return_value.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"updated_at": recent_update.isoformat()}]
        )
        mock_client.schema.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "value": {
                    "state": "open",
                    "failure_count": 3,
                    "opened_at": now.isoformat(),
                }
            }
        )

        with patch(
            "temporal.circuit_breaker._get_supabase_client",
            return_value=mock_client,
        ):
            result = await get_metrics_staleness()

        assert result["status"] == "degraded"
        assert result["circuit_breaker"]["state"] == "open"


class TestConstants:
    """Tests for circuit breaker configuration"""

    def test_failure_threshold_is_reasonable(self):
        """FAILURE_THRESHOLD should be 3"""
        assert FAILURE_THRESHOLD == 3

    def test_recovery_timeout_is_reasonable(self):
        """RECOVERY_TIMEOUT_MINUTES should be 5"""
        assert RECOVERY_TIMEOUT_MINUTES == 5
