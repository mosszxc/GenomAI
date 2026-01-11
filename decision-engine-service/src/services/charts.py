"""
Chart Generation Service

Generates charts for Telegram Admin Dashboard using QuickChart API.
"""

import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

import httpx


def generate_quickchart_url(config: dict, width: int = 500, height: int = 300) -> str:
    """
    Generate QuickChart URL from Chart.js configuration.

    Args:
        config: Chart.js configuration dict
        width: Chart width in pixels
        height: Chart height in pixels

    Returns:
        QuickChart URL for the chart image
    """
    chart_json = json.dumps(config)
    encoded = urllib.parse.quote(chart_json)
    return f"https://quickchart.io/chart?c={encoded}&w={width}&h={height}"


def build_win_rate_trend_chart(
    labels: list[str],
    datasets: list[dict],
    title: str = "Win Rate Trends",
) -> dict:
    """
    Build Chart.js config for win rate trend line chart.

    Args:
        labels: X-axis labels (dates)
        datasets: List of dataset configs with name, data, color

    Returns:
        Chart.js configuration dict
    """
    chart_datasets = []
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0"]

    for i, ds in enumerate(datasets):
        color = ds.get("color", colors[i % len(colors)])
        chart_datasets.append({
            "label": ds["name"],
            "data": ds["data"],
            "fill": False,
            "borderColor": color,
            "backgroundColor": color,
            "tension": 0.3,
            "pointRadius": 3,
        })

    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": chart_datasets,
        },
        "options": {
            "title": {
                "display": True,
                "text": title,
                "fontSize": 16,
            },
            "scales": {
                "yAxes": [{
                    "ticks": {
                        "min": 0,
                        "max": 100,
                    },
                    "scaleLabel": {
                        "display": True,
                        "labelString": "Win Rate %",
                    },
                }],
            },
            "legend": {
                "position": "bottom",
            },
        },
    }


async def get_component_win_rate_trends(
    supabase_url: str,
    supabase_key: str,
    days: int = 7,
    top_n: int = 5,
) -> tuple[list[str], list[dict]]:
    """
    Get win rate trends for top components.

    Returns labels (dates) and datasets for chart.
    """
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    # Get top components by sample_size
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{supabase_url}/rest/v1/component_learnings"
            f"?select=component_type,component_value,win_rate,sample_size"
            f"&sample_size=gt.0"
            f"&order=sample_size.desc"
            f"&limit={top_n}",
            headers=headers,
        )

        if response.status_code != 200:
            return [], []

        components = response.json()

    if not components:
        return [], []

    # Generate date labels for the period
    today = datetime.utcnow().date()
    labels = []
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        labels.append(date.strftime("%m/%d"))

    # Build datasets from components
    datasets = []
    for comp in components:
        win_rate = float(comp.get("win_rate", 0) or 0) * 100
        name = f"{comp['component_type']}:{comp['component_value'][:12]}"

        # For now, use static win_rate (historical tracking TBD)
        # Later: query daily snapshots for actual trends
        data = [win_rate] * days

        datasets.append({
            "name": name,
            "data": data,
        })

    return labels, datasets


async def get_emotion_win_rate_trends(
    supabase_url: str,
    supabase_key: str,
    days: int = 7,
) -> tuple[list[str], list[dict]]:
    """
    Get win rate trends for emotion_primary components.

    Returns labels (dates) and datasets for chart.
    """
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{supabase_url}/rest/v1/component_learnings"
            f"?component_type=eq.emotion_primary"
            f"&select=component_value,win_rate,sample_size"
            f"&sample_size=gt.0"
            f"&order=sample_size.desc"
            f"&limit=5",
            headers=headers,
        )

        if response.status_code != 200:
            return [], []

        components = response.json()

    if not components:
        return [], []

    # Generate date labels
    today = datetime.utcnow().date()
    labels = []
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        labels.append(date.strftime("%m/%d"))

    # Emotion-specific colors
    emotion_colors = {
        "fear": "#E91E63",
        "hope": "#4CAF50",
        "curiosity": "#2196F3",
        "urgency": "#FF9800",
        "desire": "#9C27B0",
        "frustration": "#F44336",
        "relief": "#00BCD4",
    }

    datasets = []
    for comp in components:
        emotion = comp["component_value"]
        win_rate = float(comp.get("win_rate", 0) or 0) * 100

        # Static win_rate for now
        data = [win_rate] * days

        datasets.append({
            "name": emotion.capitalize(),
            "data": data,
            "color": emotion_colors.get(emotion.lower(), "#607D8B"),
        })

    return labels, datasets


async def generate_win_rate_chart_url(
    supabase_url: str,
    supabase_key: str,
    chart_type: str = "emotions",
    days: int = 7,
) -> Optional[str]:
    """
    Generate complete chart URL for win rate trends.

    Args:
        supabase_url: Supabase URL
        supabase_key: Supabase service role key
        chart_type: "emotions" or "components"
        days: Number of days to show

    Returns:
        QuickChart URL or None if no data
    """
    if chart_type == "emotions":
        labels, datasets = await get_emotion_win_rate_trends(
            supabase_url, supabase_key, days
        )
        title = f"Emotion Win Rates ({days} days)"
    else:
        labels, datasets = await get_component_win_rate_trends(
            supabase_url, supabase_key, days
        )
        title = f"Top Component Win Rates ({days} days)"

    if not datasets:
        return None

    config = build_win_rate_trend_chart(labels, datasets, title)
    return generate_quickchart_url(config, width=600, height=350)
