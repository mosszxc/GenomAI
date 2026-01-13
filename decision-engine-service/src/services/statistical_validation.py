"""
Statistical Validation Service

Provides statistical safeguards for feature engineering to prevent false discoveries.

Safeguards implemented:
1. Bonferroni correction for multiple hypothesis testing
2. Wilson confidence intervals for small samples
3. Simpson's paradox detection
4. Correlation stability checks

Issue: #306
"""

import math
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from src.services.feature_registry import (
    list_features,
    get_feature,
)


# Statistical thresholds
STATISTICAL_RULES = {
    "base_alpha": 0.05,  # Base significance level
    "min_sample_for_decision": 30,  # Minimum for any conclusions
    "min_sample_for_promotion": 100,  # Minimum for activation
    "stability_std_threshold": 0.15,  # Max std for stable correlation
    "stability_min_windows": 3,  # Minimum windows for stability check
    "confidence_level": 0.95,  # CI confidence level
}


@dataclass
class ValidationResult:
    """Result of statistical validation"""

    valid: bool
    check_name: str
    message: str
    details: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "check_name": self.check_name,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# 1. Multiple Hypothesis Testing - Bonferroni Correction
# =============================================================================


def adjusted_significance_threshold(n_features: int, alpha: float = 0.05) -> float:
    """
    Calculate Bonferroni-adjusted significance threshold.

    When testing multiple hypotheses, the chance of at least one false positive
    increases. Bonferroni correction divides alpha by number of tests.

    Example: 10 features → threshold = 0.005 instead of 0.05

    Args:
        n_features: Number of features being tested
        alpha: Base significance level (default 0.05)

    Returns:
        Adjusted significance threshold
    """
    if n_features <= 0:
        return alpha
    return alpha / n_features


async def validate_feature_significance(
    feature_name: str,
    p_value: float,
) -> ValidationResult:
    """
    Validate feature significance using Bonferroni correction.

    Args:
        feature_name: Name of feature being validated
        p_value: P-value from correlation test

    Returns:
        ValidationResult with pass/fail
    """
    # Count active and shadow features (all being tested)
    shadow_features = await list_features(status="shadow")
    active_features = await list_features(status="active")
    n_features = len(shadow_features) + len(active_features)

    if n_features == 0:
        n_features = 1  # At minimum, we're testing this feature

    threshold = adjusted_significance_threshold(n_features, STATISTICAL_RULES["base_alpha"])

    if p_value > threshold:
        return ValidationResult(
            valid=False,
            check_name="bonferroni_significance",
            message=f"p-value {p_value:.4f} > adjusted threshold {threshold:.4f}",
            details={
                "p_value": p_value,
                "threshold": threshold,
                "n_features": n_features,
                "base_alpha": STATISTICAL_RULES["base_alpha"],
            },
        )

    return ValidationResult(
        valid=True,
        check_name="bonferroni_significance",
        message=f"p-value {p_value:.4f} <= threshold {threshold:.4f}",
        details={
            "p_value": p_value,
            "threshold": threshold,
            "n_features": n_features,
        },
    )


# =============================================================================
# 2. Small Sample Sizes - Wilson Confidence Intervals
# =============================================================================


def wilson_confidence_interval(
    wins: int, total: int, confidence: float = 0.95
) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval for proportion.

    Wilson interval is more accurate than normal approximation for:
    - Small sample sizes
    - Proportions near 0 or 1

    Formula uses z-score for desired confidence level.

    Args:
        wins: Number of successes
        total: Total number of trials
        confidence: Confidence level (default 0.95)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if total == 0:
        return 0.0, 1.0

    # Z-score for confidence level (two-tailed)
    # 0.95 -> z = 1.96, 0.99 -> z = 2.576
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    p = wins / total
    n = total

    denominator = 1 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denominator

    spread_term = (p * (1 - p) + (z**2) / (4 * n)) / n
    if spread_term < 0:
        spread_term = 0
    spread = z * math.sqrt(spread_term) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return lower, upper


def validate_sample_size(sample_size: int, for_promotion: bool = False) -> ValidationResult:
    """
    Validate that sample size is sufficient for conclusions.

    Args:
        sample_size: Number of samples
        for_promotion: If True, use stricter promotion threshold

    Returns:
        ValidationResult with pass/fail
    """
    min_required = (
        STATISTICAL_RULES["min_sample_for_promotion"]
        if for_promotion
        else STATISTICAL_RULES["min_sample_for_decision"]
    )

    if sample_size < min_required:
        return ValidationResult(
            valid=False,
            check_name="sample_size",
            message=f"Sample size {sample_size} < minimum {min_required}",
            details={
                "sample_size": sample_size,
                "min_required": min_required,
                "for_promotion": for_promotion,
            },
        )

    return ValidationResult(
        valid=True,
        check_name="sample_size",
        message=f"Sample size {sample_size} >= minimum {min_required}",
        details={
            "sample_size": sample_size,
            "min_required": min_required,
        },
    )


