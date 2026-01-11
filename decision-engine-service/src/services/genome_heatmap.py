"""
Genome Heatmap Service

Generates component performance matrix (heatmap) showing win rates
by component × geography.

Issue: #293 - base heatmap
Issue: #296 - segmented analysis (--by geo/avatar/week)
"""

import os
from datetime import datetime, timedelta
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
            "🧬 <b>Матрица компонентов</b>\n\n"
            f"<i>Нет данных для {component_type}</i>\n\n"
            "Нужно минимум 3 семпла для отображения."
        )

    title = title or "Матрица компонентов"

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
            f"<i>Тип: {component_type}</i>",
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
    types = list(
        set(row.get("component_type") for row in data if row.get("component_type"))
    )
    return sorted(types)


async def get_segmented_analysis(
    component_value: str,
    segment_by: str = "geo",
    component_type: str = "emotion_primary",
) -> dict:
    """
    Get segmented analysis for a specific component value.

    Args:
        component_value: The component to analyze (e.g., "fear", "hope")
        segment_by: Segment dimension - "geo", "аватарам", or "week"
        component_type: Type of component (default: emotion_primary)

    Returns:
        {
            "component_value": "fear",
            "segment_by": "geo",
            "segments": [
                {"сегментам": "US", "win_rate": 0.15, "sample_size": 10},
                {"сегментам": "EU", "win_rate": 0.22, "sample_size": 5},
            ],
            "insight": "fear лучше работает в EU"
        }
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    segments = []

    if segment_by == "geo":
        segments = await _get_segments_by_geo(
            rest_url, headers, component_value, component_type
        )
    elif segment_by == "аватарам":
        segments = await _get_segments_by_avatar(
            rest_url, headers, component_value, component_type
        )
    elif segment_by == "week":
        segments = await _get_segments_by_week(
            rest_url, headers, component_value, component_type
        )

    # Generate insight
    insight = _generate_insight(component_value, segment_by, segments)

    return {
        "component_value": component_value,
        "component_type": component_type,
        "segment_by": segment_by,
        "segments": segments,
        "insight": insight,
    }


async def _get_segments_by_geo(
    rest_url: str, headers: dict, component_value: str, component_type: str
) -> list[dict]:
    """Get segments by geography from component_learnings."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/component_learnings"
            f"?component_type=eq.{component_type}"
            f"&component_value=eq.{component_value}"
            f"&avatar_id=is.null"
            f"&select=geo,win_rate,sample_size"
            f"&order=sample_size.desc"
            f"&limit=10",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    segments = []
    for row in data:
        geo = row.get("geo") or "GLOBAL"
        win_rate = row.get("win_rate")
        sample_size = row.get("sample_size") or 0

        if win_rate is not None:
            try:
                win_rate = float(win_rate)
            except (TypeError, ValueError):
                win_rate = None

        segments.append(
            {
                "сегментам": geo,
                "win_rate": win_rate,
                "sample_size": sample_size,
            }
        )

    return segments


