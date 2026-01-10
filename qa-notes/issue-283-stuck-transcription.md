# Issue #283: Stuck Creative in Transcription Queue

## Problem
E2E test detected 1 creative stuck in transcription queue for >5 minutes.

## Root Cause
Creative with test URL `test.example.com/historical-video-test.mp4` — invalid/inaccessible URL that cannot be transcribed.

## Resolution

### Immediate Fix
- Manually marked creative `0a2c852d-819e-4a4e-af5e-db0dc0263efc` as `transcription_failed`

### Automated Monitoring
Added `mark_stuck_transcriptions_failed` activity to MaintenanceWorkflow:
- Runs every 6 hours as part of maintenance
- Timeout: 10 minutes (configurable via `stuck_transcription_timeout_minutes`)
- Marks creatives with status `registered` and no transcript after timeout as `transcription_failed`

## Files Changed
- `temporal/activities/maintenance.py` — new activity
- `temporal/workflows/maintenance.py` — workflow update
- `temporal/worker.py` — activity registration
- `temporal/activities/__init__.py` — export

## Test
```sql
-- Verify no stuck creatives
SELECT count(*) FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
WHERE t.id IS NULL AND c.status = 'registered'
  AND c.created_at < now() - interval '10 minutes';
-- Result: 0
```

## Acceptance Criteria
- [x] Identify root cause — test URL inaccessible
- [x] Process stuck creative — marked as `transcription_failed`
- [x] Add monitoring — MaintenanceWorkflow now handles stuck transcriptions
