# Issue #295: Telegram /confidence Command - Confidence Intervals

## Summary
Added `/confidence` command to Telegram bot showing win rate confidence intervals using Wilson score interval.

## Changes
- `decision-engine-service/src/services/confidence.py` - new service with Wilson score CI calculation
- `decision-engine-service/src/routes/telegram.py` - added `/confidence` handler and routing

## Test Results

### Wilson Score Formula Verification
```
10/23 wins: 25.6% - 63.2% (±18.8%)
5/7 wins: 35.9% - 91.8% (±27.9%)
Required samples for 45% WR, ±5% CI: 381
Required samples for 71% WR, ±5% CI: 317
```

### Output Format
```
<b>Component Confidence Intervals</b>

<b>fear</b> HIGH VARIANCE
  0% ±18% (95% CI)
  ├─ Range: 0% - 35%
  ├─ Sample size: 7
  ├─ For ±5% CI: +381 samples
  └─ Trend: stable ↔
```

## DB Query Used
```sql
SELECT component_type, component_value, win_rate, sample_size, win_count
FROM genomai.component_learnings
WHERE sample_size >= 3
ORDER BY sample_size DESC
LIMIT 5;
```

## Implementation Details
- Z-score 1.96 for 95% CI
- HIGH_VARIANCE_THRESHOLD = 10% (half-width)
- TARGET_CI_WIDTH = 5% for sample size calculation
- min_samples = 3 default filter
