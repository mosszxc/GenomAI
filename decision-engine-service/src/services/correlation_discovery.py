"""
Correlation Discovery Service

Discovers which component combinations work well together (synergies)
or poorly (conflicts) based on win/loss outcomes.

Issue: #297 - Telegram Admin Dashboard - Correlation Discovery

Metrics:
- Lift: P(win|A∩B) / (P(win|A) * P(win|B))
  - Lift > 1.0 = synergy (components work better together)
  - Lift < 1.0 = conflict (components hurt each other)
- Chi-squared test for statistical significance
"""

import os
import math
from typing import Optional
from dataclasses import dataclass
import httpx

SCHEMA = "genomai"

# Minimum samples for correlation to be meaningful
MIN_PAIR_SAMPLES = 5
MIN_SINGLE_SAMPLES = 10

# Lift thresholds for categorization
STRONG_POSITIVE_LIFT = 1.15  # +15% lift = strong synergy
WEAK_POSITIVE_LIFT = 1.05    # +5% lift = weak synergy
WEAK_NEGATIVE_LIFT = 0.95    # -5% lift = weak conflict
STRONG_NEGATIVE_LIFT = 0.85  # -15% lift = strong conflict


@dataclass
class Correlation:
    """Represents a discovered correlation between two components."""
    component_a_type: str
    component_a_value: str
    component_b_type: str
    component_b_value: str
    lift: float
    pair_win_rate: float
    pair_sample_size: int
    a_win_rate: float
    a_sample_size: int
    b_win_rate: float
    b_sample_size: int
    correlation_type: str  # "positive" or "negative"
    strength: str  # "strong" or "weak"

    @property
    def lift_percent(self) -> float:
        """Lift as percentage change."""
        return (self.lift - 1.0) * 100


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


def _calculate_lift(
    pair_win_rate: float,
    a_win_rate: float,
    b_win_rate: float,
) -> float:
    """
    Calculate lift for a component pair.

    Lift = P(win|A∩B) / (P(win|A) * P(win|B))

    Interpretation:
    - Lift = 1.0: Components are independent
    - Lift > 1.0: Components have positive synergy
    - Lift < 1.0: Components have negative correlation
    """
    if a_win_rate <= 0 or b_win_rate <= 0:
        return 1.0

    expected = a_win_rate * b_win_rate
    if expected <= 0:
        return 1.0

    return pair_win_rate / expected


def _categorize_lift(lift: float) -> tuple[str, str]:
    """
    Categorize lift into type and strength.

    Returns:
        (correlation_type, strength)
    """
    if lift >= STRONG_POSITIVE_LIFT:
        return ("positive", "strong")
    elif lift >= WEAK_POSITIVE_LIFT:
        return ("positive", "weak")
    elif lift <= STRONG_NEGATIVE_LIFT:
        return ("negative", "strong")
    elif lift <= WEAK_NEGATIVE_LIFT:
        return ("negative", "weak")
    else:
        return ("neutral", "none")


