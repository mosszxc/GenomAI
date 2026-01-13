"""
Feature Registry Service

Manages experimental ML features with lifecycle: shadow → active → deprecated.
Provides governance rules for feature promotion based on sample size and correlation.

Issues: #303, #306
"""

import os
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from src.core.http_client import get_http_client

from src.utils.errors import SupabaseError
from src.services.statistical_validation import (
    full_validation_for_promotion,
)


SCHEMA = "genomai"

# Feature governance rules
FEATURE_RULES = {
    "min_sample_size": 100,
    "min_abs_correlation": 0.08,
    "max_active_features": 10,
    "deprecate_after_days": 30,
}


@dataclass
class FeatureResult:
    """Result of feature operations"""

    success: bool
    feature_name: str
    message: str
    data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "feature_name": self.feature_name,
            "message": self.message,
            "data": self.data,
        }


class FeatureRegistryError(Exception):
    """Error in feature registry operations"""

    pass


class FeatureNotFoundError(FeatureRegistryError):
    """Feature not found"""

    pass


class FeaturePromotionError(FeatureRegistryError):
    """Cannot promote feature"""

    pass


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with schema"""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


async def add_feature(
    name: str,
    sql_definition: str,
    description: Optional[str] = None,
    depends_on: Optional[list[str]] = None,
) -> dict:
    """
    Add a new experimental feature in shadow status.

    Args:
        name: Unique feature name
        sql_definition: SQL query that computes the feature
        description: Human-readable description
        depends_on: List of feature names this depends on

    Returns:
        Created feature record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "name": name,
        "sql_definition": sql_definition,
        "description": description,
        "status": "shadow",
        "depends_on": depends_on or [],
    }

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/feature_experiments",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else payload


async def get_feature(name: str) -> Optional[dict]:
    """
    Get feature by name.

    Args:
        name: Feature name

    Returns:
        Feature record or None if not found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/feature_experiments?name=eq.{name}",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else None


async def list_features(status: Optional[str] = None) -> list[dict]:
    """
    List all features, optionally filtered by status.

    Args:
        status: Filter by status ('shadow', 'active', 'deprecated')

    Returns:
        List of feature records
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    url = f"{rest_url}/feature_experiments"
    if status:
        url += f"?status=eq.{status}"

    client = get_http_client()
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def count_features(status: str) -> int:
    """
    Count features by status.

    Args:
        status: Status to count

    Returns:
        Number of features with given status
    """
    features = await list_features(status=status)
    return len(features)


async def can_promote(name: str) -> tuple[bool, str]:
    """
    Check if feature can be promoted from shadow to active.

    Basic validation rules:
    1. Sample size >= min_sample_size
    2. Absolute correlation >= min_abs_correlation
    3. Active features < max_active_features

    For full statistical validation, use can_promote_with_statistics().

    Args:
        name: Feature name

    Returns:
        Tuple of (can_promote, reason)
    """
    feature = await get_feature(name)
    if not feature:
        return False, f"Feature '{name}' not found"

    if feature.get("status") != "shadow":
        return False, f"Feature is {feature.get('status')}, not shadow"

    sample_size = feature.get("sample_size", 0)
    if sample_size < FEATURE_RULES["min_sample_size"]:
        return (
            False,
            f"Need {FEATURE_RULES['min_sample_size']}+ samples, have {sample_size}",
        )

    correlation = feature.get("correlation_cpa")
    if correlation is None or abs(float(correlation)) < FEATURE_RULES["min_abs_correlation"]:
        corr_str = f"{correlation:.4f}" if correlation else "None"
        return (
            False,
            f"Correlation {corr_str} too low (need >= {FEATURE_RULES['min_abs_correlation']})",
        )

    active_count = await count_features(status="active")
    if active_count >= FEATURE_RULES["max_active_features"]:
        return (
            False,
            f"Already {active_count} active features (max {FEATURE_RULES['max_active_features']})",
        )

    return True, "OK"