def validate_confidence_interval_width(
    wins: int, total: int, max_width: float = 0.3
) -> ValidationResult:
    """
    Validate that confidence interval is narrow enough to be useful.

    A CI of [0.47, 0.99] is too wide for decisions.

    Args:
        wins: Number of successes
        total: Total trials
        max_width: Maximum acceptable CI width

    Returns:
        ValidationResult with pass/fail
    """
    lower, upper = wilson_confidence_interval(wins, total)
    width = upper - lower

    if width > max_width:
        return ValidationResult(
            valid=False,
            check_name="confidence_interval_width",
            message=f"CI [{lower:.2f}, {upper:.2f}] width {width:.2f} > max {max_width}",
            details={
                "lower": lower,
                "upper": upper,
                "width": width,
                "max_width": max_width,
                "wins": wins,
                "total": total,
            },
        )

    return ValidationResult(
        valid=True,
        check_name="confidence_interval_width",
        message=f"CI [{lower:.2f}, {upper:.2f}] width {width:.2f} acceptable",
        details={
            "lower": lower,
            "upper": upper,
            "width": width,
        },
    )


# =============================================================================
# 3. Simpson's Paradox Detection
# =============================================================================


def detect_simpsons_paradox(
    aggregate_correlation: float, segment_correlations: dict[str, Optional[float]]
) -> ValidationResult:
    """
    Detect Simpson's paradox where aggregate differs from segments.

    If aggregate correlation is positive but some segments are negative
    (or vice versa), this indicates Simpson's paradox - the aggregate
    might be misleading.

    Args:
        aggregate_correlation: Overall correlation value
        segment_correlations: Dict of segment_name -> correlation

    Returns:
        ValidationResult with warning if paradox detected
    """
    # Filter out None values
    valid_correlations = {k: v for k, v in segment_correlations.items() if v is not None}

    if len(valid_correlations) < 2:
        return ValidationResult(
            valid=True,
            check_name="simpsons_paradox",
            message="Insufficient segments for paradox detection",
            details={"n_segments": len(valid_correlations)},
        )

    # Check if all segments agree on direction
    segment_values = list(valid_correlations.values())
    all_positive = all(c > 0 for c in segment_values)
    all_negative = all(c < 0 for c in segment_values)

    segments_agree = all_positive or all_negative

    # Check if aggregate matches segment consensus
    aggregate_positive = aggregate_correlation > 0

    paradox_detected = False
    warning_message = None

    if not segments_agree:
        paradox_detected = True
        warning_message = "Segments disagree on correlation direction"
    elif all_positive and not aggregate_positive:
        paradox_detected = True
        warning_message = "Segments positive but aggregate negative"
    elif all_negative and aggregate_positive:
        paradox_detected = True
        warning_message = "Segments negative but aggregate positive"

    if paradox_detected:
        return ValidationResult(
            valid=False,
            check_name="simpsons_paradox",
            message=f"Simpson's paradox detected: {warning_message}",
            details={
                "aggregate": aggregate_correlation,
                "segments": valid_correlations,
                "warning": warning_message,
            },
        )

    return ValidationResult(
        valid=True,
        check_name="simpsons_paradox",
        message="No Simpson's paradox detected",
        details={
            "aggregate": aggregate_correlation,
            "segments": valid_correlations,
        },
    )


# =============================================================================
# 4. Correlation Stability Check
# =============================================================================


def check_correlation_stability(
    correlation_history: list[float], std_threshold: float = 0.15, min_windows: int = 3
) -> ValidationResult:
    """
    Check if correlation is stable over time.

    A correlation that swings from 0.15 to -0.05 between windows
    is unreliable for decision making.

    Args:
        correlation_history: List of correlations from different time windows
        std_threshold: Maximum allowed standard deviation
        min_windows: Minimum number of windows required

    Returns:
        ValidationResult with stability assessment
    """
    valid_correlations = [c for c in correlation_history if c is not None]

    if len(valid_correlations) < min_windows:
        return ValidationResult(
            valid=True,  # Not enough data to fail, but noted
            check_name="correlation_stability",
            message=f"Insufficient data ({len(valid_correlations)}/{min_windows} windows)",
            details={
                "n_windows": len(valid_correlations),
                "min_required": min_windows,
                "status": "insufficient_data",
            },
        )

    correlations_array = np.array(valid_correlations)
    std_dev = float(np.std(correlations_array))
    mean_corr = float(np.mean(correlations_array))

    if std_dev > std_threshold:
        return ValidationResult(
            valid=False,
            check_name="correlation_stability",
            message=f"Unstable correlation: std={std_dev:.3f} > threshold={std_threshold}",
            details={
                "std_dev": std_dev,
                "threshold": std_threshold,
                "mean_correlation": mean_corr,
                "history": valid_correlations,
            },
        )

    return ValidationResult(
        valid=True,
        check_name="correlation_stability",
        message=f"Stable correlation: std={std_dev:.3f}",
        details={
            "std_dev": std_dev,
            "mean_correlation": mean_corr,
            "n_windows": len(valid_correlations),
        },
    )


