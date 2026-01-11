# QA Notes: Issue #305 - Feature Correlation Monitoring

## Summary
Implemented automatic correlation tracking between ML features and CPA in the Learning Loop.

## Changes

### New Files
- `src/services/feature_correlation.py` - Core correlation service
  - `get_feature_cpa_pairs()` - Joins derived_feature_values with outcome_aggregates via decisions
  - `compute_pearson_correlation()` - Calculates Pearson correlation
  - `update_all_feature_correlations()` - Updates all shadow/active features
  - `auto_deprecate_low_correlation_features()` - Auto-deprecates shadow features with |corr| < 0.05 after 30 days
  - `detect_feature_drift()` - Detects drift > 0.1 for active features

- `temporal/activities/feature_monitoring.py` - Temporal activities
  - `update_feature_correlations` - Updates correlations + auto-deprecation
  - `detect_feature_drift` - Drift detection for active features
  - `emit_feature_event` - Event logging

### Modified Files
- `temporal/workflows/learning_loop.py` - Added `_run_feature_monitoring()` after outcome processing
- `temporal/activities/__init__.py` - Export new activities
- `temporal/worker.py` - Register activities in metrics worker
- `requirements.txt` - Added scipy>=1.11.0

## Data Flow
```
derived_feature_values (entity_type='idea')
         |
         v
    ideas.id
         |
         v
  decisions.idea_id
         |
         v
outcome_aggregates.decision_id → cpa
```

## Test Results
```
Test 1 (insufficient samples <30): PASS - returns None
Test 2 (perfect positive correlation): PASS (corr=1.0000)
Test 3 (negative correlation): PASS (corr=-1.0000)
Test 4 (near-zero correlation): PASS (corr=0.0706)
```

## Events Emitted
- `feature.correlations.updated` - After correlation update
- `feature.auto_deprecated` - When shadow feature auto-deprecated
- `feature.drift_detected` - When active feature drift > 0.1

## Thresholds
| Constant | Value | Description |
|----------|-------|-------------|
| MIN_SAMPLES_FOR_CORRELATION | 30 | Minimum samples for correlation |
| LOW_CORRELATION_THRESHOLD | 0.05 | Auto-deprecate if |corr| < this |
| DRIFT_THRESHOLD | 0.1 | Significant drift threshold |
| DEPRECATION_DAYS | 30 | Days before auto-deprecation |

## Integration
Feature monitoring runs automatically at the end of every Learning Loop execution (both batch and individual modes).

## Validation
- [x] Syntax check passed
- [x] Unit tests for correlation logic passed
- [x] Worker imports verified
