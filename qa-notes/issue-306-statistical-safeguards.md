# QA Notes: Issue #306 - Statistical Safeguards for Features

## Summary
Implemented statistical safeguards to prevent false discoveries during ML feature engineering.

## Implementation

### New Module: `statistical_validation.py`
Located at: `decision-engine-service/src/services/statistical_validation.py`

#### Functions Implemented:
| Function | Purpose |
|----------|---------|
| `adjusted_significance_threshold()` | Bonferroni correction for multiple hypothesis testing |
| `wilson_confidence_interval()` | Wilson score CI for small samples |
| `validate_sample_size()` | Minimum sample validation |
| `validate_feature_significance()` | P-value significance with Bonferroni |
| `detect_simpsons_paradox()` | Detects when segments disagree with aggregate |
| `check_correlation_stability()` | Rolling correlation std check |
| `full_validation_for_promotion()` | Complete validation for feature promotion |

### Integration: `feature_registry.py`
Added `can_promote_with_statistics()` function that runs full statistical validation.

### Migration: `034_feature_statistical_validation.sql`
Added columns to `feature_experiments`:
- `p_value` - P-value from correlation test
- `correlation_std_dev` - Rolling correlation std for stability

## Test Results

### Wilson Confidence Interval
```
n=8, wins=7:  CI = [0.53, 0.98], width = 0.45
n=100, wins=50: CI = [0.40, 0.60], width = 0.19
```
- Smaller samples → wider intervals
- Correctly rejects decisions with wide CIs

### Bonferroni Correction
```
n=10 features: threshold = 0.005 (vs 0.05 base)
```
- Properly adjusts for multiple testing

### Simpson's Paradox Detection
- Correctly detects when segment correlations disagree
- Example: aggregate=0.15, MX=0.12, DE=-0.05 → paradox detected

## Migration Verification
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'feature_experiments'
AND column_name IN ('p_value', 'correlation_std_dev');
-- Returns: p_value, correlation_std_dev ✓
```

## Usage Example
```python
from src.services.feature_registry import can_promote_with_statistics

can_promote, errors = await can_promote_with_statistics(
    name="hook_count",
    p_value=0.001,
    correlation_history=[0.12, 0.15, 0.11, 0.13],
    segment_correlations={"MX": 0.10, "DE": 0.15, "US": 0.12}
)
```

## Definition of Done Checklist
- [x] Bonferroni correction implemented
- [x] Wilson confidence intervals for winrate
- [x] Simpson's paradox detection
- [x] Stability check (rolling correlation std)
- [x] Promotion uses full validation (`can_promote_with_statistics`)
