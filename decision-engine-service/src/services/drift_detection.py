"""
Drift Detection Service

Detects performance drift in components by comparing baseline (30d) with current (7d) periods.
Uses Chi-squared test for statistical significance.

Issue: #294
"""

import os
from typing import Optional
from dataclasses import dataclass
import httpx

SCHEMA = "genomai"

# Drift thresholds
DRIFT_THRESHOLD_HIGH = 0.5  # >50% relative change = high drift
DRIFT_THRESHOLD_MEDIUM = 0.25  # 25-50% = medium drift
# <25% = low drift

# Minimum sample sizes
MIN_BASELINE_SAMPLES = 5
MIN_CURRENT_SAMPLES = 3

# Chi-squared critical values (df=1)
CHI2_CRITICAL_005 = 3.841  # p < 0.05
CHI2_CRITICAL_001 = 6.635  # p < 0.01


@dataclass
class DriftResult:
    """Result of drift detection for a single component."""

    component_type: str
    component_value: str
    baseline_win_rate: float
    current_win_rate: float
    baseline_samples: int
    current_samples: int
    drift_score: float
    chi2_value: float
    p_value_category: str  # "p<0.01", "p<0.05", "not_significant"
    severity: str  # "high", "medium", "low"
    recommendation: str


def _get_credentials():
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str) -> dict:
    """Get headers for Supabase REST API."""
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
    }


def calculate_chi2(
    baseline_wins: int,
    baseline_losses: int,
    current_wins: int,
    current_losses: int,
) -> float:
    """
    Calculate Chi-squared statistic for 2x2 contingency table.

    Tests if current win/loss distribution differs from baseline.
    """
    # Totals
    baseline_total = baseline_wins + baseline_losses
    current_total = current_wins + current_losses
    total = baseline_total + current_total

    if total == 0:
        return 0.0

    total_wins = baseline_wins + current_wins
    total_losses = baseline_losses + current_losses

    # Expected values under null hypothesis
    e_baseline_wins = (baseline_total * total_wins) / total
    e_baseline_losses = (baseline_total * total_losses) / total
    e_current_wins = (current_total * total_wins) / total
    e_current_losses = (current_total * total_losses) / total

    # Chi-squared calculation with Yates correction for small samples
    chi2 = 0.0
    for observed, expected in [
        (baseline_wins, e_baseline_wins),
        (baseline_losses, e_baseline_losses),
        (current_wins, e_current_wins),
        (current_losses, e_current_losses),
    ]:
        if expected > 0:
            # Yates correction
            diff = abs(observed - expected) - 0.5
            if diff > 0:
                chi2 += (diff * diff) / expected

    return chi2


def calculate_drift_score(baseline_rate: float, current_rate: float) -> float:
    """
    Calculate relative drift score.

    Returns absolute relative change (0 to 1+).
    """
    if baseline_rate <= 0:
        # If baseline is 0, any positive current is infinite drift
        return 1.0 if current_rate > 0 else 0.0

    return abs(current_rate - baseline_rate) / baseline_rate


def get_severity(drift_score: float, chi2: float) -> str:
    """Determine severity based on drift score and statistical significance."""
    if chi2 < CHI2_CRITICAL_005:
        return "low"  # Not statistically significant

    if drift_score >= DRIFT_THRESHOLD_HIGH:
        return "high"
    elif drift_score >= DRIFT_THRESHOLD_MEDIUM:
        return "medium"
    return "low"


def get_p_value_category(chi2: float) -> str:
    """Get p-value category from chi-squared value."""
    if chi2 >= CHI2_CRITICAL_001:
        return "p<0.01"
    elif chi2 >= CHI2_CRITICAL_005:
        return "p<0.05"
    return "not_significant"


def get_recommendation(severity: str, current_rate: float, baseline_rate: float) -> str:
    """Get recommendation based on drift severity and direction."""
    if severity == "high":
        if current_rate < baseline_rate:
            return "Рассмотреть паузу компонента"
        else:
            return "Значительное улучшение"
    elif severity == "medium":
        if current_rate < baseline_rate:
            return "Мониторить внимательно"
        else:
            return "Позитивный тренд"
    return "Действий не требуется"


