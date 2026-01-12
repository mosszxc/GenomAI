# QA Notes: Issue #489 - Workflow Timing Optimization

## Changes Made

### 1. schedules.py
- Changed `keitaro-poller` interval: 10 min → 1 hour
- Removed `metrics-processor` from SCHEDULES
- Removed `learning-loop` from SCHEDULES
- Updated descriptions and docstrings

### 2. keitaro_polling.py
- Added `MetricsProcessingWorkflow` as child workflow
- Chain: keitaro → metrics-processor → learning-loop
- Added `metrics_processing_triggered` field to result

### 3. Documentation
- Updated CLAUDE.md workflows table
- Updated docs/TEMPORAL_WORKFLOWS.md architecture diagram and workflow descriptions

## Before/After

| Metric | Before | After |
|--------|--------|-------|
| Schedules | 6 | 4 |
| keitaro-poller interval | 10 min | 1 hour |
| metrics-processor | Independent (30 min) | Child of keitaro |
| learning-loop | Independent (1 hour) | Child of metrics |

## Architecture

```
Before:
- keitaro-poller (10 min) [schedule]
- metrics-processor (30 min) [schedule]
- learning-loop (1 hour) [schedule]
(independent, can run out of order)

After:
- keitaro-poller (1 hour) [schedule]
  └── metrics-processor [child workflow]
      └── learning-loop [child workflow]
(explicit chain, guaranteed order)
```

## Testing

### Pre-merge
- [x] Syntax check: `python3 -m py_compile` passed
- [x] Pre-commit hooks: ruff lint, ruff format, critical tests passed
- [x] Pre-push hooks: all unit tests passed

### Post-deploy (manual verification needed)
After deploy, trigger keitaro-poller:
```bash
python -m temporal.schedules trigger keitaro-poller
```

Expected:
1. KeitaroPollerWorkflow starts
2. Creates snapshots
3. Triggers MetricsProcessingWorkflow as child
4. MetricsProcessingWorkflow triggers LearningLoopWorkflow

Verify in Temporal UI that child workflows are created.

## Rollback Plan

If issues found:
1. Revert schedules.py changes
2. Remove child workflow trigger from keitaro_polling.py
3. Re-deploy
4. Re-create schedules: `python -m temporal.schedules delete && python -m temporal.schedules create`

## Notes

- MetricsProcessingWorkflow already triggered LearningLoopWorkflow as child (no change there)
- Old schedules (metrics-processor, learning-loop) need to be deleted manually in Temporal Cloud after deploy
