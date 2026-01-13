"""
Unit tests for dashboard service

Issue: #602
"""

from src.services.dashboard_service import (
    classify_components,
    _calculate_win_rate,
    _calculate_cpa,
    _classify_fatigue,
    _estimate_trend,
    MIN_SAMPLE_SIZE_HOT,
    MIN_WIN_RATE_HOT,
    MAX_WIN_RATE_COLD,
    MAX_SAMPLE_SIZE_GAP,
)


class TestCalculateWinRate:
    """Tests for _calculate_win_rate function"""

    def test_normal_calculation(self):
        """Standard win rate calculation"""
        assert _calculate_win_rate(5, 10) == 0.5
        assert _calculate_win_rate(3, 10) == 0.3

    def test_zero_sample_size(self):
        """Zero sample size returns 0.0"""
        assert _calculate_win_rate(0, 0) == 0.0

    def test_all_wins(self):
        """All wins returns 1.0"""
        assert _calculate_win_rate(10, 10) == 1.0

    def test_no_wins(self):
        """No wins returns 0.0"""
        assert _calculate_win_rate(0, 10) == 0.0


class TestCalculateCpa:
    """Tests for _calculate_cpa function"""

    def test_normal_calculation(self):
        """Standard CPA calculation"""
        assert _calculate_cpa(100.0, 10) == 10.0
        assert _calculate_cpa(50.0, 5) == 10.0

    def test_zero_wins(self):
        """Zero wins returns None"""
        assert _calculate_cpa(100.0, 0) is None

    def test_zero_spend(self):
        """Zero spend with wins returns 0.0"""
        assert _calculate_cpa(0.0, 10) == 0.0


class TestClassifyFatigue:
    """Tests for _classify_fatigue function"""

    def test_low_sample_size(self):
        """Low sample size returns LOW fatigue"""
        assert _classify_fatigue(0.05, 3) == "LOW"

    def test_high_fatigue(self):
        """Very low win rate with sufficient samples returns HIGH"""
        assert _classify_fatigue(0.05, 20) == "HIGH"

    def test_medium_fatigue(self):
        """Medium win rate with sufficient samples returns MEDIUM"""
        assert _classify_fatigue(0.15, 20) == "MEDIUM"

    def test_low_fatigue(self):
        """Good win rate returns LOW"""
        assert _classify_fatigue(0.25, 20) == "LOW"


class TestEstimateTrend:
    """Tests for _estimate_trend function"""

    def test_positive_trend(self):
        """High win rate gives positive trend"""
        trend = _estimate_trend(0.4, 20)
        assert trend > 0

    def test_negative_trend(self):
        """Low win rate gives negative trend"""
        trend = _estimate_trend(0.1, 20)
        assert trend < 0

    def test_baseline_trend(self):
        """Baseline win rate gives near-zero trend"""
        trend = _estimate_trend(0.25, 20)
        assert abs(trend) < 0.01

    def test_low_confidence_reduces_trend(self):
        """Low sample size reduces trend magnitude"""
        trend_high_confidence = _estimate_trend(0.5, 30)
        trend_low_confidence = _estimate_trend(0.5, 5)
        assert abs(trend_high_confidence) > abs(trend_low_confidence)


