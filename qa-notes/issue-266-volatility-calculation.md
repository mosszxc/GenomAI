# QA Notes: Issue #266 - Volatility Calculation

## Summary
Added volatility calculation to `OutcomeService.aggregate()` using coefficient of variation (CV).

## Changes Made

### `outcome_service.py`
1. **New method: `calculate_volatility(cpa_values: List[Decimal])`**
   - Input: list of CPA values (minimum 2 required)
   - Formula: CV = std_dev / mean
   - Returns: Decimal (0.0 - 1.0+) or None

2. **New method: `get_historical_cpa(creative_id, lookback_days=7)`**
   - Fetches CPA values from last 7 days
   - Used to calculate volatility trend

3. **Integration in `aggregate()`**
   - Gets historical CPA + current CPA
   - Calculates volatility before inserting outcome
   - Stores in `outcome_aggregates.volatility`

## Test Cases

| CPA Values | Result | Interpretation |
|------------|--------|----------------|
| [10, 12, 11] | 0.0909 | Low volatility (<0.1) |
| [10, 20, 15] | 0.3333 | High volatility (>0.3) |
| [5, 5, 5] | 0.0 | No volatility |
| [10] | None | Insufficient data |
| [] | None | No data |

## Volatility Interpretation
- `< 0.1` - Low volatility (stable performance)
- `0.1 - 0.3` - Medium volatility
- `> 0.3` - High volatility (unstable performance)

## Edge Cases
- First outcome for creative: volatility = None (only 1 data point)
- All CPA values equal: volatility = 0.0
- Mean CPA = 0: volatility = None (division by zero protection)
- None values in history: filtered out before calculation

## Testing Commands
```bash
# Trigger MetricsProcessingWorkflow
cd decision-engine-service && python -m temporal.schedules trigger metrics-processing

# Check volatility in database
SELECT id, creative_id, cpa, volatility, trend, created_at
FROM genomai.outcome_aggregates
WHERE volatility IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

## Integration Points
- `OutcomeAggregate` dataclass includes `volatility` field
- `to_dict()` returns volatility as float
- `insert_outcome()` stores volatility in database
