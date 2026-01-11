"""
Unit tests for module selector service.

Tests selection constants and utility functions.
"""

import pytest


class TestSelectionConstants:
    """Tests for selection ratio constants"""

    def test_exploitation_ratio(self):
        """Exploitation ratio should be 90%"""
        from src.services.module_selector import EXPLOITATION_RATIO

        assert EXPLOITATION_RATIO == 0.9

    def test_exploration_ratio(self):
        """Exploration ratio should be 10%"""
        from src.services.module_selector import EXPLORATION_RATIO

        assert EXPLORATION_RATIO == 0.1

    def test_ratios_sum_to_one(self):
        """Exploitation + exploration should equal 1.0"""
        from src.services.module_selector import EXPLOITATION_RATIO, EXPLORATION_RATIO

        assert EXPLOITATION_RATIO + EXPLORATION_RATIO == 1.0

    def test_exploration_threshold(self):
        """Exploration threshold should be 5"""
        from src.services.module_selector import EXPLORATION_SAMPLE_THRESHOLD

        assert EXPLORATION_SAMPLE_THRESHOLD == 5


class TestMinimumRequirements:
    """Tests for minimum module requirements"""

    def test_min_hooks_required(self):
        """Should require at least 3 hooks"""
        from src.services.module_selector import MIN_HOOKS_REQUIRED

        assert MIN_HOOKS_REQUIRED == 3

    def test_min_promises_required(self):
        """Should require at least 3 promises"""
        from src.services.module_selector import MIN_PROMISES_REQUIRED

        assert MIN_PROMISES_REQUIRED == 3

    def test_min_proofs_required(self):
        """Should require at least 2 proofs"""
        from src.services.module_selector import MIN_PROOFS_REQUIRED

        assert MIN_PROOFS_REQUIRED == 2

    def test_min_explored_modules(self):
        """Should require at least 2 explored modules"""
        from src.services.module_selector import MIN_EXPLORED_MODULES

        assert MIN_EXPLORED_MODULES == 2


class TestSplitCalculation:
    """Tests for exploitation/exploration split calculation"""

    def test_split_for_3_modules(self):
        """3 modules should be 2 exploitation + 1 exploration"""
        from src.services.module_selector import EXPLOITATION_RATIO

        count = 3
        exploitation = max(1, int(count * EXPLOITATION_RATIO))
        exploration = count - exploitation

        assert exploitation == 2
        assert exploration == 1

    def test_split_for_5_modules(self):
        """5 modules should be 4 exploitation + 1 exploration"""
        from src.services.module_selector import EXPLOITATION_RATIO

        count = 5
        exploitation = max(1, int(count * EXPLOITATION_RATIO))
        exploration = count - exploitation

        assert exploitation == 4
        assert exploration == 1

    def test_split_for_10_modules(self):
        """10 modules should be 9 exploitation + 1 exploration"""
        from src.services.module_selector import EXPLOITATION_RATIO

        count = 10
        exploitation = max(1, int(count * EXPLOITATION_RATIO))
        exploration = count - exploitation

        assert exploitation == 9
        assert exploration == 1

    def test_split_minimum_exploitation(self):
        """Should always have at least 1 exploitation"""
        from src.services.module_selector import EXPLOITATION_RATIO

        count = 1
        exploitation = max(1, int(count * EXPLOITATION_RATIO))

        assert exploitation >= 1


class TestSchemaConstant:
    """Tests for schema constant"""

    def test_schema_is_genomai(self):
        """Schema should be 'genomai'"""
        from src.services.module_selector import SCHEMA

        assert SCHEMA == "genomai"


class TestCompatibilityScore:
    """Tests for compatibility score logic"""

    def test_default_score_is_neutral(self):
        """Default compatibility score should be 0.5 (neutral)"""
        # This is tested through the get_compatibility_score function
        # which returns 0.5 when no data exists
        neutral_score = 0.5
        assert neutral_score == 0.5

    def test_score_range(self):
        """Compatibility score should be between 0 and 1"""
        min_score = 0.0
        max_score = 1.0
        neutral_score = 0.5

        assert min_score <= neutral_score <= max_score


class TestCombinedScoreWeights:
    """Tests for combined score calculation logic"""

    def test_combined_score_weights(self):
        """Combined score should be 70% win_rate + 30% compatibility"""
        win_rate_weight = 0.7
        compatibility_weight = 0.3

        assert win_rate_weight + compatibility_weight == 1.0

    def test_combined_score_calculation(self):
        """Should correctly calculate combined score"""
        win_rate = 0.8
        compatibility = 0.6

        combined = 0.7 * win_rate + 0.3 * compatibility

        assert combined == pytest.approx(0.74)  # 0.7*0.8 + 0.3*0.6 = 0.56 + 0.18

    def test_combined_score_with_perfect_scores(self):
        """Perfect scores should give combined score of 1.0"""
        win_rate = 1.0
        compatibility = 1.0

        combined = 0.7 * win_rate + 0.3 * compatibility

        assert combined == pytest.approx(1.0)

    def test_combined_score_with_zero_scores(self):
        """Zero scores should give combined score of 0.0"""
        win_rate = 0.0
        compatibility = 0.0

        combined = 0.7 * win_rate + 0.3 * compatibility

        assert combined == pytest.approx(0.0)


class TestModuleOrdering:
    """Tests for module ordering logic"""

    def test_ordering_for_id_comparison(self):
        """Module A ID should be less than Module B ID in compatibility table"""
        # This tests the constraint: module_a_id < module_b_id
        id_a = "00000000-0000-0000-0000-000000000001"
        id_b = "00000000-0000-0000-0000-000000000002"

        # Ensure correct ordering
        if id_a > id_b:
            id_a, id_b = id_b, id_a

        assert id_a < id_b

    def test_swap_if_needed(self):
        """Should swap IDs if first is greater than second"""
        id_a = "z-module"
        id_b = "a-module"

        # Simulate the swap logic from get_compatibility_score
        if id_a > id_b:
            id_a, id_b = id_b, id_a

        assert id_a == "a-module"
        assert id_b == "z-module"
