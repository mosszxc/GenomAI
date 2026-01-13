"""
Feature Monitoring Activities

Activities for tracking feature correlations and detecting drift:
- Update all feature correlations
- Auto-deprecate low correlation features
- Detect feature drift

Issue: #305
"""

from dataclasses import dataclass
from typing import Optional

from temporalio import activity


@dataclass
class UpdateCorrelationsInput:
    """Input for update_feature_correlations activity"""

    pass  # No input parameters needed


@dataclass
class CorrelationUpdate:
    """Single feature correlation update result"""

    feature_name: str
    correlation: Optional[float]
    sample_size: int
    message: str


@dataclass
class UpdateCorrelationsOutput:
    """Output from update_feature_correlations activity"""

    updated_count: int
    results: list[CorrelationUpdate]
    deprecated_features: list[str]
    errors: list[str]


@activity.defn
async def update_feature_correlations(
    input: UpdateCorrelationsInput,
) -> UpdateCorrelationsOutput:
    """
    Update correlation metrics for all shadow and active features.

    Also auto-deprecates shadow features with low correlation after 30 days.

    Returns:
        UpdateCorrelationsOutput with results
    """
    activity.logger.info("Updating feature correlations")

    from src.services import feature_correlation

    errors = []
    results = []

    try:
        # Update all correlations
        correlation_results = await feature_correlation.update_all_feature_correlations()

        for r in correlation_results:
            results.append(
                CorrelationUpdate(
                    feature_name=r.feature_name,
                    correlation=r.correlation,
                    sample_size=r.sample_size,
                    message=r.message,
                )
            )

        activity.logger.info(f"Updated correlations for {len(results)} features")

    except Exception as e:
        activity.logger.error(f"Error updating correlations: {e}")
        errors.append(f"correlation_update: {str(e)}")

    # Auto-deprecate low correlation features
    deprecated = []
    try:
        deprecated = await feature_correlation.auto_deprecate_low_correlation_features()
        if deprecated:
            activity.logger.info(f"Auto-deprecated {len(deprecated)} features: {deprecated}")

    except Exception as e:
        activity.logger.error(f"Error in auto-deprecation: {e}")
        errors.append(f"auto_deprecation: {str(e)}")

    updated_count = len([r for r in results if r.correlation is not None])

    return UpdateCorrelationsOutput(
        updated_count=updated_count,
        results=results,
        deprecated_features=deprecated,
        errors=errors,
    )


@dataclass
class DetectDriftInput:
    """Input for detect_feature_drift activity"""

    pass  # No input parameters needed


@dataclass
class DriftDetection:
    """Single feature drift detection result"""

    feature_name: str
    historical_correlation: float
    recent_correlation: float
    drift: float
    is_significant: bool


@dataclass
class DetectDriftOutput:
    """Output from detect_feature_drift activity"""

    checked_count: int
    drift_detected: list[DriftDetection]
    errors: list[str]


@activity.defn
async def detect_feature_drift(input: DetectDriftInput) -> DetectDriftOutput:
    """
    Detect correlation drift for active features.

    Significant drift (>0.1) indicates the feature's predictive
    power has changed and may need investigation.

    Returns:
        DetectDriftOutput with drift results
    """
    activity.logger.info("Detecting feature drift")

    from src.services import feature_correlation
    from src.services import feature_registry

    errors = []
    drift_results = []

    try:
        # Get active features count
        active_features = await feature_registry.list_features(status="active")
        checked_count = len(active_features)

        # Detect drift
        drift_list = await feature_correlation.detect_all_feature_drift()

        for d in drift_list:
            drift_results.append(
                DriftDetection(
                    feature_name=d.feature_name,
                    historical_correlation=d.historical_correlation,
                    recent_correlation=d.recent_correlation,
                    drift=d.drift,
                    is_significant=d.is_significant,
                )
            )

        if drift_results:
            activity.logger.warning(
                f"Drift detected for {len(drift_results)} features: "
                f"{[d.feature_name for d in drift_results]}"
            )

        return DetectDriftOutput(
            checked_count=checked_count,
            drift_detected=drift_results,
            errors=errors,
        )

    except Exception as e:
        activity.logger.error(f"Error detecting drift: {e}")
        return DetectDriftOutput(
            checked_count=0,
            drift_detected=[],
            errors=[str(e)],
        )


@dataclass
class EmitFeatureEventInput:
    """Input for emit_feature_event activity"""

    event_type: str
    payload: dict


@dataclass
class EmitFeatureEventOutput:
    """Output from emit_feature_event activity"""

    success: bool
    event_id: Optional[str]


@activity.defn
async def emit_feature_event(input: EmitFeatureEventInput) -> EmitFeatureEventOutput:
    """
    Emit feature monitoring event to event_log.

    Event types:
    - feature.correlations.updated
    - feature.auto_deprecated
    - feature.drift_detected

    Returns:
        EmitFeatureEventOutput with result
    """
    activity.logger.info(f"Emitting feature event: {input.event_type}")

    from src.services.event_log import emit_event

    try:
        event_id = await emit_event(
            event_type=input.event_type,
            payload=input.payload,
        )

        return EmitFeatureEventOutput(
            success=True,
            event_id=event_id,
        )

    except Exception as e:
        activity.logger.error(f"Error emitting event: {e}")
        return EmitFeatureEventOutput(
            success=False,
            event_id=None,
        )
