"""
Tests for staleness_detector.py

Focus: Error handling and fallback behavior (issue #466)
"""

import pytest
from unittest.mock import AsyncMock, patch
import logging

from src.services.staleness_detector import (
    calculate_staleness_metrics,
    StalenessMetrics,
    DAYS_STALE_THRESHOLD,
)


@pytest.mark.asyncio
async def test_error_sources_tracked_on_db_failure():
    """When DB fails, error_sources should contain the failed metrics."""
    with (
        patch(
            "src.services.staleness_detector.calculate_diversity_score",
            new_callable=AsyncMock,
            side_effect=Exception("DB connection failed"),
        ),
        patch(
            "src.services.staleness_detector.calculate_win_rate_trend",
            new_callable=AsyncMock,
            side_effect=Exception("DB timeout"),
        ),
        patch(
            "src.services.staleness_detector.calculate_fatigue_ratio",
            new_callable=AsyncMock,
            return_value=0.3,  # This one succeeds
        ),
        patch(
            "src.services.staleness_detector.calculate_days_since_new_component",
            new_callable=AsyncMock,
            return_value=7,  # This one succeeds
        ),
        patch(
            "src.services.staleness_detector.calculate_exploration_success_rate",
            new_callable=AsyncMock,
            side_effect=Exception("Network error"),
        ),
    ):
        metrics = await calculate_staleness_metrics()

        # Should have tracked the 3 failures
        assert len(metrics.error_sources) == 3
        assert "diversity_score" in metrics.error_sources
        assert "win_rate_trend" in metrics.error_sources
        assert "exploration_success_rate" in metrics.error_sources

        # Should NOT have successful ones
        assert "fatigue_ratio" not in metrics.error_sources
        assert "days_since_new_component" not in metrics.error_sources

        # Should use fallback values for failed metrics
        assert metrics.diversity_score == 0.5  # neutral fallback
        assert metrics.win_rate_trend == 0.0  # neutral fallback
        assert metrics.exploration_success_rate == 0.5  # neutral fallback

        # Should use actual values for successful metrics
        assert metrics.fatigue_ratio == 0.3
        assert metrics.days_since_new_component == 7


@pytest.mark.asyncio
async def test_no_errors_when_db_succeeds():
    """When DB works, error_sources should be empty."""
    with (
        patch(
            "src.services.staleness_detector.calculate_diversity_score",
            new_callable=AsyncMock,
            return_value=0.8,
        ),
        patch(
            "src.services.staleness_detector.calculate_win_rate_trend",
            new_callable=AsyncMock,
            return_value=0.1,
        ),
        patch(
            "src.services.staleness_detector.calculate_fatigue_ratio",
            new_callable=AsyncMock,
            return_value=0.2,
        ),
        patch(
            "src.services.staleness_detector.calculate_days_since_new_component",
            new_callable=AsyncMock,
            return_value=5,
        ),
        patch(
            "src.services.staleness_detector.calculate_exploration_success_rate",
            new_callable=AsyncMock,
            return_value=0.6,
        ),
    ):
        metrics = await calculate_staleness_metrics()

        # No errors
        assert len(metrics.error_sources) == 0
        assert metrics.error_sources == []

        # Actual values used
        assert metrics.diversity_score == 0.8
        assert metrics.win_rate_trend == 0.1
        assert metrics.fatigue_ratio == 0.2
        assert metrics.days_since_new_component == 5
        assert metrics.exploration_success_rate == 0.6


@pytest.mark.asyncio
async def test_errors_are_logged(caplog):
    """DB errors should be logged with ERROR level."""
    with (
        patch(
            "src.services.staleness_detector.calculate_diversity_score",
            new_callable=AsyncMock,
            side_effect=Exception("Test DB error"),
        ),
        patch(
            "src.services.staleness_detector.calculate_win_rate_trend",
            new_callable=AsyncMock,
            return_value=0.0,
        ),
        patch(
            "src.services.staleness_detector.calculate_fatigue_ratio",
            new_callable=AsyncMock,
            return_value=0.0,
        ),
        patch(
            "src.services.staleness_detector.calculate_days_since_new_component",
            new_callable=AsyncMock,
            return_value=7,
        ),
        patch(
            "src.services.staleness_detector.calculate_exploration_success_rate",
            new_callable=AsyncMock,
            return_value=0.5,
        ),
    ):
        with caplog.at_level(logging.ERROR):
            await calculate_staleness_metrics(avatar_id="test-avatar", geo="US")

        # Check error was logged
        assert "Failed to calculate diversity_score" in caplog.text
        assert "Test DB error" in caplog.text
        assert "avatar=test-avatar" in caplog.text
        assert "geo=US" in caplog.text


@pytest.mark.asyncio
async def test_all_errors_fallback_warning_logged(caplog):
    """When all metrics fail, a warning should be logged."""
    with (
        patch(
            "src.services.staleness_detector.calculate_diversity_score",
            new_callable=AsyncMock,
            side_effect=Exception("Error 1"),
        ),
        patch(
            "src.services.staleness_detector.calculate_win_rate_trend",
            new_callable=AsyncMock,
            side_effect=Exception("Error 2"),
        ),
        patch(
            "src.services.staleness_detector.calculate_fatigue_ratio",
            new_callable=AsyncMock,
            side_effect=Exception("Error 3"),
        ),
        patch(
            "src.services.staleness_detector.calculate_days_since_new_component",
            new_callable=AsyncMock,
            side_effect=Exception("Error 4"),
        ),
        patch(
            "src.services.staleness_detector.calculate_exploration_success_rate",
            new_callable=AsyncMock,
            side_effect=Exception("Error 5"),
        ),
    ):
        with caplog.at_level(logging.WARNING):
            metrics = await calculate_staleness_metrics()

        # All 5 metrics failed
        assert len(metrics.error_sources) == 5

        # Warning about fallback values
        assert "5/5 fallback values due to errors" in caplog.text


@pytest.mark.asyncio
async def test_staleness_metrics_dataclass_has_error_sources():
    """StalenessMetrics dataclass should have error_sources field."""
    metrics = StalenessMetrics(
        diversity_score=0.5,
        win_rate_trend=0.0,
        fatigue_ratio=0.0,
        days_since_new_component=14,
        exploration_success_rate=0.5,
        staleness_score=0.5,
        is_stale=False,
        error_sources=["diversity_score", "win_rate_trend"],
    )

    assert hasattr(metrics, "error_sources")
    assert metrics.error_sources == ["diversity_score", "win_rate_trend"]


@pytest.mark.asyncio
async def test_error_sources_default_empty():
    """error_sources should default to empty list."""
    metrics = StalenessMetrics(
        diversity_score=0.5,
        win_rate_trend=0.0,
        fatigue_ratio=0.0,
        days_since_new_component=14,
        exploration_success_rate=0.5,
        staleness_score=0.5,
        is_stale=False,
    )

    assert metrics.error_sources == []