async def detect_drift(
    component_type: Optional[str] = None,
    baseline_days: int = 30,
    current_days: int = 7,
    min_severity: str = "medium",
) -> list[DriftResult]:
    """
    Detect drift in component performance.

    Args:
        component_type: Filter by component type (e.g., "emotion_primary")
        baseline_days: Days for baseline period (default 30)
        current_days: Days for current period (default 7)
        min_severity: Minimum severity to include ("low", "medium", "high")

    Returns:
        List of DriftResult for components with detected drift.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Query for aggregated data by period
    # Using component_learnings for current state
    # and component_learning_snapshots for historical baseline
    filter_clause = ""
    if component_type:
        filter_clause = f"&component_type=eq.{component_type}"

    async with httpx.AsyncClient() as client:
        # Get current period data from component_learnings
        current_resp = await client.get(
            f"{rest_url}/component_learnings"
            f"?avatar_id=is.null{filter_clause}"
            f"&select=component_type,component_value,sample_size,win_count,loss_count,win_rate"
            f"&sample_size=gte.{MIN_CURRENT_SAMPLES}",
            headers=headers,
        )
        current_resp.raise_for_status()
        current_data = current_resp.json()

        # Get baseline from snapshots (oldest available)
        # Since we just created the table, use earliest snapshot as baseline proxy
        baseline_resp = await client.get(
            f"{rest_url}/component_learning_snapshots"
            f"?avatar_id=is.null{filter_clause}"
            f"&select=component_type,component_value,sample_size,win_count,loss_count,win_rate,snapshot_date"
            f"&order=snapshot_date.asc"
            f"&limit=100",
            headers=headers,
        )
        baseline_resp.raise_for_status()
        baseline_data = baseline_resp.json()

    # Build lookup for baseline
    baseline_lookup = {}
    for row in baseline_data:
        key = (row["component_type"], row["component_value"])
        if key not in baseline_lookup:
            baseline_lookup[key] = row

    results = []
    severity_order = {"low": 0, "medium": 1, "high": 2}
    min_sev_val = severity_order.get(min_severity, 1)

    for current in current_data:
        key = (current["component_type"], current["component_value"])
        baseline = baseline_lookup.get(key)

        if not baseline:
            continue

        baseline_wins = baseline.get("win_count") or 0
        baseline_losses = baseline.get("loss_count") or 0
        baseline_samples = baseline.get("sample_size") or 0
        baseline_rate = float(baseline.get("win_rate") or 0)

        current_wins = current.get("win_count") or 0
        current_losses = current.get("loss_count") or 0
        current_samples = current.get("sample_size") or 0
        current_rate = float(current.get("win_rate") or 0)

        # Skip if not enough baseline samples
        if baseline_samples < MIN_BASELINE_SAMPLES:
            continue

        # Calculate drift metrics
        drift_score = calculate_drift_score(baseline_rate, current_rate)
        chi2 = calculate_chi2(
            baseline_wins, baseline_losses, current_wins, current_losses
        )
        severity = get_severity(drift_score, chi2)
        p_category = get_p_value_category(chi2)
        recommendation = get_recommendation(severity, current_rate, baseline_rate)

        # Filter by minimum severity
        if severity_order.get(severity, 0) < min_sev_val:
            continue

        results.append(
            DriftResult(
                component_type=current["component_type"],
                component_value=current["component_value"],
                baseline_win_rate=baseline_rate,
                current_win_rate=current_rate,
                baseline_samples=baseline_samples,
                current_samples=current_samples,
                drift_score=drift_score,
                chi2_value=chi2,
                p_value_category=p_category,
                severity=severity,
                recommendation=recommendation,
            )
        )

    # Sort by severity (high first) then drift score
    results.sort(key=lambda r: (-severity_order.get(r.severity, 0), -r.drift_score))

    return results


def format_drift_telegram(results: list[DriftResult]) -> str:
    """Format drift detection results for Telegram."""
    if not results:
        return (
            "✅ <b>Дрифт не обнаружен</b>\n\n"
            "Все компоненты работают в пределах нормы.\n\n"
            "<i>Дрифт сравнивает последние 7 дней с базовыми 30 днями.</i>"
        )

    emoji_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    lines = ["⚠️ <b>Обнаружен дрифт</b>\n"]

    for result in results[:5]:  # Limit to top 5
        emoji = emoji_map.get(result.severity, "⚪")
        direction = "↓" if result.current_win_rate < result.baseline_win_rate else "↑"

        lines.append(
            f"\n{emoji} <b>{result.component_type}.{result.component_value}</b>"
        )
        lines.append(
            f"├── Базовый: {result.baseline_win_rate:.0%} "
            f"({result.baseline_samples} samples)"
        )
        lines.append(
            f"├── Текущий: {result.current_win_rate:.0%} "
            f"({result.current_samples} samples) {direction}"
        )
        lines.append(f"├── Дрифт: {result.drift_score:.0%} ({result.severity})")
        lines.append(f"├── Стат: {result.p_value_category}")
        lines.append(f"└── <i>{result.recommendation}</i>")

    if len(results) > 5:
        lines.append(f"\n<i>+{len(results) - 5} ещё компонентов с дрифтом</i>")

    lines.append("\n\n<code>/drift [type]</code> - фильтр по типу компонента")

    return "\n".join(lines)


async def get_available_component_types() -> list[str]:
    """Get list of component types available for drift detection."""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/component_learnings"
            f"?avatar_id=is.null"
            f"&sample_size=gte.{MIN_BASELINE_SAMPLES}"
            f"&select=component_type",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    types = list(
        set(row["component_type"] for row in data if row.get("component_type"))
    )
    return sorted(types)
