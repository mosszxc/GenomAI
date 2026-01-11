# Issue #314: Maintenance workflow integrity_issues=2 fix

## Problem
MaintenanceWorkflow reported `integrity_issues: 2` in event_log repeatedly.

## Root Cause Analysis

### 1. What were the integrity issues?
Two hypotheses without `delivered_at`:
- `4358f699...` - status=`pending`, no buyer_id - E2E test hypothesis
- `ef95307d...` - status=`failed`, no buyer_id - already failed hypothesis

### 2. Why were they counted?
The `check_data_integrity` activity queried:
```
?delivered_at=is.null&created_at=lt.{cutoff_1h}
```
This didn't filter by `status`, so **failed hypotheses** (which don't need delivery) were counted.

### 3. Why did count increase from 1 to 2?
- Initially: 1 failed hypothesis (`ef95307d`, 2025-12-31)
- Later: 1 more pending orphan hypothesis added by E2E test (`4358f699`, 2026-01-09)

## Fix Applied

### Code changes (`maintenance.py`)
1. Added `&status=eq.pending` filter - only pending hypotheses need delivery
2. Added `buyer_id` to select - to distinguish orphan hypotheses
3. Separate reporting for:
   - Real issues: pending hypotheses WITH buyer_id waiting for delivery
   - Orphan issues: pending hypotheses WITHOUT buyer_id (cannot be delivered)
4. Include hypothesis IDs in issue messages for debugging

### Code changes (`maintenance.py` - `emit_maintenance_event`)
1. Added optional `issues_details: List[str]` parameter
2. Added `integrity_issues_details` to event payload when issues exist

### Workflow changes
1. Pass `result.integrity_issues` list to `emit_maintenance_event`

### Data cleanup
```sql
UPDATE genomai.hypotheses
SET status = 'failed', delivered_at = NOW()
WHERE id = '4358f699-fd49-48d0-8cc1-9f09b5aba941';
```

## Test Verification
After fix:
```sql
SELECT * FROM genomai.hypotheses
WHERE delivered_at IS NULL AND status = 'pending'
AND created_at < NOW() - INTERVAL '1 hour';
-- Result: [] (empty)
```

Expected: Next MaintenanceWorkflow run should show `integrity_issues: 0`

## Files Changed
- `decision-engine-service/temporal/activities/maintenance.py`
- `decision-engine-service/temporal/workflows/maintenance.py`
