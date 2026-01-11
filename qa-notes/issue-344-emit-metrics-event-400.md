# Issue #344: emit_metrics_event returns 400 Bad Request

## Problem
Activity `emit_metrics_event` failed with 400 Bad Request when writing events to `event_log` table.

## Root Cause
- `entity_id` column in `event_log` has type **UUID**
- Workflows passed `workflow.info().workflow_id` (string like `"keitaro-poller-2026-01-11"`) as `entity_id`
- Supabase REST API rejected the non-UUID string with 400 Bad Request
- `MaintenanceCompleted` worked because `emit_maintenance_event` never sent `entity_id` (NULL is valid)

## Solution
1. Made `entity_id` optional in `EmitMetricsEventInput` (default=None)
2. Only include `entity_id` in payload if provided
3. Moved `workflow_id` to `payload.workflow_id` (jsonb field) to preserve traceability

## Files Changed
- `temporal/activities/metrics.py:326-370` - EmitMetricsEventInput + emit_metrics_event
- `temporal/workflows/keitaro_polling.py` - Removed entity_id from all events, added workflow_id to payload
- `temporal/workflows/metrics_processing.py:173-183` - Same change

## Follow-up Fix
Issue #342 (merged before #344) added `RawMetricsObserved` event with same bug.
Required additional commit to fix: `aa0b6b4`

## Testing
| Test | Result |
|------|--------|
| Unit tests | 85/85 passed |
| SQL INSERT without entity_id | OK (entity_id=null) |
| Post-deploy keitaro-poller trigger | **OK** - event recorded with entity_id=null |

## Verified in DB
```sql
SELECT event_type, entity_id, payload->>'workflow_id', occurred_at
FROM genomai.event_log WHERE event_type = 'keitaro.polling.completed';
-- Result: entity_id=null, workflow_id in payload
```

## PRs/Commits
- PR #384 (initial fix)
- Commit aa0b6b4 (follow-up for RawMetricsObserved)
