"""
Auto-Recommendation Service

Generates "Today's Best Bet" - optimal component combination
based on current learnings, fatigue state, and discovered correlations.

Issue: #299 - Telegram Admin Dashboard - Auto-Recommendations

Different from DailyRecommendationWorkflow:
- For admin insight, not buyer delivery
- Shows reasoning and explanation
- Factors in correlations (synergies/conflicts)
- Considers component freshness (usage frequency as fatigue proxy)
"""

import os
from dataclasses import dataclass, field
from src.core.http_client import get_http_client

from src.services.correlation_discovery import (
    discover_correlations,
    Correlation,
)

SCHEMA = "genomai"

# Component types to recommend (ordered by importance)
RECOMMEND_COMPONENT_TYPES = [
    "emotion_primary",
    "angle_type",
    "source_type",
    "opening_type",
    "message_structure",
    "promise_type",
]

# Minimum samples for confident recommendation
MIN_SAMPLES_FOR_CONFIDENCE = 5
HIGH_CONFIDENCE_SAMPLES = 15

# Freshness penalty: components used recently get penalty
FRESHNESS_WINDOW_DAYS = 7
MAX_USAGE_BEFORE_FATIGUE = 3  # More than 3 uses in 7 days = fatigued


@dataclass
class ComponentScore:
    """Score for a single component."""

    component_type: str
    component_value: str
    base_win_rate: float
    sample_size: int
    synergy_bonus: float = 0.0
    conflict_penalty: float = 0.0
    freshness_score: float = 1.0  # 1.0 = fresh, 0.5 = fatigued
    final_score: float = 0.0
    confidence: str = "low"  # low, medium, high
    reasoning: list[str] = field(default_factory=list)

    def calculate_final_score(self):
        """Calculate final score with all adjustments."""
        # Base score from конверсия
        self.final_score = self.base_win_rate

        # Apply synergy bonus (additive)
        self.final_score += self.synergy_bonus

        # Apply conflict penalty (subtractive)
        self.final_score -= self.conflict_penalty

        # Apply freshness multiplier
        self.final_score *= self.freshness_score

        # Clamp to [0, 1]
        self.final_score = max(0.0, min(1.0, self.final_score))

        # Calculate confidence
        if self.sample_size >= HIGH_CONFIDENCE_SAMPLES:
            self.confidence = "high"
        elif self.sample_size >= MIN_SAMPLES_FOR_CONFIDENCE:
            self.confidence = "medium"
        else:
            self.confidence = "low"


@dataclass
class BestBetRecommendation:
    """Complete best bet recommendation."""

    components: list[ComponentScore]
    expected_win_rate: float
    overall_confidence: str
    reasoning: list[str]
    synergies_applied: list[str]
    conflicts_avoided: list[str]
    fatigued_components: list[str]


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


async def get_component_learnings(
    component_type: str,
    min_samples: int = MIN_SAMPLES_FOR_CONFIDENCE,
) -> list[dict]:
    """
    Get component learnings for a specific type.

    Returns components sorted by win_rate DESC.
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/component_learnings"
        f"?component_type=eq.{component_type}"
        f"&sample_size=gte.{min_samples}"
        f"&select=component_value,win_rate,sample_size"
        f"&order=win_rate.desc"
        f"&limit=10",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_recent_usage() -> dict[tuple[str, str], int]:
    """
    Get component usage counts in last 7 days.

    Returns: {(component_type, component_value): usage_count}
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    usage_counts: dict[tuple[str, str], int] = {}

    client = get_http_client()
    # Get recent decomposed creatives
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
        for comp_type in RECOMMEND_COMPONENT_TYPES:
            comp_value = payload.get(comp_type)
            if comp_value:
                key = (comp_type, comp_value)
                usage_counts[key] = usage_counts.get(key, 0) + 1

    return usage_counts


def calculate_freshness_score(usage_count: int) -> float:
    """
    Calculate freshness score based on recent usage.

    - 0 uses: 1.0 (completely fresh)
    - 1-2 uses: 0.9 (slightly used)
    - 3+ uses: 0.5 (fatigued)
    """
    if usage_count == 0:
        return 1.0
    elif usage_count <= 2:
        return 0.9
    else:
        return 0.5


