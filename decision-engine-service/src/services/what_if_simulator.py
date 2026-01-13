"""
What-If Simulator Service

Predicts win rate for hypothetical component combinations before creating a hypothesis.
Based on historical performance of similar ideas.

Issue: #298 - Telegram Admin Dashboard - What-If Simulator
"""

import os
import re
from typing import Optional
from src.core.http_client import get_http_client

SCHEMA = "genomai"

# Confidence thresholds based on sample size
CONFIDENCE_THRESHOLDS = {
    "low": 10,  # <10 samples
    "medium": 30,  # 10-30 samples
    "high": 100,  # >30 samples
}

# Minimum samples to make a prediction
MIN_SAMPLES_FOR_PREDICTION = 3


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


def parse_components(text: str) -> list[str]:
    """
    Parse component values from user input.

    Examples:
        "fear + question + ugc" -> ["fear", "question", "ugc"]
        "hope, curiosity, testimonial" -> ["hope", "curiosity", "testimonial"]
        "fear question ugc" -> ["fear", "question", "ugc"]
    """
    # Remove /simulate prefix if present
    text = re.sub(r"^/simulate\s*", "", text, flags=re.IGNORECASE)

    # Split by common separators
    components = re.split(r"[+,\s]+", text)

    # Clean and filter
    components = [c.strip().lower() for c in components if c.strip()]

    return components


async def identify_component_types(components: list[str]) -> dict[str, str]:
    """
    Identify component_type for each component_value.

    Returns:
        {"fear": "emotion_primary", "question": "opening_type", ...}
    """
    if not components:
        return {}

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Query component_learnings for these values
    values_list = ",".join(f'"{v}"' for v in components)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?component_value=in.({values_list})"
        f"&avatar_id=is.null"
        f"&select=component_type,component_value"
        f"&order=sample_size.desc",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    # Map value -> type (take first occurrence, highest sample_size)
    result = {}
    for row in data:
        value = row.get("component_value")
        comp_type = row.get("component_type")
        if value and comp_type and value not in result:
            result[value] = comp_type

    return result


async def find_similar_ideas(
    components: list[str],
    component_types: dict[str, str],
    geo: Optional[str] = None,
) -> dict:
    """
    Find historical ideas with similar component combinations.

    Uses Jaccard similarity: intersection / union of components.

    Returns:
        {
            "similar_ideas": [{"idea_id": ..., "test_result": ..., "similarity": ...}],
            "exact_matches": int,
            "partial_matches": int,
        }
    """
    if not components:
        return {"similar_ideas": [], "exact_matches": 0, "partial_matches": 0}

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build JSONB contains filters for each component
    # We'll search for creatives that have at least one of the components
    similar_ideas = []

    client = get_http_client()
    # Get decomposed creatives
    response = await client.get(
        f"{rest_url}/decomposed_creatives?select=creative_id,idea_id,payload&limit=200",
        headers=headers,
    )
    response.raise_for_status()
    decomposed = response.json()

    if not decomposed:
        return {"similar_ideas": [], "exact_matches": 0, "partial_matches": 0}

    # Get creatives with test results
    creative_ids = list(set(d["creative_id"] for d in decomposed if d.get("creative_id")))
    if not creative_ids:
        return {"similar_ideas": [], "exact_matches": 0, "partial_matches": 0}

    creative_list = ",".join(f'"{cid}"' for cid in creative_ids[:100])

    filter_parts = [f"id=in.({creative_list})", "test_result=not.is.null"]
    if geo:
        filter_parts.append(f"target_geo=eq.{geo}")

    response = await client.get(
        f"{rest_url}/creatives?{'&'.join(filter_parts)}&select=id,test_result,idea_id",
        headers=headers,
    )
    response.raise_for_status()
    creatives = response.json()

    # Build creative_id -> test_result map
    creative_results = {c["id"]: c.get("test_result") for c in creatives}

    # Calculate similarity for each decomposed creative
    exact_matches = 0
    partial_matches = 0

    input_components_set = set(components)

    for dc in decomposed:
        creative_id = dc.get("creative_id")
        if creative_id not in creative_results:
            continue

        payload = dc.get("payload") or {}

        # Extract component values from payload
        creative_components = set()
        for _comp_type, comp_value in payload.items():
            if isinstance(comp_value, str):
                creative_components.add(comp_value.lower())

        # Calculate Jaccard similarity
        intersection = input_components_set & creative_components
        union = input_components_set | creative_components

        if not union:
            continue

        similarity = len(intersection) / len(union)

        # Only include if at least one component matches
        if not intersection:
            continue

        test_result = creative_results.get(creative_id)
        idea_id = dc.get("idea_id")

        similar_ideas.append(
            {
                "idea_id": idea_id,
                "creative_id": creative_id,
                "test_result": test_result,
                "similarity": similarity,
                "matching_components": list(intersection),
            }
        )

        if similarity == 1.0:
            exact_matches += 1
        else:
            partial_matches += 1

    # Sort by similarity
    similar_ideas.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "similar_ideas": similar_ideas[:20],  # Top 20
        "exact_matches": exact_matches,
        "partial_matches": partial_matches,
    }


