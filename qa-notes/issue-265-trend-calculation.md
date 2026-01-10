# Issue #265: Add trend calculation to OutcomeService

## Summary
Added automatic trend calculation based on CPA comparison with previous outcome.

## Changes
- `calculate_trend(current_cpa, previous_cpa)` - static method
- `get_previous_outcome(creative_id)` - fetches last outcome for comparison
- `OutcomeAggregate.trend` field added to dataclass
- `aggregate()` now calculates and stores trend

## Trend Logic
| CPA Change | Trend Value |
|------------|-------------|
| < -10% | `improving` |
| > +10% | `declining` |
| within ±10% | `stable` |
| no previous data | `null` |

## Edge Cases Handled
1. **First outcome for creative** - trend = null (no previous to compare)
2. **CPA is null** (0 conversions) - trend = null
3. **Previous CPA is 0** - trend = null (avoid division by zero)

## Test Commands
```bash
cd decision-engine-service
uv pip install pytest
uv run pytest tests/unit/test_outcome_service.py -v
```

## Verification
- 32/32 unit tests passed
- 10 new tests for `TestTrendCalculation` class
- Boundary tests for ±10% threshold

## Files Modified
- `src/services/outcome_service.py`
- `tests/unit/test_outcome_service.py`

## PR
https://github.com/mosszxc/GenomAI/pull/278