async def can_promote_with_statistics(
    name: str,
    p_value: Optional[float] = None,
    correlation_history: Optional[list[float]] = None,
    segment_correlations: Optional[dict[str, Optional[float]]] = None,
) -> tuple[bool, list[str]]:
    """
    Check if feature can be promoted with full statistical validation.

    Runs all basic checks plus:
    1. Bonferroni-adjusted significance (if p_value provided)
    2. Correlation stability over time (if history provided)
    3. Simpson's paradox detection (if segment data provided)

    Args:
        name: Feature name
        p_value: P-value from correlation test
        correlation_history: Rolling correlation values over time
        segment_correlations: Correlations by segment (geo, vertical, etc.)

    Returns:
        Tuple of (can_promote, list_of_errors)
    """
    # Run basic checks first
    basic_ok, basic_reason = await can_promote(name)
    if not basic_ok:
        return False, [basic_reason]

    # Run full statistical validation
    validation = await full_validation_for_promotion(
        feature_name=name,
        p_value=p_value,
        correlation_history=correlation_history,
        segment_correlations=segment_correlations,
    )

    return validation.can_promote, validation.errors


async def promote_feature(name: str) -> FeatureResult:
    """
    Promote feature from shadow to active status.

    Args:
        name: Feature name

    Returns:
        FeatureResult with success/failure info
    """
    can_do, reason = await can_promote(name)
    if not can_do:
        return FeatureResult(
            success=False,
            feature_name=name,
            message=reason,
        )

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "status": "active",
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/feature_experiments?name=eq.{name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return FeatureResult(
        success=True,
        feature_name=name,
        message="Promoted to active",
        data=data[0] if data else None,
    )


async def deprecate_feature(name: str, reason: str) -> FeatureResult:
    """
    Deprecate a feature (any status → deprecated).

    Args:
        name: Feature name
        reason: Reason for deprecation

    Returns:
        FeatureResult with success/failure info
    """
    feature = await get_feature(name)
    if not feature:
        return FeatureResult(
            success=False,
            feature_name=name,
            message=f"Feature '{name}' not found",
        )

    if feature.get("status") == "deprecated":
        return FeatureResult(
            success=False,
            feature_name=name,
            message="Feature already deprecated",
        )

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "status": "deprecated",
        "deprecated_at": datetime.now(timezone.utc).isoformat(),
        "deprecation_reason": reason,
    }

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/feature_experiments?name=eq.{name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return FeatureResult(
        success=True,
        feature_name=name,
        message="Deprecated",
        data=data[0] if data else None,
    )


async def update_feature_metrics(
    name: str, sample_size: int, correlation_cpa: float
) -> FeatureResult:
    """
    Update feature validation metrics.

    Args:
        name: Feature name
        sample_size: Number of samples used for validation
        correlation_cpa: Correlation with CPA

    Returns:
        FeatureResult with success/failure info
    """
    feature = await get_feature(name)
    if not feature:
        return FeatureResult(
            success=False,
            feature_name=name,
            message=f"Feature '{name}' not found",
        )

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "sample_size": sample_size,
        "correlation_cpa": correlation_cpa,
        "correlation_updated_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/feature_experiments?name=eq.{name}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return FeatureResult(
        success=True,
        feature_name=name,
        message=f"Metrics updated: samples={sample_size}, correlation={correlation_cpa:.4f}",
        data=data[0] if data else None,
    )


async def compute_feature_values(name: str, entity_type: str) -> int:
    """
    Compute feature values for all entities of given type.
    Executes the feature's SQL definition and stores results.

    Args:
        name: Feature name
        entity_type: 'idea', 'outcome', or 'creative'

    Returns:
        Number of values computed

    Note: This is a placeholder. Actual implementation requires
    executing dynamic SQL which needs careful security review.
    """
    feature = await get_feature(name)
    if not feature:
        raise FeatureNotFoundError(f"Feature '{name}' not found")

    # Placeholder: actual implementation would:
    # 1. Execute feature.sql_definition with entity_type filter
    # 2. Insert/update derived_feature_values
    # 3. Return count of computed values

    return 0


async def get_feature_value(feature_name: str, entity_type: str, entity_id: str) -> Optional[float]:
    """
    Get computed feature value for an entity.

    Args:
        feature_name: Feature name
        entity_type: Entity type
        entity_id: Entity UUID

    Returns:
        Feature value or None if not computed
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/derived_feature_values"
        f"?feature_name=eq.{feature_name}"
        f"&entity_type=eq.{entity_type}"
        f"&entity_id=eq.{entity_id}",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        return data[0].get("value")
    return None


async def store_feature_value(
    feature_name: str, entity_type: str, entity_id: str, value: float
) -> dict:
    """
    Store computed feature value for an entity.

    Args:
        feature_name: Feature name
        entity_type: Entity type ('idea', 'outcome', 'creative')
        entity_id: Entity UUID
        value: Computed feature value

    Returns:
        Created/updated record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"

    payload = {
        "feature_name": feature_name,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "value": value,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/derived_feature_values",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    return data[0] if data else payload
