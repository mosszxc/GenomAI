# Issue #313: Failed Hypothesis Retry Mechanism

## Problem
E2E test detected hypothesis with status `failed` that was never retried.
- Hypothesis ID: `ef95307d-b2aa-4621-8f0e-89366fd4a477`
- Status: `failed`
- No retry mechanism existed

## Solution
Added automatic retry mechanism for failed hypothesis deliveries:

1. **Migration 032**: Added retry tracking columns to `hypotheses` table
   - `retry_count` (INT) - tracks delivery attempts
   - `last_retry_at` (TIMESTAMPTZ) - prevents rapid retries
   - `last_error` (TEXT) - stores failure reason

2. **Activities** (`hygiene_cleanup.py`):
   - `retry_failed_hypotheses`: Finds failed hypotheses, attempts re-delivery via Telegram
   - `cleanup_exhausted_hypotheses`: Marks hypotheses that exhausted retries as `abandoned`

3. **MaintenanceWorkflow** integration:
   - New Step 6: Retry failed hypotheses (max 3 attempts)
   - Cleanup exhausted hypotheses older than 7 days
   - New result fields: `hypotheses_retried`, `hypotheses_retry_succeeded`, `hypotheses_abandoned`

## Retry Logic
- Max 3 retry attempts per hypothesis
- 1 hour cooldown between retries
- Processes max 10 hypotheses per maintenance run
- After 3 failed attempts + 7 days: marked as `abandoned`

## Files Changed
- `infrastructure/migrations/032_hypothesis_retry.sql` (new)
- `decision-engine-service/temporal/activities/hygiene_cleanup.py` (2 new activities)
- `decision-engine-service/temporal/workflows/maintenance.py` (Step 6 added)
- `decision-engine-service/temporal/worker.py` (activities registered)

## Testing
- Syntax check: PASSED
- Full test requires deployment and MaintenanceWorkflow trigger:
  ```bash
  python -m temporal.schedules trigger maintenance
  ```

## Verification Query
```sql
SELECT id, status, retry_count, last_retry_at, last_error
FROM genomai.hypotheses
WHERE status IN ('failed', 'abandoned')
ORDER BY created_at DESC
LIMIT 10;
```
