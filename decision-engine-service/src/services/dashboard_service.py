"""
Dashboard Service

Provides HOT/COLD/GAPS meta analysis for creative components.

Issue: #602
"""

import os
from dataclasses import dataclass
from typing import Any, Optional, cast

from src.core.http_client import get_http_client
from src.utils.errors import SupabaseError


SCHEMA = "genomai"

# Thresholds for HOT/COLD/GAPS classification
MIN_SAMPLE_SIZE_HOT = 10  # Minimum samples to be considered HOT
MIN_WIN_RATE_HOT = 0.35  # Minimum win rate for HOT
MAX_WIN_RATE_COLD = 0.15  # Maximum win rate to be COLD
MAX_SAMPLE_SIZE_GAP = 5  # Maximum samples to be considered GAP


@dataclass
class HotComponent:
    """High-performing component"""

    variable: str
    value: str
    win_rate: float
    cpa: Optional[float]
    sample_size: int


@dataclass
class ColdComponent:
    """Underperforming component"""

    variable: str
    value: str
    fatigue: str  # HIGH, MEDIUM, LOW
    trend: float  # Negative = declining
    sample_size: int


@dataclass
class GapComponent:
    """Underexplored component"""

    variable: str
    value: str
    sample_size: int


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str) -> dict:
    """Get headers for Supabase REST API with schema"""
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }


def _calculate_win_rate(win_count: int, sample_size: int) -> float:
    """Calculate win rate with zero division protection"""
    return win_count / sample_size if sample_size > 0 else 0.0


def _calculate_cpa(total_spend: float, win_count: int) -> Optional[float]:
    """Calculate CPA (Cost Per Acquisition) with zero division protection"""
    return total_spend / win_count if win_count > 0 else None


def _classify_fatigue(win_rate: float, sample_size: int) -> str:
    """Classify fatigue level based on win rate and sample size"""
    if sample_size < 5:
        return "LOW"  # Not enough data
    if win_rate < 0.1:
        return "HIGH"
    if win_rate < 0.2:
        return "MEDIUM"
    return "LOW"


def _estimate_trend(win_rate: float, sample_size: int) -> float:
    """
    Estimate trend based on current win rate.

    Note: For a more accurate trend, we would need historical snapshots.
    This is a simplified estimation based on win rate deviation from expected.
    """
    # Expected baseline win rate
    baseline = 0.25
    # Trend is deviation from baseline, scaled by confidence (sample_size)
    confidence_factor = min(sample_size / 20, 1.0)  # Max confidence at 20 samples
    return (win_rate - baseline) * confidence_factor


async def get_component_learnings(
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> list[dict]:
    """
    Fetch component learnings from database.

    Args:
        geo: Filter by geo (optional)
        vertical: Filter by vertical (optional, not yet implemented in table)

    Returns:
        List of component learning records
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build query
    query = f"{rest_url}/component_learnings?select=*"

    # Add geo filter if provided
    if geo:
        query += f"&geo=eq.{geo}"

    # Note: vertical filtering would require joining with ideas/decomposed_creatives
    # For now, we focus on geo filtering which is directly available

    client = get_http_client()
    response = await client.get(query, headers=headers)
    response.raise_for_status()

    return cast(list[dict[str, Any]], response.json())


def classify_components(
    learnings: list[dict],
) -> tuple[list[HotComponent], list[ColdComponent], list[GapComponent]]:
    """
    Classify components into HOT, COLD, and GAPS categories.

    Args:
        learnings: List of component learning records

    Returns:
        Tuple of (hot, cold, gaps) lists
    """
    hot: list[HotComponent] = []
    cold: list[ColdComponent] = []
    gaps: list[GapComponent] = []

    for record in learnings:
        component_type = record.get("component_type", "")
        component_value = record.get("component_value", "")
        sample_size = record.get("sample_size", 0)
        win_count = record.get("win_count", 0)
        total_spend = record.get("total_spend", 0) or 0

        win_rate = _calculate_win_rate(win_count, sample_size)
        cpa = _calculate_cpa(total_spend, win_count)

        # GAP: Low sample size - needs more exploration
        if sample_size < MAX_SAMPLE_SIZE_GAP:
            gaps.append(
                GapComponent(
                    variable=component_type,
                    value=component_value,
                    sample_size=sample_size,
                )
            )
        # HOT: High win rate with sufficient samples
        elif sample_size >= MIN_SAMPLE_SIZE_HOT and win_rate >= MIN_WIN_RATE_HOT:
            hot.append(
                HotComponent(
                    variable=component_type,
                    value=component_value,
                    win_rate=round(win_rate, 2),
                    cpa=round(cpa, 2) if cpa else None,
                    sample_size=sample_size,
                )
            )
        # COLD: Low win rate with sufficient samples
        elif sample_size >= MIN_SAMPLE_SIZE_HOT and win_rate <= MAX_WIN_RATE_COLD:
            fatigue = _classify_fatigue(win_rate, sample_size)
            trend = _estimate_trend(win_rate, sample_size)
            cold.append(
                ColdComponent(
                    variable=component_type,
                    value=component_value,
                    fatigue=fatigue,
                    trend=round(trend, 2),
                    sample_size=sample_size,
                )
            )

    # Sort by relevance
    hot.sort(key=lambda x: x.win_rate, reverse=True)
    cold.sort(key=lambda x: x.trend)  # Most negative first
    gaps.sort(key=lambda x: x.sample_size)  # Least explored first

    return hot, cold, gaps


def get_current_week() -> int:
    """Get current ISO week number"""
    from datetime import datetime

    return datetime.now().isocalendar()[1]


async def get_dashboard_meta(
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> dict:
    """
    Main entry point: Get dashboard meta for HOT/COLD/GAPS.

    Args:
        geo: Filter by geo (optional)
        vertical: Filter by vertical (optional)

    Returns:
        Dashboard meta response
    """
    # Fetch component learnings
    learnings = await get_component_learnings(geo=geo, vertical=vertical)

    # Classify components
    hot, cold, gaps = classify_components(learnings)

    return {
        "geo": geo,
        "vertical": vertical,
        "week": get_current_week(),
        "hot": [
            {
                "variable": h.variable,
                "value": h.value,
                "win_rate": h.win_rate,
                "cpa": h.cpa,
            }
            for h in hot[:10]  # Limit to top 10
        ],
        "cold": [
            {
                "variable": c.variable,
                "value": c.value,
                "fatigue": c.fatigue,
                "trend": c.trend,
            }
            for c in cold[:10]  # Limit to top 10
        ],
        "gaps": [
            {
                "variable": g.variable,
                "value": g.value,
                "sample_size": g.sample_size,
            }
            for g in gaps[:10]  # Limit to top 10
        ],
        "summary": {
            "total_components": len(learnings),
            "hot_count": len(hot),
            "cold_count": len(cold),
            "gaps_count": len(gaps),
        },
    }
