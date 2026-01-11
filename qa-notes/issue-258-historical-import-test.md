# Issue #258: Test Historical Import Process

## Summary
Validated historical import process. Found GAP: no Temporal workflow exists for video_url handling in historical import.

## Test Date
2026-01-10

## Test Plan Execution

### 1. Queue Entry Creation (PASS)
- **Status:** `pending_video`
- **Campaign:** 10136
- **Buyer:** TU (d75efea6-597f-46a1-820c-e82ec5fe2449)
- **Metrics from Keitaro:** clicks=1190, conversions=6, cost=85.20

```sql
SELECT campaign_id, status, video_url, metrics, buyer_id
FROM genomai.historical_import_queue
WHERE status = 'pending_video';
-- Result: 3 entries found
```

### 2. Video URL Submission (MANUAL)
- **No Temporal workflow exists** for video_url submission
- Had to update directly in database:

```sql
UPDATE genomai.historical_import_queue
SET video_url = 'https://test.example.com/historical-video-test.mp4',
    status = 'ready'
WHERE campaign_id = '10136';
```

### 3. Creative Registration (MANUAL)
- **CreativeRegistrationWorkflow** uses `source_type = 'telegram'` (hardcoded)
- Had to insert creative manually:

```sql
INSERT INTO genomai.creatives (video_url, source_type, buyer_id, tracker_id, status)
VALUES ('...', 'historical', '...', '10136', 'registered');
```

### 4. Keitaro Metrics (PASS)
- Metrics exist in `historical_import_queue.metrics` column
- Populated by KeitaroPollerWorkflow

## Findings

### GAP: Missing Historical Video URL Handler

**Issue:** No Temporal workflow handles video_url for historical imports.

**Current State:**
1. `HistoricalImportWorkflow` - creates queue entries with `pending_video` status
2. `CreativeRegistrationWorkflow` - registers creatives but uses `source_type = 'telegram'`

**Missing:**
- Workflow/API to receive video_url for pending_video entries
- Update queue status: pending_video → ready → processing → completed
- Create creative with `source_type = 'historical'`
- Link creative to historical metrics

**n8n Equivalent:** `UYgvqpsU3TMzb2Qd` (Historical Import Video Handler)

### Workaround
Currently requires manual database updates or n8n workflow.

## Recommendations

1. **Create HistoricalVideoHandlerWorkflow** in Temporal:
   - Signal-based or API-triggered
   - Accept: campaign_id + video_url
   - Update queue status
   - Create creative with source_type = 'historical'
   - Link to historical metrics
   - Trigger CreativePipelineWorkflow

2. **Alternative:** Add API endpoint `/api/historical/submit-video`
   - Accept: campaign_id, video_url, buyer_id
   - Start appropriate workflow

## Test Data Created

| Table | ID | Notes |
|-------|-----|-------|
| historical_import_queue | 1349a8b0-731f-4493-b19e-ed40bffef575 | status=completed |
| creatives | 0a2c852d-819e-4a4e-af5e-db0dc0263efc | source_type=historical |

## Verdict
**PARTIAL PASS** - Queue creation and metrics import work. Video URL handling requires manual intervention.
