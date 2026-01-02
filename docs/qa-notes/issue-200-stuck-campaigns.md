# QA Notes: Issue #200 - 337 Campaigns Stuck in historical_import_queue

## Problem
337 campaigns in `historical_import_queue` with `pending_video` status were never processed. Created 27-30 December 2025.

## Root Cause
Historical import workflow requires video URL to create:
1. creative (needs video_url)
2. transcript (needs video)
3. decomposed_creative (needs transcript)
4. idea (needs decomposed_creative)
5. decision (needs idea)
6. outcome_aggregate (needs decision)

Without video, the full pipeline cannot run. These campaigns came from Keitaro with metrics but no associated video files.

## Analysis
- All 337 campaigns had `buyer_id` (linked to buyers)
- All had `metrics` (cost, clicks, conversions, cpa)
- None had `video_url`
- No creatives existed for these campaign_ids

## Solution Options Considered
1. **Cleanup (delete)** - loses metrics data
2. **Telegram reminder** - impractical, videos don't exist for historical campaigns
3. **Metrics-only learning** - requires major architecture changes (anonymous ideas)

## Chosen Solution
Added `expired` status for campaigns stuck too long without video:

### Migration 023_historical_queue_expired_status
```sql
ALTER TABLE genomai.historical_import_queue
DROP CONSTRAINT IF EXISTS historical_import_queue_status_check;

ALTER TABLE genomai.historical_import_queue
ADD CONSTRAINT historical_import_queue_status_check
CHECK (status IN ('pending_video', 'ready', 'processing', 'completed', 'failed', 'expired'));
```

### Data Fix
```sql
UPDATE genomai.historical_import_queue
SET status = 'expired', updated_at = NOW()
WHERE status = 'pending_video'
  AND created_at < NOW() - INTERVAL '5 days';
```

Result: 336 campaigns → `expired`, 1 campaign remains `pending_video` (created <5 days ago)

## Future Considerations
- Pipeline Health Monitor could automatically expire old pending_video campaigns
- Consider adding Telegram notification when campaigns expire
- Metrics data preserved in `expired` records for potential future use

## Status Distribution After Fix
| Status | Count |
|--------|-------|
| expired | 336 |
| pending_video | 1 |

## Test Verification
```sql
SELECT status, COUNT(*) FROM genomai.historical_import_queue GROUP BY status;
-- expired: 336, pending_video: 1
```
