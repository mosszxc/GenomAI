# QA Notes: Keitaro Poller Pipeline Fix

**Date:** 2025-12-30
**Workflow:** Keitaro Poller (`0TrVJOtHiNEEAsTN`)

## Issues Found & Fixed

### 1. Upsert Raw Metrics - Duplicate Key Error
**Problem:** Supabase node used `operation: "create"` which failed on existing records with "duplicate key value violates unique constraint"

**Root Cause:** Need upsert behavior, not insert

**Fix:** Changed to HTTP Request with:
- `?on_conflict=tracker_id` (NOT `tracker_id,date` - PK is only `tracker_id`)
- Header: `Prefer: resolution=merge-duplicates`
- Header: `Content-Profile: genomai`

### 2. Sync to Queue - Invalid Column Error
**Problem:** When metrics below threshold, returned `{synced: false, clicks, cost}` which got passed to Upsert Queue node causing "Could not find 'clicks' column" error

**Root Cause:** Sync to Queue Code node returned wrong structure on filter-out

**Fix:** Return empty array `[]` instead of object when below threshold - stops flow cleanly

### 3. Loop Over Campaigns - Broken Connections
**Problem:** Workflow stopped after 8 nodes, 3 seconds - Loop didn't execute Get Campaign Metrics

**Root Cause:** n8n partial_update API created malformed connection format:
```json
// WRONG
"Loop Over Campaigns": {"1": [[{type: "1"}]]}

// CORRECT
"Loop Over Campaigns": {"main": [[], [{node...}]]}
```

**Fix:** Used `n8n_update_full_workflow` with complete nodes/connections arrays

## Constraints Discovered

- `raw_metrics_current` PK is only `tracker_id` (not composite with date)
- Table stores "current" metrics only - one record per tracker
- splitInBatches connections require exact format: `{"main": [[], [connections]]}`

## Test Results

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Duration | 3 sec | 57 sec |
| Nodes executed | 8 | 17 |
| Records upserted | 0 (error) | 14 |
| Status | Error | Success |

## Verification Query

```sql
SELECT tracker_id, date, metrics->>'clicks' as clicks, updated_at
FROM genomai.raw_metrics_current
ORDER BY updated_at DESC LIMIT 5;
```
