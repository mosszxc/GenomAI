"""
Feature Correlation Monitoring Service

Tracks correlation between ML features and CPA.
Auto-deprecates shadow features with low correlation.
Detects drift for active features.

Issue: #305
"""

import os
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from src.core.http_client import get_http_client
from scipy.stats import pearsonr
import numpy as np

from src.utils.errors import SupabaseError
from src.services import feature_registry


SCHEMA = "genomai"

# Correlation thresholds
MIN_SAMPLES_FOR_CORRELATION = 30
DRIFT_THRESHOLD = 0.1
DEPRECATION_DAYS = 30
LOW_CORRELATION_THRESHOLD = 0.05


@dataclass
class FeatureCpaPair:
    """A pair of feature value and corresponding CPA"""

    feature_value: float
    cpa: float


@dataclass
class CorrelationResult:
    """Result of correlation computation"""

    feature_name: str
    correlation: Optional[float]
    p_value: Optional[float]
    sample_size: int
    message: str


@dataclass
class DriftResult:
    """Result of drift detection"""

    feature_name: str
    historical_correlation: float
    recent_correlation: float
    drift: float
    is_significant: bool


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str) -> dict:
    """Get headers for Supabase REST API"""
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }


async def get_feature_cpa_pairs(
    feature_name: str, limit: int = 1000
) -> list[FeatureCpaPair]:
    """
    Get pairs of (feature_value, cpa) for correlation calculation.

    Joins:
    - derived_feature_values (entity_type='idea', entity_id=idea_id)
    - decisions (idea_id)
    - outcome_aggregates (decision_id, cpa)

    Args:
        feature_name: Feature to get values for
        limit: Maximum number of pairs to return

    Returns:
        List of FeatureCpaPair objects
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Use RPC for complex join query
    # We need to call raw SQL via postgrest RPC or use multiple queries
    # For now, use multiple queries approach

    # Step 1: Get feature values for ideas
    client = get_http_client()
    response = await client.get(
        f"{rest_url}/derived_feature_values"
        f"?feature_name=eq.{feature_name}"
        f"&entity_type=eq.idea"
        f"&value=not.is.null"
        f"&order=computed_at.desc"
        f"&limit={limit * 2}",  # Get more to filter later
        headers=headers,
    )
    response.raise_for_status()
    feature_values = response.json()

    if not feature_values:
        return []

    # Step 2: Get idea_ids that have feature values
    idea_ids = [fv["entity_id"] for fv in feature_values]

    # Step 3: Get decisions for these ideas
    # Batch in groups of 50 to avoid URL length limits
    all_decisions = []
    for i in range(0, len(idea_ids), 50):
        batch_ids = idea_ids[i : i + 50]
        ids_param = ",".join(batch_ids)

        client = get_http_client()
        response = await client.get(
            f"{rest_url}/decisions?idea_id=in.({ids_param})&select=id,idea_id",
            headers=headers,
        )
        response.raise_for_status()
        all_decisions.extend(response.json())

    if not all_decisions:
        return []

    # Build idea_id -> decision_id mapping
    idea_to_decision = {d["idea_id"]: d["id"] for d in all_decisions}
    decision_ids = list(idea_to_decision.values())

    # Step 4: Get outcome_aggregates with CPA for these decisions
    all_outcomes = []
    for i in range(0, len(decision_ids), 50):
        batch_ids = decision_ids[i : i + 50]
        ids_param = ",".join(batch_ids)

        client = get_http_client()
        response = await client.get(
            f"{rest_url}/outcome_aggregates"
            f"?decision_id=in.({ids_param})"
            f"&cpa=not.is.null"
            f"&select=decision_id,cpa",
            headers=headers,
        )
        response.raise_for_status()
        all_outcomes.extend(response.json())

    if not all_outcomes:
        return []

    # Build decision_id -> cpa mapping (use latest/avg if multiple)
    decision_to_cpa = {}
    for outcome in all_outcomes:
        dec_id = outcome["decision_id"]
        cpa = float(outcome["cpa"])
        if dec_id not in decision_to_cpa:
            decision_to_cpa[dec_id] = []
        decision_to_cpa[dec_id].append(cpa)

    # Average CPA per decision
    decision_to_avg_cpa = {
        dec_id: sum(cpas) / len(cpas) for dec_id, cpas in decision_to_cpa.items()
    }

    # Step 5: Join feature values with CPA
    pairs = []
    for fv in feature_values:
        idea_id = fv["entity_id"]
        if idea_id not in idea_to_decision:
            continue
        decision_id = idea_to_decision[idea_id]
        if decision_id not in decision_to_avg_cpa:
            continue

        pairs.append(
            FeatureCpaPair(
                feature_value=float(fv["value"]),
                cpa=decision_to_avg_cpa[decision_id],
            )
        )

        if len(pairs) >= limit:
            break

    return pairs


def compute_pearson_correlation(
    pairs: list[FeatureCpaPair],
) -> tuple[Optional[float], Optional[float]]:
    """
    Compute Pearson correlation between feature values and CPA.

    Args:
        pairs: List of (feature_value, cpa) pairs

    Returns:
        Tuple of (correlation, p_value) or (None, None) if insufficient data
    """
    if len(pairs) < MIN_SAMPLES_FOR_CORRELATION:
        return None, None

    feature_values = np.array([p.feature_value for p in pairs])
    cpa_values = np.array([p.cpa for p in pairs])

    # Check for constant values (no variance)
    if np.std(feature_values) == 0 or np.std(cpa_values) == 0:
        return None, None

    correlation, p_value = pearsonr(feature_values, cpa_values)
    return float(correlation), float(p_value)


async def compute_feature_correlation(feature_name: str) -> CorrelationResult:
    """
    Compute correlation for a single feature.

    Args:
        feature_name: Feature to compute correlation for

    Returns:
        CorrelationResult with correlation, p_value, sample_size
    """
    pairs = await get_feature_cpa_pairs(feature_name)

    if len(pairs) < MIN_SAMPLES_FOR_CORRELATION:
        return CorrelationResult(
            feature_name=feature_name,
            correlation=None,
            p_value=None,
            sample_size=len(pairs),
            message=f"Need {MIN_SAMPLES_FOR_CORRELATION}+ samples, have {len(pairs)}",
        )

    correlation, p_value = compute_pearson_correlation(pairs)

    if correlation is None:
        return CorrelationResult(
            feature_name=feature_name,
            correlation=None,
            p_value=None,
            sample_size=len(pairs),
            message="Could not compute correlation (no variance)",
        )

    return CorrelationResult(
        feature_name=feature_name,
        correlation=correlation,
        p_value=p_value,
        sample_size=len(pairs),
        message=f"Correlation: {correlation:.4f} (p={p_value:.4f})",
    )


async def update_all_feature_correlations() -> list[CorrelationResult]:
    """
    Update correlation for all shadow and active features.

    Returns:
        List of CorrelationResult for each feature
    """
    results = []

    # Get shadow and active features
    shadow_features = await feature_registry.list_features(status="shadow")
    active_features = await feature_registry.list_features(status="active")
    all_features = shadow_features + active_features

    for feature in all_features:
        name = feature["name"]

        # Compute correlation
        result = await compute_feature_correlation(name)
        results.append(result)

        # Update feature metrics if we got a correlation
        if result.correlation is not None:
            await feature_registry.update_feature_metrics(
                name=name,
                sample_size=result.sample_size,
                correlation_cpa=result.correlation,
            )

    return results


async def auto_deprecate_low_correlation_features() -> list[str]:
    """
    Auto-deprecate shadow features with low correlation after 30 days.

    Returns:
        List of deprecated feature names
    """
    deprecated = []

    shadow_features = await feature_registry.list_features(status="shadow")
    now = datetime.now(timezone.utc)

    for feature in shadow_features:
        name = feature["name"]
        created_at_str = feature.get("created_at")
        correlation = feature.get("correlation_cpa")
        sample_size = feature.get("sample_size", 0)

        if not created_at_str:
            continue

        # Parse created_at
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        days_since_creation = (now - created_at).days

        # Check if should auto-deprecate
        if (
            days_since_creation > DEPRECATION_DAYS
            and sample_size >= MIN_SAMPLES_FOR_CORRELATION
            and correlation is not None
            and abs(float(correlation)) < LOW_CORRELATION_THRESHOLD
        ):
            result = await feature_registry.deprecate_feature(
                name=name,
                reason=f"auto_deprecated: low_correlation ({float(correlation):.4f})",
            )
            if result.success:
                deprecated.append(name)

    return deprecated


async def detect_feature_drift(
    feature_name: str, recent_days: int = 30
) -> Optional[DriftResult]:
    """
    Detect if an active feature's correlation has drifted.

    Compares recent correlation (last N days) with historical.

    Args:
        feature_name: Feature to check
        recent_days: Window for recent correlation

    Returns:
        DriftResult if drift detected, None otherwise
    """
    feature = await feature_registry.get_feature(feature_name)
    if not feature:
        return None

    if feature.get("status") != "active":
        return None

    historical_correlation = feature.get("correlation_cpa")
    if historical_correlation is None:
        return None

    historical_correlation = float(historical_correlation)

    # Compute recent correlation
    # For simplicity, we use all available data (the pairs are ordered by computed_at desc)
    # A more sophisticated approach would filter by date range
    result = await compute_feature_correlation(feature_name)

    if result.correlation is None:
        return None

    drift = abs(result.correlation - historical_correlation)
    is_significant = drift > DRIFT_THRESHOLD

    return DriftResult(
        feature_name=feature_name,
        historical_correlation=historical_correlation,
        recent_correlation=result.correlation,
        drift=drift,
        is_significant=is_significant,
    )


async def detect_all_feature_drift() -> list[DriftResult]:
    """
    Detect drift for all active features.

    Returns:
        List of DriftResult for features with significant drift
    """
    results = []

    active_features = await feature_registry.list_features(status="active")

    for feature in active_features:
        name = feature["name"]
        drift_result = await detect_feature_drift(name)

        if drift_result and drift_result.is_significant:
            results.append(drift_result)

    return results
