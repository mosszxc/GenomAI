"""
Genome Heatmap Service

Generates component performance matrix (heatmap) showing win rates
by component × geography.

Issue: #293
"""

import os
from typing import Optional
import httpx

SCHEMA = "genomai"

# Win rate thresholds for color coding
THRESHOLD_GREEN = 0.30  # >30% = green
THRESHOLD_YELLOW = 0.15  # 15-30% = yellow
# <15% = red

# Emoji for win rate levels
EMOJI_GREEN = "🟢"
EMOJI_YELLOW = "🟡"
EMOJI_RED = "🔴"
EMOJI_NO_DATA = "⬜"

# Minimum sample size to show data
MIN_SAMPLE_SIZE = 3


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


def get_win_rate_emoji(win_rate: Optional[float], sample_size: int) -> str:
    """Get emoji for win rate level."""
    if sample_size < MIN_SAMPLE_SIZE or win_rate is None:
        return EMOJI_NO_DATA
    if win_rate >= THRESHOLD_GREEN:
        return EMOJI_GREEN
    if win_rate >= THRESHOLD_YELLOW:
        return EMOJI_YELLOW
    return EMOJI_RED


async def get_heatmap_data(
    component_type: str = "emotion_primary",
    avatar_id: Optional[str] = None,
) -> dict:
    """
    Get heatmap data for a specific component type.

    Returns:
        {
            "component_type": "emotion_primary",
            "geos": ["US", "EU", "LATAM"],
            "components": ["fear", "hope", "curiosity"],
            "matrix": {
                "fear": {"US": 0.15, "EU": 0.22, "LATAM": 0.08},
                "hope": {"US": 0.35, "EU": 0.31, "LATAM": 0.25},
                ...
            },
            "sample_sizes": {
                "fear": {"US": 10, "EU": 5, "LATAM": 12},
                ...
            }
        }
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build query
    filters = [f"component_type=eq.{component_type}"]
    if avatar_id:
        filters.append(f"avatar_id=eq.{avatar_id}")
    else:
        filters.append("avatar_id=is.null")  # Global only

    filter_str = "&".join(filters)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/component_learnings"
            f"?{filter_str}"
            f"&select=component_value,geo,win_rate,sample_size"
            f"&order=sample_size.desc",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    # Process data into matrix format
    geos = set()
    components = set()
    matrix = {}
    sample_sizes = {}

    for row in data:
        component_value = row.get("component_value")
        geo = row.get("geo")
        win_rate = row.get("win_rate")
        sample_size = row.get("sample_size") or 0

        if not component_value:
            continue

        # Handle NULL geo as "GLOBAL"
        geo = geo or "GLOBAL"

        geos.add(geo)
        components.add(component_value)

        if component_value not in matrix:
            matrix[component_value] = {}
            sample_sizes[component_value] = {}

        # Convert win_rate to float
        if win_rate is not None:
            try:
                win_rate = float(win_rate)
            except (TypeError, ValueError):
                win_rate = None

        matrix[component_value][geo] = win_rate
        sample_sizes[component_value][geo] = sample_size

    # Sort geos and components for consistent display
    sorted_geos = sorted(geos)
    sorted_components = sorted(components)

    return {
        "component_type": component_type,
        "geos": sorted_geos,
        "components": sorted_components,
        "matrix": matrix,
        "sample_sizes": sample_sizes,
    }


def format_heatmap_telegram(data: dict, title: Optional[str] = None) -> str:
    """
    Format heatmap data for Telegram display.

    Returns formatted string with emoji grid.
    """
    geos = data.get("geos", [])
    components = data.get("components", [])
    matrix = data.get("matrix", {})
    sample_sizes = data.get("sample_sizes", {})
    component_type = data.get("component_type", "unknown")

    if not geos or not components:
        return (
            "🧬 <b>Component Performance Matrix</b>\n\n"
            f"<i>No data for {component_type}</i>\n\n"
            "Components need at least 3 samples to appear."
        )

    title = title or "Component Performance Matrix"

    # Limit display to top 6 components by total sample size
    component_totals = {}
    for comp in components:
        total = sum(sample_sizes.get(comp, {}).values())
        component_totals[comp] = total

    top_components = sorted(
        components, key=lambda c: component_totals.get(c, 0), reverse=True
    )[:6]

    # Limit to top 5 geos by total samples
    geo_totals = {}
    for geo in geos:
        total = 0
        for comp in components:
            total += sample_sizes.get(comp, {}).get(geo, 0)
        geo_totals[geo] = total

    top_geos = sorted(geos, key=lambda g: geo_totals.get(g, 0), reverse=True)[:5]

    # Build header row
    # Calculate column width (max 6 chars for geo)
    col_width = 6
    header_row = " " * 12  # Space for component names
    for geo in top_geos:
        header_row += geo[:col_width].center(col_width)

    lines = [
        f"🧬 <b>{title}</b>",
        "",
        f"<code>{header_row}</code>",
    ]

    # Build data rows
    for comp in top_components:
        # Truncate component name to 10 chars
        comp_display = comp[:10].ljust(12)

        row = f"<code>{comp_display}"
        for geo in top_geos:
            win_rate = matrix.get(comp, {}).get(geo)
            sample = sample_sizes.get(comp, {}).get(geo, 0)
            emoji = get_win_rate_emoji(win_rate, sample)
            row += emoji.center(col_width - 1) + " "
        row += "</code>"
        lines.append(row)

    # Legend
    lines.extend(
        [
            "",
            f"{EMOJI_GREEN} &gt;30%  {EMOJI_YELLOW} 15-30%  {EMOJI_RED} &lt;15%  {EMOJI_NO_DATA} &lt;3 samples",
            "",
            f"<i>Type: {component_type}</i>",
        ]
    )

    return "\n".join(lines)


async def get_available_component_types() -> list[str]:
    """Get list of component types with data."""
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/component_learnings"
            f"?avatar_id=is.null"
            f"&select=component_type"
            f"&order=component_type",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    # Get unique component types
    types = list(set(row.get("component_type") for row in data if row.get("component_type")))
    return sorted(types)
