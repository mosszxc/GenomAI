# Issue #312: Archive Failed Creatives

## Problem
E2E test found creative with `transcription_failed` status that was not being processed.
- Creative ID: `29ed41a9-2275-45a0-9a5d-806285ef0ff7`
- Status: `transcription_failed`
- Created: 2025-12-29

## Root Cause
MaintenanceWorkflow had `mark_stuck_transcriptions_failed` activity (from #283) but no mechanism to archive/cleanup creatives that remain in `transcription_failed` status.

## Solution
Added `archive_failed_creatives` activity to MaintenanceWorkflow:
- Archives creatives with `transcription_failed` status older than retention period
- Default retention: 7 days (configurable via `failed_creative_retention_days`)
- Changes status from `transcription_failed` to `archived`

## Files Changed
- `temporal/activities/maintenance.py` - new `archive_failed_creatives` activity
- `temporal/workflows/maintenance.py` - Step 4 for archival, updated Input/Result
- `temporal/activities/__init__.py` - export new activity + missing `check_staleness`
- `temporal/worker.py` - register new activities

## Workflow Flow (Updated)
1. Reset stale buyer states
2. Expire old recommendations
3. Mark stuck transcriptions as failed
4. **Archive old failed creatives** (NEW)
5. Run data integrity checks
6. Check system staleness
7. Emit maintenance event

## Test
```sql
-- Before: 1 creative with transcription_failed
SELECT status, count(*) FROM genomai.creatives GROUP BY status;
-- status: transcription_failed, cnt: 1

-- After archival
-- status: archived, cnt: 1
```

## Verification
```bash
cd decision-engine-service
python3 -c "
from temporal.activities.maintenance import archive_failed_creatives
from temporal.workflows.maintenance import MaintenanceInput, MaintenanceResult
print('Import OK')
print(f'Input has failed_creative_retention_days: {\"failed_creative_retention_days\" in [f.name for f in MaintenanceInput.__dataclass_fields__.values()]}')
print(f'Result has failed_creatives_archived: {\"failed_creatives_archived\" in [f.name for f in MaintenanceResult.__dataclass_fields__.values()]}')
"
# Import OK
# Input has failed_creative_retention_days: True
# Result has failed_creatives_archived: True
```

## Acceptance Criteria
- [x] Identify why creative was stuck - no cleanup mechanism
- [x] Add archival logic to MaintenanceWorkflow
- [x] Archive stuck creative - status changed to `archived`
- [x] Verify Python imports work correctly
