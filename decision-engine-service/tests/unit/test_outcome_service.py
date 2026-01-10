"""
Unit tests for OutcomeService

Tests window ID calculation, CPA calculation, and edge cases.
"""
import pytest
from datetime import date
from decimal import Decimal

from src.services.outcome_service import OutcomeService, OutcomeAggregate, AggregateResult


class TestWindowIdCalculation:
    """Tests for window ID calculation logic"""

    def test_d1_same_day(self):
        """Window ID should be D1 for same day"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 1)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D1"

    def test_d1_next_day(self):
        """Window ID should be D1 for 1 day difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 2)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D1"

    def test_d3_two_days(self):
        """Window ID should be D3 for 2 days difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 3)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D3"

    def test_d3_three_days(self):
        """Window ID should be D3 for 3 days difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 4)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D3"

    def test_d7_four_days(self):
        """Window ID should be D7 for 4 days difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 5)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D7"

    def test_d7_seven_days(self):
        """Window ID should be D7 for 7 days difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 8)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D7"

    def test_d7_plus_eight_days(self):
        """Window ID should be D7+ for 8+ days difference"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 1, 9)

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D7+"

    def test_d7_plus_long_period(self):
        """Window ID should be D7+ for very long period"""
        decision_date = date(2025, 1, 1)
        snapshot_date = date(2025, 6, 1)  # ~150 days later

        result = OutcomeService.calculate_window_id(decision_date, snapshot_date)

        assert result == "D7+"


class TestTrendCalculation:
    """Tests for trend calculation logic"""

    def test_trend_improving(self):
        """Trend should be 'improving' when CPA decreases by >10%"""
        current_cpa = Decimal("8.00")
        previous_cpa = Decimal("10.00")  # -20% change

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "improving"

    def test_trend_declining(self):
        """Trend should be 'declining' when CPA increases by >10%"""
        current_cpa = Decimal("12.00")
        previous_cpa = Decimal("10.00")  # +20% change

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "declining"

    def test_trend_stable(self):
        """Trend should be 'stable' when CPA change is within 10%"""
        current_cpa = Decimal("10.50")
        previous_cpa = Decimal("10.00")  # +5% change

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "stable"

    def test_trend_stable_slight_decrease(self):
        """Trend should be 'stable' for slight decrease within 10%"""
        current_cpa = Decimal("9.50")
        previous_cpa = Decimal("10.00")  # -5% change

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "stable"

    def test_trend_none_when_current_cpa_none(self):
        """Trend should be None when current CPA is None"""
        current_cpa = None
        previous_cpa = Decimal("10.00")

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result is None

    def test_trend_none_when_previous_cpa_none(self):
        """Trend should be None when previous CPA is None"""
        current_cpa = Decimal("10.00")
        previous_cpa = None

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result is None

    def test_trend_none_when_both_cpa_none(self):
        """Trend should be None when both CPAs are None"""
        result = OutcomeService.calculate_trend(None, None)

        assert result is None

    def test_trend_none_when_previous_cpa_zero(self):
        """Trend should be None when previous CPA is zero (avoid division)"""
        current_cpa = Decimal("10.00")
        previous_cpa = Decimal("0")

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result is None

    def test_trend_boundary_improving(self):
        """Test exact -10% boundary for improving"""
        previous_cpa = Decimal("100.00")
        current_cpa = Decimal("89.00")  # -11% = improving

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "improving"

    def test_trend_boundary_declining(self):
        """Test exact +10% boundary for declining"""
        previous_cpa = Decimal("100.00")
        current_cpa = Decimal("111.00")  # +11% = declining

        result = OutcomeService.calculate_trend(current_cpa, previous_cpa)

        assert result == "declining"


class TestCpaCalculation:
    """Tests for CPA calculation logic"""

    def test_cpa_normal(self):
        """CPA should be spend/conversions"""
        spend = Decimal("100.00")
        conversions = 10

        result = OutcomeService.calculate_cpa(spend, conversions)

        assert result == Decimal("10.00")

    def test_cpa_fractional(self):
        """CPA should handle fractional results"""
        spend = Decimal("100.00")
        conversions = 3

        result = OutcomeService.calculate_cpa(spend, conversions)

        assert result == Decimal("100.00") / Decimal("3")

    def test_cpa_zero_conversions(self):
        """CPA should be None when conversions is 0"""
        spend = Decimal("100.00")
        conversions = 0

        result = OutcomeService.calculate_cpa(spend, conversions)

        assert result is None

    def test_cpa_zero_spend(self):
        """CPA should be 0 when spend is 0"""
        spend = Decimal("0.00")
        conversions = 10

        result = OutcomeService.calculate_cpa(spend, conversions)

        assert result == Decimal("0.00")

    def test_cpa_high_precision(self):
        """CPA should maintain precision"""
        spend = Decimal("99.99")
        conversions = 7

        result = OutcomeService.calculate_cpa(spend, conversions)

        assert result == Decimal("99.99") / Decimal("7")


class TestOutcomeAggregate:
    """Tests for OutcomeAggregate dataclass"""

    def test_to_dict_complete(self):
        """to_dict should return all fields"""
        outcome = OutcomeAggregate(
            id="test-id",
            creative_id="creative-123",
            decision_id="decision-456",
            window_id="D3",
            window_start=date(2025, 1, 1),
            window_end=date(2025, 1, 4),
            conversions=10,
            spend=Decimal("50.00"),
            cpa=Decimal("5.00"),
            trend="improving",
            origin_type="system",
            learning_applied=False
        )

        result = outcome.to_dict()

        assert result["id"] == "test-id"
        assert result["creative_id"] == "creative-123"
        assert result["decision_id"] == "decision-456"
        assert result["window_id"] == "D3"
        assert result["window_start"] == "2025-01-01"
        assert result["window_end"] == "2025-01-04"
        assert result["conversions"] == 10
        assert result["spend"] == 50.0
        assert result["cpa"] == 5.0
        assert result["trend"] == "improving"
        assert result["origin_type"] == "system"
        assert result["learning_applied"] is False

    def test_to_dict_null_cpa(self):
        """to_dict should handle null CPA"""
        outcome = OutcomeAggregate(
            creative_id="creative-123",
            decision_id="decision-456",
            window_id="D1",
            window_start=date(2025, 1, 1),
            window_end=date(2025, 1, 1),
            conversions=0,
            spend=Decimal("50.00"),
            cpa=None
        )

        result = outcome.to_dict()

        assert result["cpa"] is None
        assert result["conversions"] == 0

    def test_to_dict_defaults(self):
        """to_dict should handle default values"""
        outcome = OutcomeAggregate()

        result = outcome.to_dict()

        assert result["id"] is None
        assert result["creative_id"] == ""
        assert result["conversions"] == 0
        assert result["spend"] == 0
        assert result["origin_type"] == "system"
        assert result["learning_applied"] is False


class TestAggregateResult:
    """Tests for AggregateResult dataclass"""

    def test_success_result(self):
        """AggregateResult success should have outcome"""
        outcome = OutcomeAggregate(
            id="test-id",
            creative_id="creative-123",
            decision_id="decision-456",
            window_id="D3"
        )

        result = AggregateResult(
            success=True,
            outcome=outcome,
            learning_triggered=True
        )

        assert result.success is True
        assert result.outcome is not None
        assert result.outcome.id == "test-id"
        assert result.learning_triggered is True
        assert result.error_code is None
        assert result.error_message is None

    def test_failure_result(self):
        """AggregateResult failure should have error"""
        result = AggregateResult(
            success=False,
            error_code="SNAPSHOT_NOT_FOUND",
            error_message="Snapshot abc123 not found"
        )

        assert result.success is False
        assert result.outcome is None
        assert result.learning_triggered is False
        assert result.error_code == "SNAPSHOT_NOT_FOUND"
        assert result.error_message == "Snapshot abc123 not found"


class TestWindowIdBoundaries:
    """Edge case tests for window ID boundaries"""

    def test_boundary_d1_to_d3(self):
        """Test exact boundary between D1 and D3 (2 days)"""
        decision_date = date(2025, 1, 1)

        # 1 day = D1
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 2)) == "D1"

        # 2 days = D3
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 3)) == "D3"

    def test_boundary_d3_to_d7(self):
        """Test exact boundary between D3 and D7 (4 days)"""
        decision_date = date(2025, 1, 1)

        # 3 days = D3
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 4)) == "D3"

        # 4 days = D7
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 5)) == "D7"

    def test_boundary_d7_to_d7_plus(self):
        """Test exact boundary between D7 and D7+ (8 days)"""
        decision_date = date(2025, 1, 1)

        # 7 days = D7
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 8)) == "D7"

        # 8 days = D7+
        assert OutcomeService.calculate_window_id(decision_date, date(2025, 1, 9)) == "D7+"


class TestWindowIdAllValues:
    """Test all possible window ID values"""

    def test_all_window_ids_reachable(self):
        """Verify all window IDs (D1, D3, D7, D7+) can be produced"""
        decision_date = date(2025, 1, 1)

        window_ids = set()

        # Test 0-30 days range
        for days in range(31):
            snapshot_date = date(2025, 1, 1 + days)
            if snapshot_date.month == 1:  # Stay in January
                window_id = OutcomeService.calculate_window_id(decision_date, snapshot_date)
                window_ids.add(window_id)

        assert window_ids == {"D1", "D3", "D7", "D7+"}
