"""
Meta Dashboard Service

Generates Meta Dashboard showing HOT/COLD/GAPS components
for Telegram display.

Issue: #603 - Telegram Dashboard UI

HOT: Components with high win rate (>30%)
COLD: Components with fatigue (frequently used, declining performance)
GAPS: Components with insufficient test data (<5 samples)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.core.http_client import get_http_client

SCHEMA = "genomai"

# Thresholds
HOT_WIN_RATE_THRESHOLD = 0.30  # >30% = hot
MIN_SAMPLES_FOR_HOT = 5
MIN_SAMPLES_FOR_COLD = 3
FATIGUE_USAGE_THRESHOLD = 3  # >3 uses in 7 days = fatigued
FRESHNESS_WINDOW_DAYS = 7
GAPS_SAMPLE_THRESHOLD = 5  # <5 samples = gap

# Component types to analyze
COMPONENT_TYPES = [
    "emotion_primary",
    "angle_type",
    "source_type",
    "opening_type",
    "message_structure",
    "promise_type",
]

# Type display names for dashboard
TYPE_DISPLAY_NAMES = {
    "emotion_primary": "Hook",
    "angle_type": "Angle",
    "source_type": "Source",
    "opening_type": "Opening",
    "message_structure": "Structure",
    "promise_type": "Promise",
}


@dataclass
class MetaComponent:
    """A component entry in meta dashboard."""

    component_type: str
    component_value: str
    win_rate: Optional[float] = None
    sample_size: int = 0
    usage_count: int = 0  # Recent usage for fatigue
    revenue: float = 0.0  # Estimated revenue contribution

    @property
    def display_type(self) -> str:
        """Get display name for component type."""
        return TYPE_DISPLAY_NAMES.get(self.component_type, self.component_type[:8])

    @property
    def is_hot(self) -> bool:
        """Check if component is hot (high performer)."""
        return (
            self.win_rate is not None
            and self.win_rate >= HOT_WIN_RATE_THRESHOLD
            and self.sample_size >= MIN_SAMPLES_FOR_HOT
        )

    @property
    def is_fatigued(self) -> bool:
        """Check if component is fatigued."""
        return self.usage_count >= FATIGUE_USAGE_THRESHOLD

    @property
    def is_gap(self) -> bool:
        """Check if component is a gap (needs more testing)."""
        return self.sample_size < GAPS_SAMPLE_THRESHOLD


@dataclass
class MetaDashboard:
    """Complete meta dashboard data."""

    geo: Optional[str] = None
    avatar: Optional[str] = None
    week_num: int = 0
    hot_components: list[MetaComponent] = field(default_factory=list)
    cold_components: list[MetaComponent] = field(default_factory=list)
    gap_components: list[MetaComponent] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


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


async def _get_component_learnings(
    rest_url: str,
    headers: dict[str, str],
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Get component learnings with optional filters."""
    filters = []
    if geo:
        filters.append(f"geo=eq.{geo}")
    else:
        filters.append("geo=is.null")

    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")

    filter_str = "&".join(filters) if filters else ""

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?{filter_str}"
        f"&select=component_type,component_value,win_rate,sample_size"
        f"&order=win_rate.desc.nullslast",
        headers=headers,
    )
    response.raise_for_status()
    result: list[dict[str, Any]] = response.json()
    return result


async def _get_recent_usage(rest_url: str, headers: dict[str, str]) -> dict[tuple[str, str], int]:
    """
    Get component usage counts in last 7 days.

    Returns: {(component_type, component_value): usage_count}
    """
    usage_counts: dict[tuple[str, str], int] = {}

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/decomposed_creatives"
        f"?created_at=gte.now()-interval'{FRESHNESS_WINDOW_DAYS} days'"
        f"&select=payload",
        headers=headers,
    )

    if response.status_code != 200:
        return usage_counts

    rows = response.json()

    for row in rows:
        payload = row.get("payload") or {}
        for comp_type in COMPONENT_TYPES:
            comp_value = payload.get(comp_type)
            if comp_value:
                key = (comp_type, comp_value)
                usage_counts[key] = usage_counts.get(key, 0) + 1

    return usage_counts


