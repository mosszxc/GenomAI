"""
Confidence Interval Service

Calculates Wilson score intervals for component win rates.
Shows statistical confidence based on sample size.
"""

import math
import os
from dataclasses import dataclass
from typing import Optional

import httpx


# Z-score for 95% confidence interval
Z_95 = 1.96
# Threshold for high variance flag (CI width > threshold)
HIGH_VARIANCE_THRESHOLD = 0.10  # ±10%
# Target CI width for required sample calculation
TARGET_CI_WIDTH = 0.05  # ±5%


@dataclass
class ComponentConfidence:
    """Confidence interval data for a component."""

    component_type: str
    component_value: str
    win_rate: float
    sample_size: int
    win_count: int
    ci_lower: float
    ci_upper: float
    ci_width: float
    high_variance: bool
    required_samples: Optional[int]  # Samples needed for target CI
    trend: str  # "up", "down", "stable"


def wilson_score_interval(
    successes: int,
    trials: int,
    z: float = Z_95,
) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval for binomial proportion.

    Args:
        successes: Number of successes (wins)
        trials: Total number of trials (sample_size)
        z: Z-score for confidence level (default 1.96 for 95%)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if trials == 0:
        return 0.0, 0.0

    n = trials
    p = successes / n
    z2 = z * z

    # Wilson score formula
    denominator = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denominator

    # Width calculation
    sqrt_term = math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    width = z * sqrt_term / denominator

    lower = max(0.0, center - width)
    upper = min(1.0, center + width)

    return lower, upper


def required_sample_size(
    current_p: float,
    target_ci_width: float = TARGET_CI_WIDTH,
    z: float = Z_95,
) -> int:
    """
    Calculate required sample size for target CI width.

    Args:
        current_p: Current observed proportion (win rate)
        target_ci_width: Target half-width of CI (e.g., 0.05 for ±5%)
        z: Z-score for confidence level

    Returns:
        Required sample size for target precision
    """
    if target_ci_width <= 0:
        return 0

    # Handle edge cases
    p = max(0.01, min(0.99, current_p))  # Bound between 1% and 99%

    # Sample size formula: n = z² * p(1-p) / E²
    # Using conservative estimate (p=0.5 if unknown)
    n = (z * z * p * (1 - p)) / (target_ci_width * target_ci_width)

    return int(math.ceil(n))


async def get_component_confidence_data(
    component_type: Optional[str] = None,
    min_samples: int = 3,
    limit: int = 10,
) -> list[ComponentConfidence]:
    """
    Get confidence interval data for components.

    Args:
        component_type: Filter by component type (e.g., "emotion_primary")
        min_samples: Minimum sample size to include
        limit: Maximum number of components to return

    Returns:
        List of ComponentConfidence objects sorted by sample_size desc
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return []

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    # Build query
    query = (
        f"{supabase_url}/rest/v1/component_learnings"
        f"?select=component_type,component_value,win_rate,sample_size,win_count"
        f"&sample_size=gte.{min_samples}"
        f"&order=sample_size.desc"
        f"&limit={limit}"
    )

    if component_type:
        query += f"&component_type=eq.{component_type}"

    async with httpx.AsyncClient() as client:
        response = await client.get(query, headers=headers)

        if response.status_code != 200:
            return []

        components = response.json()

    results = []
    for comp in components:
        sample_size = int(comp.get("sample_size", 0) or 0)
        win_count = int(comp.get("win_count", 0) or 0)
        win_rate = float(comp.get("win_rate", 0) or 0)

        # Calculate Wilson CI
        ci_lower, ci_upper = wilson_score_interval(win_count, sample_size)
        ci_width = (ci_upper - ci_lower) / 2  # Half-width

        # Check high variance
        high_variance = ci_width > HIGH_VARIANCE_THRESHOLD

        # Calculate required samples for target precision
        req_samples = None
        if high_variance:
            total_needed = required_sample_size(win_rate, TARGET_CI_WIDTH)
            additional_needed = max(0, total_needed - sample_size)
            req_samples = additional_needed if additional_needed > 0 else None

        results.append(
            ComponentConfidence(
                component_type=comp["component_type"],
                component_value=comp["component_value"],
                win_rate=win_rate,
                sample_size=sample_size,
                win_count=win_count,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                ci_width=ci_width,
                high_variance=high_variance,
                required_samples=req_samples,
                trend="stable",  # TODO: calculate from historical data
            )
        )

    return results


def format_confidence_telegram(data: list[ComponentConfidence]) -> str:
    """
    Format confidence data for Telegram message.

    Args:
        data: List of ComponentConfidence objects

    Returns:
        Formatted Telegram message with HTML
    """
    if not data:
        return (
            "No confidence data available.\n\n"
            "Components need at least 3 samples to calculate confidence intervals."
        )

    lines = ["<b>Component Confidence Intervals</b>", ""]

    for comp in data:
        # Win rate with CI
        win_pct = comp.win_rate * 100
        ci_pct = comp.ci_width * 100
        ci_lower_pct = comp.ci_lower * 100
        ci_upper_pct = comp.ci_upper * 100

        # Component header with variance flag
        variance_flag = " HIGH VARIANCE" if comp.high_variance else ""
        lines.append(f"<b>{comp.component_value}</b>{variance_flag}")

        # Win rate line with CI
        lines.append(f"  {win_pct:.0f}% \u00b1{ci_pct:.0f}% (95% CI)")
        lines.append(f"  \u251c\u2500 Range: {ci_lower_pct:.0f}% - {ci_upper_pct:.0f}%")
        lines.append(f"  \u251c\u2500 Sample size: {comp.sample_size}")

        # Required samples if high variance
        if comp.required_samples:
            lines.append(
                f"  \u251c\u2500 For \u00b15% CI: +{comp.required_samples} samples"
            )

        # Trend indicator
        trend_arrow = {"up": "\u2191", "down": "\u2193", "stable": "\u2194"}.get(
            comp.trend, "\u2194"
        )
        lines.append(f"  \u2514\u2500 Trend: {comp.trend} {trend_arrow}")
        lines.append("")

    # Legend
    lines.extend(
        [
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            "<i>HIGH VARIANCE = CI > \u00b110%</i>",
            "<i>More samples = narrower CI</i>",
        ]
    )

    return "\n".join(lines)


async def get_available_component_types() -> list[str]:
    """Get list of available component types with data."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return []

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{supabase_url}/rest/v1/component_learnings"
            f"?select=component_type"
            f"&sample_size=gt.0",
            headers=headers,
        )

        if response.status_code != 200:
            return []

        rows = response.json()

    # Get unique types
    types = sorted(set(r["component_type"] for r in rows if r.get("component_type")))
    return types
