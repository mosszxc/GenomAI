# QA Notes: Issue #256 - Test: Maintenance Process

## Summary
Tested and fixed MaintenanceWorkflow for periodic system cleanup tasks.

## Bugs Found and Fixed

### 1. Wrong column name in hypotheses check
- **File:** `temporal/activities/maintenance.py:215`
- **Bug:** Used `delivery_status` instead of `delivered_at`
- **Fix:** Changed to `delivered_at`

### 2. Wrong column names in buyer_states
- **File:** `temporal/activities/maintenance.py:69-106`
- **Bug:** Used `id`, `buyer_id` (non-existent columns)
- **Fix:** Changed to `telegram_id`, reset to idle instead of delete

### 3. Non-deterministic workflow code
- **File:** `temporal/workflows/maintenance.py:128`
- **Bug:** Used `datetime.utcnow()` in workflow (not allowed in Temporal)
- **Fix:** Changed to `workflow.now()`

## Test Results

### Workflow Execution
- **Workflow ID:** `maintenance-{{.ScheduledTime}}-2026-01-10T11:24:41Z`
- **Status:** Completed
- **Duration:** ~2 seconds

### MaintenanceCompleted Event
```json
{
  "buyers_reset": 0,
  "recommendations_expired": 0,
  "integrity_issues": 1
}
```

### Validation
- [x] Workflow executed without errors
- [x] MaintenanceCompleted event in event_log
- [x] No pending recommendations older than 7 days (expected)
- [x] No stale buyer states (expected - only idle state exists)
- [x] Integrity check detected 1 issue (hypotheses pending delivery)

## Commits
- `6170ba7` - fix: correct column names in maintenance activities + ruff lint/format
- `df82882` - fix: use workflow.now() instead of datetime.utcnow() in workflow

## Commands Used
```bash
# Trigger schedule
temporal schedule trigger --schedule-id maintenance

# Check workflow status
temporal workflow list --query 'WorkflowType="MaintenanceWorkflow"'

# Check results
SELECT * FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted';
```
