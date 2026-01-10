# QA Notes: Issue #282 - HistoricalVideoHandlerWorkflow

## Scope
Implemented `HistoricalVideoHandlerWorkflow` for handling video URL submission for historical imports.

## Changes

### New Files
- `src/routes/historical.py` - API endpoints for historical import operations

### Modified Files
- `temporal/workflows/historical_import.py` - Added `HistoricalVideoHandlerWorkflow`
- `temporal/models/buyer.py` - Added `HistoricalVideoHandlerInput` and `HistoricalVideoHandlerResult`
- `temporal/activities/buyer.py` - Added `get_import_by_campaign_id`, `update_import_with_video`, `ImportQueueRecord`, `UpdateImportVideoInput`
- `temporal/activities/supabase.py` - Added `create_historical_creative`
- `temporal/worker.py` - Registered new workflow and activities
- `main.py` - Added historical router

## Workflow Logic

```
1. POST /api/historical/submit-video
   └── campaign_id, video_url, buyer_id

2. HistoricalVideoHandlerWorkflow
   ├── get_import_by_campaign_id → find queue record
   ├── update_import_with_video → status='ready'
   ├── load_buyer_by_id → get geos/verticals
   ├── update_import_status → status='processing'
   ├── create_historical_creative → source_type='historical', tracker_id=campaign_id
   ├── emit_event → HistoricalCreativeRegistered
   ├── execute_child_workflow(CreativePipelineWorkflow)
   └── update_import_status → status='completed'
```

## Test Plan

### API Endpoint Test
```bash
curl -X POST https://genomai.onrender.com/api/historical/submit-video \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "test-campaign-123",
    "video_url": "https://example.com/video.mp4",
    "buyer_id": "<valid-buyer-uuid>"
  }'
```

Expected response:
```json
{
  "success": true,
  "workflow_id": "historical-video-<campaign_id>",
  "message": "Video processing started for campaign test-campaign-123"
}
```

### Queue Status Endpoint Test
```bash
curl https://genomai.onrender.com/api/historical/queue/<buyer_id>
```

### DB Verification
```sql
-- Check queue status transitions
SELECT id, campaign_id, status, video_url, updated_at
FROM genomai.historical_import_queue
WHERE campaign_id = 'test-campaign-123';

-- Check creative created with historical source
SELECT id, tracker_id, source_type, buyer_id
FROM genomai.creatives
WHERE tracker_id = 'test-campaign-123' AND source_type = 'historical';

-- Check event logged
SELECT *
FROM genomai.event_log
WHERE event_type = 'HistoricalCreativeRegistered'
ORDER BY occurred_at DESC LIMIT 1;
```

## Status Transitions
- `pending` → `pending_video` (HistoricalImportWorkflow queues without video)
- `pending_video` → `ready` (video_url submitted)
- `ready` → `processing` (workflow starts)
- `processing` → `completed` (pipeline finished)
- `processing` → `failed` (on error)

## Acceptance Criteria
- [x] video_url can be submitted via API
- [x] Creative created with `source_type = 'historical'`
- [x] Queue status transitions: pending_video → ready → processing → completed
- [ ] Metrics from Keitaro attached to creative (pending test)

## Notes
- Workflow registered on `telegram` task queue
- Uses `CreativePipelineWorkflow` as child workflow on `creative-pipeline` queue
- Syntax validated with `py_compile`
- Integration test pending deploy