async def get_component_stats(
    components: list[str],
    component_types: dict[str, str],
    geo: Optional[str] = None,
) -> dict[str, dict]:
    """
    Get individual component performance stats.

    Returns:
        {
            "fear": {"win_rate": 0.25, "sample_size": 15, "component_type": "emotion_primary"},
            ...
        }
    """
    if not components:
        return {}

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    values_list = ",".join(f'"{v}"' for v in components)

    filters = [
        f"component_value=in.({values_list})",
        "avatar_id=is.null",
    ]

    # If geo specified, filter by it; otherwise get all geos
    if geo:
        filters.append(f"geo=eq.{geo}")

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?{'&'.join(filters)}"
        f"&select=component_type,component_value,win_rate,sample_size",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    # Aggregate data across geos for each component
    aggregated = {}
    for row in data:
        value = row.get("component_value")
        if not value:
            continue

        win_rate = row.get("win_rate")
        sample_size = row.get("sample_size") or 0

        if win_rate is not None:
            try:
                win_rate = float(win_rate)
            except (TypeError, ValueError):
                win_rate = None

        if value not in aggregated:
            aggregated[value] = {
                "total_wins": 0,
                "total_samples": 0,
                "component_type": row.get("component_type"),
            }

        # Aggregate: sum samples and weighted wins
        if win_rate is not None and sample_size > 0:
            aggregated[value]["total_wins"] += win_rate * sample_size
            aggregated[value]["total_samples"] += sample_size

    # Convert aggregated to final stats
    stats = {}
    for value, agg in aggregated.items():
        total_samples = agg["total_samples"]
        if total_samples > 0:
            win_rate = agg["total_wins"] / total_samples
        else:
            win_rate = None

        stats[value] = {
            "win_rate": win_rate,
            "sample_size": total_samples,
            "component_type": agg["component_type"],
        }

    # Add entries for components not found in learnings
    for comp in components:
        if comp not in stats:
            stats[comp] = {
                "win_rate": None,
                "sample_size": 0,
                "component_type": component_types.get(comp, "unknown"),
            }

    return stats