async def _get_segments_by_avatar(
    rest_url: str, headers: dict, component_value: str, component_type: str
) -> list[dict]:
    """Get segments by avatar from component_learnings + avatars."""
    async with httpx.AsyncClient() as client:
        # Get component learnings with avatar_id
        response = await client.get(
            f"{rest_url}/component_learnings"
            f"?component_type=eq.{component_type}"
            f"&component_value=eq.{component_value}"
            f"&avatar_id=not.is.null"
            f"&select=avatar_id,win_rate,sample_size,geo"
            f"&order=sample_size.desc"
            f"&limit=10",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        # Get avatar names
        avatar_ids = list(
            set(row.get("avatar_id") for row in data if row.get("avatar_id"))
        )
        avatar_names = {}

        if avatar_ids:
            avatar_list = ",".join(f'"{aid}"' for aid in avatar_ids)
            avatars_resp = await client.get(
                f"{rest_url}/avatars?id=in.({avatar_list})&select=id,name",
                headers=headers,
            )
            if avatars_resp.status_code == 200:
                avatars = avatars_resp.json()
                avatar_names = {a["id"]: a.get("name", "Unknown") for a in avatars}

    segments = []
    for row in data:
        avatar_id = row.get("avatar_id")
        avatar_name = avatar_names.get(
            avatar_id, avatar_id[:8] if avatar_id else "Unknown"
        )
        win_rate = row.get("win_rate")
        sample_size = row.get("sample_size") or 0

        if win_rate is not None:
            try:
                win_rate = float(win_rate)
            except (TypeError, ValueError):
                win_rate = None

        segments.append(
            {
                "сегментам": avatar_name,
                "win_rate": win_rate,
                "sample_size": sample_size,
            }
        )

    return segments


async def _get_segments_by_week(
    rest_url: str, headers: dict, component_value: str, component_type: str
) -> list[dict]:
    """
    Get segments by week.

    Aggregates from decomposed_creatives + creatives since
    component_learnings doesn't have time dimension.
    """
    # Calculate date range (last 4 weeks)
    now = datetime.utcnow()
    weeks_ago = now - timedelta(weeks=4)

    async with httpx.AsyncClient() as client:
        # Use RPC for complex aggregation
        # Fall back to simple query joining tables
        response = await client.get(
            f"{rest_url}/rpc/get_component_weekly_stats"
            f"?component_type={component_type}"
            f"&component_value={component_value}"
            f"&weeks=4",
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            return [
                {
                    "сегментам": row.get("week_label", "Unknown"),
                    "win_rate": float(row["win_rate"]) if row.get("win_rate") else None,
                    "sample_size": row.get("sample_size", 0),
                }
                for row in data
            ]

        # Fallback: aggregate client-side if RPC doesn't exist
        # Get creatives with test results in date range
        response = await client.get(
            f"{rest_url}/creatives"
            f"?test_result=not.is.null"
            f"&concluded_at=gte.{weeks_ago.isoformat()}"
            f"&select=id,test_result,concluded_at,idea_id",
            headers=headers,
        )
        if response.status_code != 200:
            return []

        creatives = response.json()
        creative_ids = [c["id"] for c in creatives]

        if not creative_ids:
            return []

        # Get decomposed components for these creatives
        creative_list = ",".join(f'"{cid}"' for cid in creative_ids[:50])  # Limit
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?creative_id=in.({creative_list})"
            f"&select=creative_id,payload",
            headers=headers,
        )
        if response.status_code != 200:
            return []

        decomposed = response.json()

    # Build creative_id -> test_result, concluded_at mapping
    creative_map = {
        c["id"]: {
            "result": c["test_result"],
            "week": _get_week_label(c.get("concluded_at")),
        }
        for c in creatives
    }

    # Aggregate by week
    week_stats = {}
    for row in decomposed:
        creative_id = row.get("creative_id")
        payload = row.get("payload") or {}

        # Check if this creative has the component
        component_val = payload.get(component_type)
        if component_val != component_value:
            continue

        info = creative_map.get(creative_id)
        if not info:
            continue

        week = info["week"]
        result = info["result"]

        if week not in week_stats:
            week_stats[week] = {"wins": 0, "total": 0}

        week_stats[week]["total"] += 1
        if result == "win":
            week_stats[week]["wins"] += 1

    # Convert to segments
    segments = []
    for week in sorted(week_stats.keys(), reverse=True):
        stats = week_stats[week]
        win_rate = stats["wins"] / stats["total"] if stats["total"] > 0 else None
        segments.append(
            {
                "сегментам": week,
                "win_rate": win_rate,
                "sample_size": stats["total"],
            }
        )

    return segments[:4]  # Last 4 weeks


def _get_week_label(concluded_at: Optional[str]) -> str:
    """Convert timestamp to week label."""
    if not concluded_at:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(concluded_at.replace("Z", "+00:00"))
        # ISO week format: "W01", "W02", etc.
        return f"W{dt.isocalendar()[1]:02d}"
    except (TypeError, ValueError):
        return "Unknown"


def _generate_insight(
    component_value: str, segment_by: str, segments: list[dict]
) -> str:
    """Generate insight text based on segment data."""
    if not segments:
        return f"Нет данных для {component_value}"

    # Filter segments with valid data
    valid_segments = [
        s
        for s in segments
        if s.get("win_rate") is not None and s.get("sample_size", 0) >= MIN_SAMPLE_SIZE
    ]

    if not valid_segments:
        return f"Недостаточно данных для {component_value} (нужно ≥{MIN_SAMPLE_SIZE} семплов)"

    # Find best performing segment
    best = max(valid_segments, key=lambda s: s["win_rate"])
    worst = min(valid_segments, key=lambda s: s["win_rate"])

    segment_type = {
        "geo": "географии",
        "аватарам": "аватарам",
        "week": "периодам",
    }.get(segment_by, "сегментам")

    if best["win_rate"] == worst["win_rate"]:
        return f"{component_value} стабилен по {segment_type}s"

    return (
        f"{component_value} лучше работает в {best['segment']} ({best['win_rate']:.0%})"
    )


def format_segmented_telegram(data: dict) -> str:
    """
    Format segmented analysis for Telegram display.

    Input format:
        {
            "component_value": "fear",
            "segment_by": "geo",
            "segments": [...],
            "insight": "..."
        }
    """
    component_value = data.get("component_value", "unknown")
    segment_by = data.get("segment_by", "geo")
    segments = data.get("segments", [])
    insight = data.get("insight", "")

    # Segment type emoji
    emoji_map = {
        "geo": "🌍",
        "аватарам": "👤",
        "week": "📅",
    }
    header_emoji = emoji_map.get(segment_by, "📊")

    # Segment type label
    label_map = {
        "geo": "Гео",
        "аватарам": "Аватар",
        "week": "Неделя",
    }
    header_label = label_map.get(segment_by, segment_by.title())

    if not segments:
        return (
            f"{header_emoji} <b>{component_value}</b> по {header_label}\n\n"
            f"<i>Данных нет</i>"
        )

    lines = [
        f"{header_emoji} <b>{component_value}</b> по {header_label}",
        "",
    ]

    for seg in segments:
        segment_name = seg.get("сегментам", "Unknown")
        win_rate = seg.get("win_rate")
        sample_size = seg.get("sample_size", 0)

        # Format win rate
        if win_rate is None or sample_size < MIN_SAMPLE_SIZE:
            rate_str = "N/A"
            emoji = EMOJI_NO_DATA
        else:
            rate_str = f"{win_rate:.0%}"
            emoji = get_win_rate_emoji(win_rate, sample_size)

        # Pad segment name
        seg_display = segment_name[:12].ljust(12)

        lines.append(f"<code>{seg_display}</code> {rate_str} (n={sample_size}) {emoji}")

    # Add insight
    if insight:
        lines.extend(["", f"<i>💡 {insight}</i>"])

    return "\n".join(lines)