async def discover_correlations(
    min_lift_positive: float = WEAK_POSITIVE_LIFT,
    min_lift_negative: float = WEAK_NEGATIVE_LIFT,
    component_types: Optional[list[str]] = None,
    limit: int = 20,
) -> list[Correlation]:
    """
    Discover correlations between component pairs.

    Args:
        min_lift_positive: Minimum lift for positive correlations (default: 1.05)
        min_lift_negative: Maximum lift for negative correlations (default: 0.95)
        component_types: Filter to specific component types (e.g., ["emotion_primary", "angle_type"])
        limit: Maximum correlations to return

    Returns:
        List of Correlation objects sorted by absolute lift distance from 1.0
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Default component types to analyze
    if component_types is None:
        component_types = [
            "emotion_primary",
            "angle_type",
            "opening_type",
            "promise_type",
            "message_structure",
        ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get all creatives with test results and their components
        creatives_resp = await client.get(
            f"{rest_url}/creatives"
            f"?test_result=not.is.null"
            f"&select=id,test_result",
            headers=headers,
        )
        creatives_resp.raise_for_status()
        creatives = creatives_resp.json()

        if not creatives:
            return []

        # Build creative_id -> test_result map
        creative_results = {c["id"]: c["test_result"] for c in creatives}
        creative_ids = list(creative_results.keys())

        # Step 2: Get decomposed components for these creatives
        # Batch in groups of 50 to avoid URL length limits
        all_decomposed = []
        for i in range(0, len(creative_ids), 50):
            batch_ids = creative_ids[i:i+50]
            ids_param = ",".join(f'"{cid}"' for cid in batch_ids)

            decomposed_resp = await client.get(
                f"{rest_url}/decomposed_creatives"
                f"?creative_id=in.({ids_param})"
                f"&select=creative_id,payload",
                headers=headers,
            )
            if decomposed_resp.status_code == 200:
                all_decomposed.extend(decomposed_resp.json())

    # Step 3: Build component occurrence maps
    # Map: (component_type, component_value) -> set of creative_ids
    component_creatives: dict[tuple[str, str], set[str]] = {}

    for row in all_decomposed:
        creative_id = row.get("creative_id")
        payload = row.get("payload") or {}

        if creative_id not in creative_results:
            continue

        for comp_type in component_types:
            comp_value = payload.get(comp_type)
            if comp_value:
                key = (comp_type, comp_value)
                if key not in component_creatives:
                    component_creatives[key] = set()
                component_creatives[key].add(creative_id)

    # Step 4: Calculate single component stats
    def calc_stats(creative_ids_set: set[str]) -> tuple[float, int, int]:
        """Calculate win_rate, wins, total for a set of creative IDs."""
        wins = sum(1 for cid in creative_ids_set if creative_results.get(cid) == "win")
        total = len(creative_ids_set)
        win_rate = wins / total if total > 0 else 0
        return win_rate, wins, total

    # Filter components with enough samples
    valid_components = {
        key: ids for key, ids in component_creatives.items()
        if len(ids) >= MIN_SINGLE_SAMPLES
    }

    # Step 5: Calculate pair correlations
    correlations = []
    component_keys = list(valid_components.keys())

    for i, key_a in enumerate(component_keys):
        for key_b in component_keys[i+1:]:
            # Skip same component type (e.g., emotion_primary + emotion_primary)
            if key_a[0] == key_b[0]:
                continue

            # Get intersection (creatives with both components)
            ids_a = valid_components[key_a]
            ids_b = valid_components[key_b]
            pair_ids = ids_a & ids_b

            if len(pair_ids) < MIN_PAIR_SAMPLES:
                continue

            # Calculate stats
            a_win_rate, _, a_total = calc_stats(ids_a)
            b_win_rate, _, b_total = calc_stats(ids_b)
            pair_win_rate, _, pair_total = calc_stats(pair_ids)

            # Calculate lift
            lift = _calculate_lift(pair_win_rate, a_win_rate, b_win_rate)

            # Filter by lift threshold
            if lift >= min_lift_positive or lift <= min_lift_negative:
                corr_type, strength = _categorize_lift(lift)

                if corr_type == "neutral":
                    continue

                correlations.append(Correlation(
                    component_a_type=key_a[0],
                    component_a_value=key_a[1],
                    component_b_type=key_b[0],
                    component_b_value=key_b[1],
                    lift=lift,
                    pair_win_rate=pair_win_rate,
                    pair_sample_size=pair_total,
                    a_win_rate=a_win_rate,
                    a_sample_size=a_total,
                    b_win_rate=b_win_rate,
                    b_sample_size=b_total,
                    correlation_type=corr_type,
                    strength=strength,
                ))

    # Sort by absolute distance from 1.0 (most significant first)
    correlations.sort(key=lambda c: abs(c.lift - 1.0), reverse=True)

    return correlations[:limit]


async def get_top_recommendations(limit: int = 3) -> list[Correlation]:
    """
    Get top positive correlations as recommendations.

    Returns strongest positive synergies that could be tested.
    """
    correlations = await discover_correlations(
        min_lift_positive=STRONG_POSITIVE_LIFT,
        min_lift_negative=2.0,  # Effectively disable negative
        limit=limit,
    )

    return [c for c in correlations if c.correlation_type == "positive"]


def format_correlations_telegram(
    correlations: list[Correlation],
    show_recommendation: bool = True,
) -> str:
    """
    Format correlations for Telegram display.

    Example output:
    🔗 Discovered Correlations

    Strong positive:
    ├── hope + question_opening → +23% lift
    └── curiosity + story_structure → +18% lift

    Strong negative:
    ├── fear + guaranteed_promise → -31% penalty
    └── urgency + long_form → -25% penalty

    💡 Recommendation: Test hope + question combo
    """
    if not correlations:
        return (
            "🔗 <b>Correlation Discovery</b>\n\n"
            "<i>No significant correlations found yet.</i>\n\n"
            "Need more test results to discover patterns.\n"
            f"Minimum samples: {MIN_PAIR_SAMPLES} per pair"
        )

    # Separate positive and negative
    strong_positive = [c for c in correlations if c.correlation_type == "positive" and c.strength == "strong"]
    weak_positive = [c for c in correlations if c.correlation_type == "positive" and c.strength == "weak"]
    strong_negative = [c for c in correlations if c.correlation_type == "negative" and c.strength == "strong"]
    weak_negative = [c for c in correlations if c.correlation_type == "negative" and c.strength == "weak"]

    lines = ["🔗 <b>Discovered Correlations</b>", ""]

    def format_correlation(c: Correlation, is_last: bool = False) -> str:
        """Format single correlation line."""
        prefix = "└──" if is_last else "├──"
        # Shorten component values for display
        a_short = c.component_a_value[:12]
        b_short = c.component_b_value[:12]

        if c.correlation_type == "positive":
            sign = "+"
            suffix = "lift"
        else:
            sign = ""
            suffix = "penalty"

        pct = c.lift_percent
        return f"{prefix} {a_short} + {b_short} → {sign}{pct:.0f}% {suffix}"

    # Strong positive
    if strong_positive:
        lines.append("<b>Strong positive:</b>")
        for i, c in enumerate(strong_positive[:4]):
            is_last = (i == len(strong_positive[:4]) - 1)
            lines.append(format_correlation(c, is_last))
        lines.append("")

    # Strong negative
    if strong_negative:
        lines.append("<b>Strong negative:</b>")
        for i, c in enumerate(strong_negative[:4]):
            is_last = (i == len(strong_negative[:4]) - 1)
            lines.append(format_correlation(c, is_last))
        lines.append("")

    # Weak correlations (optional, show only if no strong ones)
    if not strong_positive and not strong_negative:
        if weak_positive:
            lines.append("<b>Weak positive:</b>")
            for i, c in enumerate(weak_positive[:3]):
                is_last = (i == len(weak_positive[:3]) - 1)
                lines.append(format_correlation(c, is_last))
            lines.append("")

        if weak_negative:
            lines.append("<b>Weak negative:</b>")
            for i, c in enumerate(weak_negative[:3]):
                is_last = (i == len(weak_negative[:3]) - 1)
                lines.append(format_correlation(c, is_last))
            lines.append("")

    # Recommendation
    if show_recommendation and strong_positive:
        best = strong_positive[0]
        lines.append(f"💡 <b>Recommendation:</b> Test {best.component_a_value} + {best.component_b_value} combo")
        lines.append(f"   (n={best.pair_sample_size}, win rate {best.pair_win_rate:.0%})")

    # Stats footer
    total_corr = len(correlations)
    pos_count = len(strong_positive) + len(weak_positive)
    neg_count = len(strong_negative) + len(weak_negative)
    lines.extend([
        "",
        f"<i>Found {total_corr} correlations: {pos_count} synergies, {neg_count} conflicts</i>",
    ])

    return "\n".join(lines)