# =============================================================================
# 5. Full Validation for Promotion
# =============================================================================


@dataclass
class FullValidationResult:
    """Complete validation result for feature promotion"""

    can_promote: bool
    feature_name: str
    checks: list[ValidationResult]
    errors: list[str]

    def to_dict(self) -> dict:
        return {
            "can_promote": self.can_promote,
            "feature_name": self.feature_name,
            "checks": [c.to_dict() for c in self.checks],
            "errors": self.errors,
        }


async def full_validation_for_promotion(
    feature_name: str,
    p_value: Optional[float] = None,
    correlation_history: Optional[list[float]] = None,
    segment_correlations: Optional[dict[str, Optional[float]]] = None,
) -> FullValidationResult:
    """
    Perform full statistical validation before feature promotion.

    Checks:
    1. Sample size (must be >= 100)
    2. Bonferroni-adjusted significance (if p_value provided)
    3. Correlation stability (if history provided)
    4. Simpson's paradox (if segment data provided)

    Args:
        feature_name: Name of feature to validate
        p_value: P-value from correlation test (optional)
        correlation_history: List of rolling correlations (optional)
        segment_correlations: Dict of segment -> correlation (optional)

    Returns:
        FullValidationResult with all check results
    """
    feature = await get_feature(feature_name)

    if not feature:
        return FullValidationResult(
            can_promote=False,
            feature_name=feature_name,
            checks=[],
            errors=[f"Feature '{feature_name}' not found"],
        )

    checks: list[ValidationResult] = []
    errors: list[str] = []

    # 1. Sample size check
    sample_size = feature.get("sample_size", 0)
    sample_check = validate_sample_size(sample_size, for_promotion=True)
    checks.append(sample_check)
    if not sample_check.valid:
        errors.append(sample_check.message)

    # 2. Bonferroni significance check (if p_value provided)
    if p_value is not None:
        sig_check = await validate_feature_significance(feature_name, p_value)
        checks.append(sig_check)
        if not sig_check.valid:
            errors.append(sig_check.message)

    # 3. Correlation stability check (if history provided)
    if correlation_history:
        stability_check = check_correlation_stability(
            correlation_history,
            STATISTICAL_RULES["stability_std_threshold"],
            STATISTICAL_RULES["stability_min_windows"],
        )
        checks.append(stability_check)
        if not stability_check.valid:
            errors.append(stability_check.message)

    # 4. Simpson's paradox check (if segment data provided)
    if segment_correlations:
        aggregate = feature.get("correlation_cpa")
        if aggregate is not None:
            paradox_check = detect_simpsons_paradox(float(aggregate), segment_correlations)
            checks.append(paradox_check)
            if not paradox_check.valid:
                errors.append(paradox_check.message)

    return FullValidationResult(
        can_promote=len(errors) == 0,
        feature_name=feature_name,
        checks=checks,
        errors=errors,
    )


# =============================================================================
# 6. Helper: Point-in-Time Validation
# =============================================================================


def validate_point_in_time(
    feature_created_at: datetime,
    data_timestamp: datetime,
) -> ValidationResult:
    """
    Validate that feature computation uses only past data.

    Prevents data leakage where features use future information.

    Args:
        feature_created_at: When the feature value was computed
        data_timestamp: Timestamp of data used in computation

    Returns:
        ValidationResult indicating if temporal ordering is correct
    """
    if data_timestamp > feature_created_at:
        return ValidationResult(
            valid=False,
            check_name="point_in_time",
            message="Data leakage: using future data",
            details={
                "feature_created_at": feature_created_at.isoformat(),
                "data_timestamp": data_timestamp.isoformat(),
            },
        )

    return ValidationResult(
        valid=True,
        check_name="point_in_time",
        message="Temporal ordering valid",
        details={
            "feature_created_at": feature_created_at.isoformat(),
            "data_timestamp": data_timestamp.isoformat(),
        },
    )