def calculate_predicted_win_rate(
    similar_ideas: list[dict],
    component_stats: dict[str, dict],
) -> tuple[Optional[float], Optional[float], int]:
    """
    Calculate predicted win rate based on similar ideas and component stats.

    Uses weighted average:
    1. Similar ideas (weighted by similarity) - 60%
    2. Component averages - 40%

    Returns:
        (predicted_rate, confidence_range, sample_size)
        e.g., (0.35, 0.07, 15) means 35% ± 7% based on 15 samples
    """
    # Method 1: From similar ideas
    total_weight = 0.0
    weighted_wins = 0.0

    for idea in similar_ideas:
        similarity = idea.get("similarity", 0)
        result = idea.get("test_result")

        if result in ("win", "loss"):
            total_weight += similarity
            if result == "win":
                weighted_wins += similarity

    ideas_win_rate = None
    ideas_sample = len([i for i in similar_ideas if i.get("test_result") in ("win", "loss")])

    if total_weight > 0:
        ideas_win_rate = weighted_wins / total_weight

    # Method 2: From component averages
    component_rates = []
    for _comp, stats in component_stats.items():
        win_rate = stats.get("win_rate")
        sample = stats.get("sample_size", 0)
        if win_rate is not None and sample >= MIN_SAMPLES_FOR_PREDICTION:
            component_rates.append(win_rate)

    component_avg = None
    if component_rates:
        component_avg = sum(component_rates) / len(component_rates)

    # Combine methods
    if ideas_win_rate is not None and component_avg is not None:
        # Weighted combination
        predicted = ideas_win_rate * 0.6 + component_avg * 0.4
    elif ideas_win_rate is not None:
        predicted = ideas_win_rate
    elif component_avg is not None:
        predicted = component_avg
    else:
        return None, None, 0

    # Calculate confidence range based on sample size
    total_samples = ideas_sample + sum(s.get("sample_size", 0) for s in component_stats.values())

    # Confidence interval approximation (simplified Wilson score)
    if total_samples < 5:
        confidence_range = 0.25  # ±25%
    elif total_samples < 15:
        confidence_range = 0.15  # ±15%
    elif total_samples < 30:
        confidence_range = 0.10  # ±10%
    elif total_samples < 50:
        confidence_range = 0.07  # ±7%
    else:
        confidence_range = 0.05  # ±5%

    return predicted, confidence_range, total_samples


def get_confidence_level(sample_size: int) -> str:
    """Get confidence level based on sample size."""
    if sample_size < CONFIDENCE_THRESHOLDS["low"]:
        return "low"
    elif sample_size < CONFIDENCE_THRESHOLDS["medium"]:
        return "medium"
    else:
        return "high"


def identify_risk_factors(
    components: list[str],
    component_stats: dict[str, dict],
) -> list[str]:
    """
    Identify potential risk factors for the combination.

    Returns list of risk factor descriptions.
    """
    risks = []

    for comp, stats in component_stats.items():
        sample_size = stats.get("sample_size", 0)
        win_rate = stats.get("win_rate")

        # Low sample size
        if sample_size < MIN_SAMPLES_FOR_PREDICTION:
            risks.append(f"<code>{comp}</code> has insufficient data (n={sample_size})")
        elif sample_size < 10:
            risks.append(f"<code>{comp}</code> has low sample size (n={sample_size})")

        # Low win rate
        if win_rate is not None and win_rate < 0.15:
            risks.append(f"<code>{comp}</code> has low historical win rate ({win_rate:.0%})")

    # Check for potentially conflicting components (example heuristic)
    if len(components) > 4:
        risks.append("Many components may reduce clarity of message")

    return risks


async def simulate_combination(
    components: list[str],
    geo: Optional[str] = None,
) -> dict:
    """
    Main simulation function.

    Returns:
        {
            "components": ["fear", "question", "ugc"],
            "predicted_win_rate": 0.35,
            "confidence_range": 0.07,
            "confidence_level": "medium",
            "sample_size": 15,
            "similar_ideas_count": 12,
            "risk_factors": ["ugc has low sample size", ...],
            "component_stats": {...},
        }
    """
    if not components:
        return {
            "error": "No components provided",
            "components": [],
        }

    # Step 1: Identify component types
    component_types = await identify_component_types(components)

    # Step 2: Get component stats
    component_stats = await get_component_stats(components, component_types, geo)

    # Step 3: Find similar ideas
    similar_result = await find_similar_ideas(components, component_types, geo)
    similar_ideas = similar_result["similar_ideas"]

    # Step 4: Calculate predicted win rate
    predicted, confidence_range, sample_size = calculate_predicted_win_rate(
        similar_ideas, component_stats
    )

    # Step 5: Get confidence level
    confidence_level = get_confidence_level(sample_size)

    # Step 6: Identify risk factors
    risk_factors = identify_risk_factors(components, component_stats)

    # Get top similar idea IDs for display
    top_similar = [
        idea.get("idea_id")[:8] if idea.get("idea_id") else "unknown" for idea in similar_ideas[:3]
    ]

    return {
        "components": components,
        "component_types": component_types,
        "predicted_win_rate": predicted,
        "confidence_range": confidence_range,
        "confidence_level": confidence_level,
        "sample_size": sample_size,
        "similar_ideas_count": len(similar_ideas),
        "exact_matches": similar_result["exact_matches"],
        "partial_matches": similar_result["partial_matches"],
        "top_similar_ids": top_similar,
        "risk_factors": risk_factors,
        "component_stats": component_stats,
        "geo": geo,
    }