async def _get_revenue_stats(
    rest_url: str,
    headers: dict[str, str],
) -> dict[tuple[str, str], float]:
    """
    Get revenue statistics per component.

    Returns: {(component_type, component_value): avg_revenue}
    """
    revenue_stats: dict[tuple[str, str], float] = {}

    client = get_http_client()
    # Get creatives with revenue data
    response = await client.get(
        f"{rest_url}/creatives?revenue=not.is.null&select=id,revenue",
        headers=headers,
    )

    if response.status_code != 200:
        return revenue_stats

    creatives = response.json()
    creative_revenues = {c["id"]: float(c.get("revenue") or 0) for c in creatives}
    creative_ids = list(creative_revenues.keys())

    if not creative_ids:
        return revenue_stats

    # Get decomposed components for these creatives
    creative_list = ",".join(f'"{cid}"' for cid in creative_ids[:100])
    response = await client.get(
        f"{rest_url}/decomposed_creatives"
        f"?creative_id=in.({creative_list})"
        f"&select=creative_id,payload",
        headers=headers,
    )

    if response.status_code != 200:
        return revenue_stats

    decomposed = response.json()

    # Aggregate revenue per component
    component_revenues: dict[tuple[str, str], list[float]] = {}

    for row in decomposed:
        creative_id = row.get("creative_id")
        payload = row.get("payload") or {}
        revenue = creative_revenues.get(creative_id, 0)

        for comp_type in COMPONENT_TYPES:
            comp_value = payload.get(comp_type)
            if comp_value:
                key = (comp_type, comp_value)
                if key not in component_revenues:
                    component_revenues[key] = []
                component_revenues[key].append(revenue)

    # Calculate averages
    for key, revenues in component_revenues.items():
        if revenues:
            revenue_stats[key] = sum(revenues) / len(revenues)

    return revenue_stats