async def generate_best_bet() -> BestBetRecommendation:
    """
    Generate the "Today's Best Bet" recommendation.

    Algorithm:
    1. Get top components by win_rate for each type
    2. Fetch discovered correlations
    3. Apply synergy bonuses and conflict penalties
    4. Factor in freshness (usage-based fatigue proxy)
    5. Select best combination
    6. Generate reasoning
    """
    # Step 1: Gather component learnings
    all_candidates: dict[str, list[dict]] = {}
    for comp_type in RECOMMEND_COMPONENT_TYPES:
        candidates = await get_component_learnings(comp_type, min_samples=1)
        if candidates:
            all_candidates[comp_type] = candidates

    # Step 2: Get correlations
    correlations = await discover_correlations(limit=50)

    # Build correlation lookup
    # Key: (comp_type, comp_value) -> list of correlations
    correlation_map: dict[tuple[str, str], list[Correlation]] = {}
    for corr in correlations:
        key_a = (corr.component_a_type, corr.component_a_value)
        key_b = (corr.component_b_type, corr.component_b_value)

        if key_a not in correlation_map:
            correlation_map[key_a] = []
        if key_b not in correlation_map:
            correlation_map[key_b] = []

        correlation_map[key_a].append(corr)
        correlation_map[key_b].append(corr)

    # Step 3: Get usage counts for freshness
    usage_counts = await get_recent_usage()

    # Step 4: Score each component
    selected_components: list[ComponentScore] = []
    synergies_applied: list[str] = []
    conflicts_avoided: list[str] = []
    fatigued_components: list[str] = []

    for comp_type in RECOMMEND_COMPONENT_TYPES:
        candidates = all_candidates.get(comp_type, [])
        if not candidates:
            continue

        # Score each candidate
        scored_candidates: list[ComponentScore] = []

        for cand in candidates:
            comp_value = cand["component_value"]
            win_rate = float(cand.get("win_rate") or 0)
            sample_size = cand.get("sample_size") or 0

            score = ComponentScore(
                component_type=comp_type,
                component_value=comp_value,
                base_win_rate=win_rate,
                sample_size=sample_size,
            )

            # Check correlations with already selected components
            key = (comp_type, comp_value)
            related_corrs = correlation_map.get(key, [])

            for corr in related_corrs:
                # Find the "other" component in correlation
                if corr.component_a_type == comp_type and corr.component_a_value == comp_value:
                    other_type = corr.component_b_type
                    other_value = corr.component_b_value
                else:
                    other_type = corr.component_a_type
                    other_value = corr.component_a_value

                # Check if other component is already selected
                is_selected = any(
                    s.component_type == other_type and s.component_value == other_value
                    for s in selected_components
                )

                if is_selected:
                    if corr.correlation_type == "positive":
                        # Synergy bonus
                        bonus = (corr.lift - 1.0) * 0.5  # Half of lift as bonus
                        score.synergy_bonus += bonus
                        score.reasoning.append(
                            f"Synergy with {other_value} (+{corr.lift_percent:.0f}%)"
                        )
                    else:
                        # Conflict penalty
                        penalty = (1.0 - corr.lift) * 0.5
                        score.conflict_penalty += penalty
                        score.reasoning.append(
                            f"Conflict with {other_value} ({corr.lift_percent:.0f}%)"
                        )

            # Apply freshness
            usage = usage_counts.get(key, 0)
            score.freshness_score = calculate_freshness_score(usage)

            if score.freshness_score < 1.0:
                if score.freshness_score <= 0.5:
                    score.reasoning.append(f"Fatigued ({usage} uses in {FRESHNESS_WINDOW_DAYS}d)")
                else:
                    score.reasoning.append(f"Recently used ({usage}x)")

            # Calculate final score
            score.calculate_final_score()
            scored_candidates.append(score)

        # Select best candidate for this type
        scored_candidates.sort(key=lambda s: s.final_score, reverse=True)

        if scored_candidates:
            best = scored_candidates[0]

            # Track fatigued components that were skipped
            for cand in scored_candidates[1:]:
                if cand.freshness_score <= 0.5 and cand.base_win_rate > best.base_win_rate:
                    fatigued_components.append(f"{cand.component_value} ({cand.component_type})")

            # Track synergies and conflicts
            for reason in best.reasoning:
                if "Synergy" in reason:
                    synergies_applied.append(reason)
                elif "Conflict" in reason:
                    conflicts_avoided.append(reason)

            selected_components.append(best)

    # Step 5: Calculate overall metrics
    if selected_components:
        # Expected конверсия: weighted average of component scores
        total_samples = sum(c.sample_size for c in selected_components)
        if total_samples > 0:
            expected_win_rate = (
                sum(c.final_score * c.sample_size for c in selected_components) / total_samples
            )
        else:
            expected_win_rate = sum(c.final_score for c in selected_components) / len(
                selected_components
            )

        # Overall confidence based on lowest confidence component
        confidence_order = {"high": 3, "medium": 2, "low": 1}
        min_confidence = min(confidence_order[c.confidence] for c in selected_components)
        overall_confidence = {3: "high", 2: "medium", 1: "low"}[min_confidence]
    else:
        expected_win_rate = 0.0
        overall_confidence = "low"

    # Step 6: Generate reasoning
    reasoning = []

    if selected_components:
        top_comp = max(selected_components, key=lambda c: c.base_win_rate)
        reasoning.append(
            f"{top_comp.component_value} has best base конверсия "
            f"({top_comp.base_win_rate:.0%}, n={top_comp.sample_size})"
        )

    if synergies_applied:
        reasoning.append(f"Applied {len(synergies_applied)} synergies")

    if conflicts_avoided:
        reasoning.append(f"Avoided {len(conflicts_avoided)} conflicts")

    fresh_count = sum(1 for c in selected_components if c.freshness_score == 1.0)
    if fresh_count > 0:
        reasoning.append(f"{fresh_count} components are fresh (not recently used)")

    return BestBetRecommendation(
        components=selected_components,
        expected_win_rate=expected_win_rate,
        overall_confidence=overall_confidence,
        reasoning=reasoning,
        synergies_applied=synergies_applied,
        conflicts_avoided=conflicts_avoided,
        fatigued_components=fatigued_components,
    )


