"""
Unit tests for exploration service

Issue: #123
"""

import pytest
from unittest.mock import patch, MagicMock
import random

from src.services.exploration import (
    should_explore,
    thompson_sample,
    select_with_thompson_sampling,
    get_exploration_type,
    ExplorationOption,
    EXPLORATION_RATE,
    MIN_SAMPLES_FOR_CONFIDENCE,
)


class TestShouldExplore:
    """Tests for should_explore function"""

    def test_returns_boolean(self):
        """should_explore returns a boolean"""
        result = should_explore()
        assert isinstance(result, bool)

    def test_exploration_rate_approximately_correct(self):
        """Over many trials, exploration rate should be ~25%"""
        random.seed(42)
        trials = 10000
        explorations = sum(1 for _ in range(trials) if should_explore())
        actual_rate = explorations / trials

        # Allow 3% tolerance
        assert abs(actual_rate - EXPLORATION_RATE) < 0.03


class TestThompsonSample:
    """Tests for thompson_sample function"""

    def test_returns_float_between_0_and_1(self):
        """Thompson sample should return value in [0, 1]"""
        for _ in range(100):
            result = thompson_sample(win_count=5, loss_count=5)
            assert 0 <= result <= 1

    def test_more_wins_higher_samples(self):
        """More wins should generally produce higher samples"""
        high_win_samples = [thompson_sample(90, 10) for _ in range(1000)]
        low_win_samples = [thompson_sample(10, 90) for _ in range(1000)]

        avg_high = sum(high_win_samples) / len(high_win_samples)
        avg_low = sum(low_win_samples) / len(low_win_samples)

        assert avg_high > avg_low

    def test_zero_counts_uses_prior(self):
        """Zero wins/losses should use prior (uninformative)"""
        samples = [thompson_sample(0, 0) for _ in range(1000)]
        avg = sum(samples) / len(samples)

        # With Beta(1,1) prior, expected value is 0.5
        assert 0.4 < avg < 0.6

    def test_high_variance_with_few_samples(self):
        """Few samples should have higher variance"""
        few_samples = [thompson_sample(1, 1) for _ in range(1000)]
        many_samples = [thompson_sample(100, 100) for _ in range(1000)]

        def variance(lst):
            avg = sum(lst) / len(lst)
            return sum((x - avg) ** 2 for x in lst) / len(lst)

        assert variance(few_samples) > variance(many_samples)


class TestSelectWithThompsonSampling:
    """Tests for select_with_thompson_sampling function"""

    def test_single_option_returns_that_option(self):
        """Single option should always be selected"""
        option = ExplorationOption(
            id="1", option_type="component", value="test",
            win_count=5, loss_count=5, sample_size=10
        )
        selected, score, is_exploration = select_with_thompson_sampling([option])

        assert selected.id == "1"
        assert isinstance(score, float)

    def test_raises_on_empty_options(self):
        """Should raise ValueError for empty options"""
        with pytest.raises(ValueError, match="No options"):
            select_with_thompson_sampling([])

    def test_favors_high_win_rate_with_many_samples(self):
        """With many samples, high win rate should usually win"""
        good_option = ExplorationOption(
            id="good", option_type="component", value="good",
            win_count=90, loss_count=10, sample_size=100
        )
        bad_option = ExplorationOption(
            id="bad", option_type="component", value="bad",
            win_count=10, loss_count=90, sample_size=100
        )

        good_wins = 0
        for _ in range(1000):
            selected, _, _ = select_with_thompson_sampling([good_option, bad_option])
            if selected.id == "good":
                good_wins += 1

        # Good option should win most of the time
        assert good_wins > 800

    def test_new_option_gets_chances(self):
        """New option (0 samples) should get some selections"""
        established = ExplorationOption(
            id="established", option_type="component", value="established",
            win_count=60, loss_count=40, sample_size=100
        )
        new = ExplorationOption(
            id="new", option_type="component", value="new",
            win_count=0, loss_count=0, sample_size=0
        )

        new_wins = 0
        for _ in range(1000):
            selected, _, _ = select_with_thompson_sampling([established, new])
            if selected.id == "new":
                new_wins += 1

        # New option should be selected sometimes due to uncertainty
        assert new_wins > 100  # At least 10%

    def test_is_exploration_flag_low_samples(self):
        """Options with low samples should be marked as exploration"""
        low_samples = ExplorationOption(
            id="low", option_type="component", value="low",
            win_count=5, loss_count=5, sample_size=10
        )
        selected, _, is_exploration = select_with_thompson_sampling([low_samples])

        assert is_exploration is True

    def test_is_exploration_flag_high_samples(self):
        """Options with high samples should not be marked as exploration"""
        high_samples = ExplorationOption(
            id="high", option_type="component", value="high",
            win_count=50, loss_count=50, sample_size=100
        )
        selected, _, is_exploration = select_with_thompson_sampling([high_samples])

        assert is_exploration is False


class TestGetExplorationType:
    """Tests for get_exploration_type function"""

    def test_new_component_zero_samples(self):
        """Zero samples component should be new_component"""
        option = ExplorationOption(
            id="1", option_type="component", value="test",
            win_count=0, loss_count=0, sample_size=0
        )
        assert get_exploration_type(option) == "new_component"

    def test_new_avatar_zero_samples(self):
        """Zero samples avatar should be new_avatar"""
        option = ExplorationOption(
            id="1", option_type="avatar", value="test",
            win_count=0, loss_count=0, sample_size=0
        )
        assert get_exploration_type(option) == "new_avatar"

    def test_mutation_medium_samples(self):
        """Medium samples should be mutation"""
        option = ExplorationOption(
            id="1", option_type="component", value="test",
            win_count=10, loss_count=5, sample_size=15
        )
        assert get_exploration_type(option) == "mutation"

    def test_random_high_samples(self):
        """High samples should be random"""
        option = ExplorationOption(
            id="1", option_type="component", value="test",
            win_count=50, loss_count=50, sample_size=100
        )
        assert get_exploration_type(option) == "random"


class TestExplorationOption:
    """Tests for ExplorationOption dataclass"""

    def test_creation_with_required_fields(self):
        """Should create with required fields"""
        option = ExplorationOption(
            id="1",
            option_type="component",
            value="test_value",
            win_count=10,
            loss_count=5,
            sample_size=15
        )
        assert option.id == "1"
        assert option.value == "test_value"
        assert option.sample_size == 15

    def test_optional_fields_default_none(self):
        """Optional fields should default to None"""
        option = ExplorationOption(
            id="1", option_type="component", value="test",
            win_count=0, loss_count=0, sample_size=0
        )
        assert option.geo is None
        assert option.avatar_id is None