class TestClassifyComponents:
    """Tests for classify_components function"""

    def test_empty_learnings(self):
        """Empty learnings returns empty lists"""
        hot, cold, gaps = classify_components([])
        assert hot == []
        assert cold == []
        assert gaps == []

    def test_hot_classification(self):
        """High win rate with sufficient samples is HOT"""
        learnings = [
            {
                "component_type": "hook_mechanism",
                "component_value": "confession",
                "sample_size": 20,
                "win_count": 10,  # 50% win rate
                "loss_count": 10,
                "total_spend": 100,
            }
        ]
        hot, cold, gaps = classify_components(learnings)

        assert len(hot) == 1
        assert hot[0].variable == "hook_mechanism"
        assert hot[0].value == "confession"
        assert hot[0].win_rate == 0.5
        assert len(cold) == 0
        assert len(gaps) == 0

    def test_cold_classification(self):
        """Low win rate with sufficient samples is COLD"""
        learnings = [
            {
                "component_type": "angle_type",
                "component_value": "fear",
                "sample_size": 20,
                "win_count": 2,  # 10% win rate
                "loss_count": 18,
                "total_spend": 200,
            }
        ]
        hot, cold, gaps = classify_components(learnings)

        assert len(hot) == 0
        assert len(cold) == 1
        assert cold[0].variable == "angle_type"
        assert cold[0].value == "fear"
        assert cold[0].fatigue in ["HIGH", "MEDIUM"]
        assert len(gaps) == 0

    def test_gap_classification(self):
        """Low sample size is GAP"""
        learnings = [
            {
                "component_type": "ump_type",
                "component_value": "new_technology",
                "sample_size": 3,
                "win_count": 1,
                "loss_count": 2,
                "total_spend": 30,
            }
        ]
        hot, cold, gaps = classify_components(learnings)

        assert len(hot) == 0
        assert len(cold) == 0
        assert len(gaps) == 1
        assert gaps[0].variable == "ump_type"
        assert gaps[0].value == "new_technology"
        assert gaps[0].sample_size == 3

    def test_mixed_classification(self):
        """Mixed components are classified correctly"""
        learnings = [
            # HOT
            {
                "component_type": "hook_mechanism",
                "component_value": "confession",
                "sample_size": 25,
                "win_count": 12,
                "loss_count": 13,
                "total_spend": 100,
            },
            # COLD
            {
                "component_type": "angle_type",
                "component_value": "fear",
                "sample_size": 15,
                "win_count": 1,
                "loss_count": 14,
                "total_spend": 150,
            },
            # GAP
            {
                "component_type": "ump_type",
                "component_value": "new_tech",
                "sample_size": 2,
                "win_count": 1,
                "loss_count": 1,
                "total_spend": 20,
            },
        ]
        hot, cold, gaps = classify_components(learnings)

        assert len(hot) == 1
        assert len(cold) == 1
        assert len(gaps) == 1

    def test_sorting_hot_by_win_rate(self):
        """HOT components are sorted by win rate descending"""
        learnings = [
            {
                "component_type": "a",
                "component_value": "v1",
                "sample_size": 20,
                "win_count": 8,  # 40%
                "loss_count": 12,
                "total_spend": 100,
            },
            {
                "component_type": "b",
                "component_value": "v2",
                "sample_size": 20,
                "win_count": 16,  # 80%
                "loss_count": 4,
                "total_spend": 100,
            },
        ]
        hot, _, _ = classify_components(learnings)

        assert len(hot) == 2
        assert hot[0].win_rate > hot[1].win_rate

    def test_sorting_gaps_by_sample_size(self):
        """GAP components are sorted by sample size ascending"""
        learnings = [
            {
                "component_type": "a",
                "component_value": "v1",
                "sample_size": 4,
                "win_count": 2,
                "loss_count": 2,
                "total_spend": 40,
            },
            {
                "component_type": "b",
                "component_value": "v2",
                "sample_size": 1,
                "win_count": 0,
                "loss_count": 1,
                "total_spend": 10,
            },
        ]
        _, _, gaps = classify_components(learnings)

        assert len(gaps) == 2
        assert gaps[0].sample_size < gaps[1].sample_size

    def test_handles_null_total_spend(self):
        """Handles null total_spend gracefully"""
        learnings = [
            {
                "component_type": "test",
                "component_value": "value",
                "sample_size": 20,
                "win_count": 10,
                "loss_count": 10,
                "total_spend": None,
            }
        ]
        hot, _, _ = classify_components(learnings)

        assert len(hot) == 1
        assert hot[0].cpa is None


class TestThresholds:
    """Tests for threshold constants"""

    def test_thresholds_are_reasonable(self):
        """Threshold constants are reasonable values"""
        assert MIN_SAMPLE_SIZE_HOT > 0
        assert 0 < MIN_WIN_RATE_HOT < 1
        assert 0 < MAX_WIN_RATE_COLD < MIN_WIN_RATE_HOT
        assert MAX_SAMPLE_SIZE_GAP > 0
        assert MAX_SAMPLE_SIZE_GAP < MIN_SAMPLE_SIZE_HOT
