# Issue #714: Add missing Temporal schedules

## Problem
Only 4 of 6 expected Temporal schedules were present:
- health-check
- maintenance
- daily-recommendations
- keitaro-poller

Missing:
- metrics-processor
- learning-loop

## Solution
Added `metrics-processor` and `learning-loop` to `temporal/schedules.py`.

These schedules serve as **catch-up mechanisms**:
- Child workflow chain (keitaro-poller → metrics-processor → learning-loop) works normally
- But if chain fails at any point, independent schedules will process missed data
- Each runs hourly to catch up on unprocessed snapshots/outcomes

## Changes
- `decision-engine-service/temporal/schedules.py`: Added imports and schedule definitions

## Test
```bash
grep -c '"metrics-processor":' decision-engine-service/temporal/schedules.py && \
grep -c '"learning-loop":' decision-engine-service/temporal/schedules.py && \
echo "OK: Both schedules present"
```
