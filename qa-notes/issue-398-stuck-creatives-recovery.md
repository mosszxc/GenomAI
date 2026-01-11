# QA Notes: Issue #398 - Stuck Creatives Recovery

## Problem
Creatives were getting stuck at two stages without recovery:
1. **Transcription**: status='pending', no transcript (workflow never started or failed)
2. **Decomposition**: has transcript but no decomposed_creative (workflow failed mid-way)

### Data Before Fix
```
stuck_transcription: 3 creatives
stuck_decomposition: 4 creatives
Total: 7 creatives blocked in pipeline
```

## Solution
Added automatic recovery mechanism to MaintenanceWorkflow:

1. **New activity `find_stuck_creatives`**:
   - Detects creatives stuck on transcription (>5 min without transcript)
   - Detects creatives stuck on decomposition (>30 min with transcript but no decomposed)
   - Returns list with creative_id, buyer_id, stuck_reason

2. **Recovery integration in MaintenanceWorkflow**:
   - Calls `find_stuck_creatives` activity
   - For each stuck creative, starts child `CreativePipelineWorkflow`
   - Tracks recovered/failed counts in MaintenanceResult

3. **New config options**:
   ```python
   run_stuck_recovery: bool = True
   stuck_transcription_timeout_minutes: int = 5
   stuck_decomposition_timeout_minutes: int = 30
   ```

## Files Changed
- `temporal/activities/maintenance.py`: Added `find_stuck_creatives` activity
- `temporal/workflows/maintenance.py`: Added recovery step (Step 10)
- `temporal/worker.py`: Registered new activity
- `temporal/activities/__init__.py`: Exported new activity

## Testing

### Pre-deploy verification
```bash
make test  # 35 passed
```

### Production state after deploy
```sql
SELECT 'transcription' as stuck_reason, count(*)
FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
WHERE t.id IS NULL AND c.status = 'pending'
  AND c.created_at < now() - interval '5 minutes';
-- Result: 3

SELECT 'decomposition' as stuck_reason, count(*)
FROM genomai.creatives c
JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = c.id
WHERE d.id IS NULL AND t.created_at < now() - interval '30 minutes';
-- Result: 4
```

### Expected behavior
- MaintenanceWorkflow runs every 6 hours
- On next run, will detect 7 stuck creatives
- Will start CreativePipelineWorkflow for each
- Creatives will complete pipeline processing

## Verification Command
After next MaintenanceWorkflow run:
```sql
-- Check event_log for recovery events
SELECT * FROM genomai.event_log
WHERE event_type = 'MaintenanceCompleted'
ORDER BY occurred_at DESC LIMIT 1;

-- Verify stuck creatives count decreased
SELECT count(*) FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
WHERE t.id IS NULL AND c.status = 'pending'
  AND c.created_at < now() - interval '5 minutes';
```

## PR
- https://github.com/mosszxc/GenomAI/pull/412
- Merged and deployed: 2026-01-11

## Status
- [x] Code implemented
- [x] Tests passed
- [x] PR merged
- [x] Deployed to production
- [ ] Verified in production (pending next MaintenanceWorkflow run)