async def generate_meta_dashboard(
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
) -> MetaDashboard:
    """
    Generate meta dashboard with HOT/COLD/GAPS analysis.

    Args:
        geo: Optional geo filter (e.g., "US", "EU")
        avatar_id: Optional avatar filter

    Returns:
        MetaDashboard with categorized components
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Get current week number
    week_num = datetime.utcnow().isocalendar()[1]

    # Fetch data
    learnings = await _get_component_learnings(rest_url, headers, geo, avatar_id)
    usage_counts = await _get_recent_usage(rest_url, headers)
    revenue_stats = await _get_revenue_stats(rest_url, headers)

    # Build component map
    components: dict[tuple[str, str], MetaComponent] = {}

    for row in learnings:
        comp_type = row.get("component_type")
        comp_value = row.get("component_value")

        if not comp_type or not comp_value:
            continue

        key = (comp_type, comp_value)
        win_rate = row.get("win_rate")
        if win_rate is not None:
            try:
                win_rate = float(win_rate)
            except (TypeError, ValueError):
                win_rate = None

        sample_size = row.get("sample_size") or 0

        components[key] = MetaComponent(
            component_type=comp_type,
            component_value=comp_value,
            win_rate=win_rate,
            sample_size=sample_size,
            usage_count=usage_counts.get(key, 0),
            revenue=revenue_stats.get(key, 0.0),
        )

    # Also add components that have usage but no learnings yet
    for key, usage in usage_counts.items():
        if key not in components:
            comp_type, comp_value = key
            components[key] = MetaComponent(
                component_type=comp_type,
                component_value=comp_value,
                usage_count=usage,
            )

    # Categorize components
    hot = []
    cold = []
    gaps = []

    for comp in components.values():
        if comp.is_hot:
            hot.append(comp)
        elif comp.is_fatigued and comp.sample_size >= MIN_SAMPLES_FOR_COLD:
            cold.append(comp)
        elif comp.is_gap and comp.sample_size > 0:
            # Only show gaps that have at least 1 sample (not completely untested)
            gaps.append(comp)

    # Sort: hot by win_rate DESC, cold by usage_count DESC, gaps by sample_size ASC
    hot.sort(key=lambda c: (c.win_rate or 0, c.revenue), reverse=True)
    cold.sort(key=lambda c: c.usage_count, reverse=True)
    gaps.sort(key=lambda c: c.sample_size)

    return MetaDashboard(
        geo=geo,
        avatar=avatar_id,
        week_num=week_num,
        hot_components=hot[:5],  # Top 5
        cold_components=cold[:3],  # Top 3
        gap_components=gaps[:3],  # Top 3
    )


def format_meta_dashboard_telegram(dashboard: MetaDashboard) -> str:
    """
    Format meta dashboard for Telegram display.

    Uses ASCII box format from VISION.md:

    ╔══════════════════════════════════════════╗
    ║  META DASHBOARD — DE / POT / Week 2      ║
    ╠══════════════════════════════════════════╣
    ║  HOT:                                    ║
    ║  ├── Hook: "confession" → 47%, $12.3    ║
    ║  └── Angle: "curiosity" → 42%, $14.1    ║
    ║                                          ║
    ║  COLD:                                   ║
    ║  └── Angle: "fear" → fatigue HIGH       ║
    ║                                          ║
    ║  GAPS:                                   ║
    ║  └── Mechanism: "new_tech" → 3 tests    ║
    ╚══════════════════════════════════════════╝
    """
    # Build header
    header_parts = ["DE"]
    if dashboard.geo:
        header_parts.append(dashboard.geo)
    if dashboard.avatar:
        header_parts.append(dashboard.avatar[:8])
    header_parts.append(f"Week {dashboard.week_num}")
    header_text = " / ".join(header_parts)

    lines = [
        f"<b>META DASHBOARD</b> — {header_text}",
        "",
    ]

    # HOT section
    if dashboard.hot_components:
        lines.append("🔥 <b>HOT:</b>")
        for i, comp in enumerate(dashboard.hot_components):
            is_last = i == len(dashboard.hot_components) - 1
            prefix = "└──" if is_last else "├──"
            win_pct = f"{comp.win_rate:.0%}" if comp.win_rate else "N/A"
            revenue_str = f"${comp.revenue:.1f}" if comp.revenue > 0 else ""
            value_display = comp.component_value[:12]

            if revenue_str:
                lines.append(
                    f'{prefix} {comp.display_type}: "{value_display}" → {win_pct}, {revenue_str}'
                )
            else:
                lines.append(f'{prefix} {comp.display_type}: "{value_display}" → {win_pct}')
    else:
        lines.append("🔥 <b>HOT:</b>")
        lines.append("└── <i>Нет данных</i>")

    lines.append("")

    # COLD section
    if dashboard.cold_components:
        lines.append("❄️ <b>COLD:</b>")
        for i, comp in enumerate(dashboard.cold_components):
            is_last = i == len(dashboard.cold_components) - 1
            prefix = "└──" if is_last else "├──"
            value_display = comp.component_value[:12]
            fatigue_level = "HIGH" if comp.usage_count >= 5 else "MED"
            lines.append(
                f'{prefix} {comp.display_type}: "{value_display}" → fatigue {fatigue_level}'
            )
    else:
        lines.append("❄️ <b>COLD:</b>")
        lines.append("└── <i>Нет усталых компонентов</i>")

    lines.append("")

    # GAPS section
    if dashboard.gap_components:
        lines.append("🕳️ <b>GAPS:</b>")
        for i, comp in enumerate(dashboard.gap_components):
            is_last = i == len(dashboard.gap_components) - 1
            prefix = "└──" if is_last else "├──"
            value_display = comp.component_value[:12]
            lines.append(
                f'{prefix} {comp.display_type}: "{value_display}" → {comp.sample_size} tests'
            )
    else:
        lines.append("🕳️ <b>GAPS:</b>")
        lines.append("└── <i>Все компоненты протестированы</i>")

    # Footer with timestamp
    lines.extend(
        [
            "",
            f"<i>🕐 {dashboard.generated_at.strftime('%H:%M UTC')}</i>",
        ]
    )

    return "\n".join(lines)