def format_simulation_telegram(result: dict) -> str:
    """
    Format simulation result for Telegram display.

    Example output:
        🧪 Simulation Result

        Predicted win rate: 38-52%
        Confidence: medium (на основе 12 похожих идей)
        Similar past ideas: #A1B2, #C3D4

        Risk factors:
        ├── ugc has low sample size
        └── hope may be fatigued in US
    """
    if result.get("error"):
        return f"❌ <b>Ошибка симуляции</b>\n\n{result['error']}"

    components = result.get("components", [])
    predicted = result.get("predicted_win_rate")
    confidence_range = result.get("confidence_range")
    confidence_level = result.get("confidence_level", "unknown")
    similar_count = result.get("similar_ideas_count", 0)
    top_similar = result.get("top_similar_ids", [])
    risk_factors = result.get("risk_factors", [])
    component_stats = result.get("component_stats", {})
    geo = result.get("geo")

    lines = ["🧪 <b>Результат симуляции</b>", ""]

    # Components being simulated
    comp_display = " + ".join(f"<code>{c}</code>" for c in components)
    lines.append(f"<b>Компоненты:</b> {comp_display}")
    if geo:
        lines.append(f"<b>Гео:</b> {geo}")
    lines.append("")

    # Predicted win rate
    if predicted is not None:
        low = max(0, predicted - confidence_range) if confidence_range else predicted
        high = min(1, predicted + confidence_range) if confidence_range else predicted

        lines.append(f"<b>Прогноз конверсии:</b> {low:.0%}-{high:.0%}")

        # Confidence emoji
        confidence_emoji = {"low": "🔴", "medium": "🟡", "high": "🟢"}.get(confidence_level, "⚪")
        lines.append(
            f"<b>Уверенность:</b> {confidence_emoji} {confidence_level} "
            f"(на основе {similar_count} похожих идей)"
        )
    else:
        lines.append("<b>Прогноз конверсии:</b> <i>Недостаточно данных</i>")
        lines.append("<b>Уверенность:</b> 🔴 low (нужно больше исторических данных)")

    # Similar ideas
    if top_similar:
        similar_str = ", ".join(f"#{sid}" for sid in top_similar)
        lines.append(f"<b>Похожие идеи:</b> {similar_str}")

    lines.append("")

    # Component breakdown
    lines.append("<b>Разбивка по компонентам:</b>")
    for comp, stats in component_stats.items():
        win_rate = stats.get("win_rate")
        sample = stats.get("sample_size", 0)
        comp_type = stats.get("component_type", "")

        if win_rate is not None:
            rate_str = f"{win_rate:.0%}"
            if win_rate >= 0.30:
                emoji = "🟢"
            elif win_rate >= 0.15:
                emoji = "🟡"
            else:
                emoji = "🔴"
        else:
            rate_str = "N/A"
            emoji = "⬜"

        type_short = comp_type[:10] if comp_type else ""
        lines.append(f"  {emoji} <code>{comp}</code> ({type_short}): {rate_str} (n={sample})")

    # Risk factors
    if risk_factors:
        lines.append("")
        lines.append("<b>Факторы риска:</b>")
        for i, risk in enumerate(risk_factors):
            prefix = "└──" if i == len(risk_factors) - 1 else "├──"
            lines.append(f"{prefix} {risk}")

    return "\n".join(lines)