def format_best_bet_telegram(recommendation: BestBetRecommendation) -> str:
    """
    Format best bet recommendation for Telegram.

    Example output:
    🎯 Today's Best Bet

    Based on current learnings + fatigue:

    ┌─────────────────────────────┐
    │ fear + story + internal     │
    │ Ожидаемая: 42% конверсия      │
    │ Confidence: HIGH            │
    └─────────────────────────────┘

    Why: fear trending up, story fresh,
    internal source not fatigued

    💡 Synergies: fear + story (+15% lift)
    ⚠️ Avoided: fear + guaranteed (-20%)
    """
    if not recommendation.components:
        return (
            "🎯 <b>Лучшая ставка дня</b>\n\n"
            "<i>Рекомендаций нет.</i>\n\n"
            "Нужно больше тестовых результатов.\n"
            f"Минимум семплов: {MIN_SAMPLES_FOR_CONFIDENCE} на компонент"
        )

    # Build component summary
    comp_values = [c.component_value for c in recommendation.components[:3]]
    comp_summary = " + ".join(comp_values)

    # Confidence emoji
    conf_emoji = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🔴",
    }
    conf = recommendation.overall_confidence.upper()
    emoji = conf_emoji.get(recommendation.overall_confidence, "⚪")

    # Build main card
    lines = [
        "🎯 <b>Лучшая ставка дня</b>",
        "",
        "<i>На основе текущих данных + свежесть:</i>",
        "",
        "┌─────────────────────────────┐",
        f"│ <b>{comp_summary}</b>",
        f"│ Ожидаемая: <b>{recommendation.expected_win_rate:.0%}</b> конверсия",
        f"│ Confidence: {emoji} <b>{conf}</b>",
        "└─────────────────────────────┘",
        "",
    ]

    # Component details
    lines.append("<b>Компоненты:</b>")
    for i, comp in enumerate(recommendation.components):
        prefix = "└──" if i == len(recommendation.components) - 1 else "├──"
        conf_indicator = {"high": "✓", "medium": "~", "low": "?"}[comp.confidence]
        lines.append(
            f"{prefix} {comp.component_value} ({comp.component_type[:8]}) "
            f"{comp.base_win_rate:.0%} {conf_indicator}"
        )
    lines.append("")

    # Reasoning
    if recommendation.reasoning:
        lines.append("<b>Почему:</b>")
        for reason in recommendation.reasoning[:3]:
            lines.append(f"• {reason}")
        lines.append("")

    # Synergies applied
    if recommendation.synergies_applied:
        synergy_items = recommendation.synergies_applied[:2]
        lines.append(f"💡 <b>Синергии:</b> {', '.join(synergy_items)}")

    # Conflicts avoided
    if recommendation.conflicts_avoided:
        conflict_items = recommendation.conflicts_avoided[:2]
        lines.append(f"⚠️ <b>Избежали:</b> {', '.join(conflict_items)}")

    # Fatigued components
    if recommendation.fatigued_components:
        lines.append(
            f"😴 <b>Усталые (пропущены):</b> {', '.join(recommendation.fatigued_components[:3])}"
        )

    return "\n".join(lines)
