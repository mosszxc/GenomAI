# Keitaro Poller Connection Fix

**Date:** 2025-12-30
**Issue:** #186
**Workflow:** Keitaro Poller (0TrVJOtHiNEEAsTN)

## Problem

Keitaro Poller workflow was executing "successfully" but not collecting any metrics. Tables `raw_metrics_current` and `daily_metrics_snapshot` were empty.

## Investigation

1. Checked execution history - status was "success" but only 8 nodes executed
2. `Loop Over Campaigns` output 10 items but `Get Campaign Metrics` never executed
3. Found malformed connection in workflow JSON:

```json
"Loop Over Campaigns": {
  "1": [  // Should be "main"
    [
      {
        "node": "Get Campaign Metrics",
        "type": "0",  // Should be "main"
        "index": 0
      }
    ]
  ]
}
```

## Root Cause

Connection between `Loop Over Campaigns` (splitInBatches) and `Get Campaign Metrics` was corrupted. The key `"1"` and `"type": "0"` are invalid formats - n8n requires `"main"` for both.

## Fix

1. Used `replaceConnections` to fix all connections with correct format
2. Fixed `Aggregate Metrics` code that couldn't find tracker_id after fix

## Gotchas

- **n8n execution can show "success" even when nodes are skipped** - always check `executedNodes` count
- **splitInBatches connections are fragile** - can be corrupted during manual edits
- **pairedItem lookup is complex** - when data flows through splitInBatches, pairedItem indices may not match original positions

## Verification Steps

```sql
-- Check raw_metrics_current has data
SELECT COUNT(*), MAX(updated_at) FROM genomai.raw_metrics_current;
-- Expected: count > 0, updated_at recent
```

## Prevention

- Always use `n8n_validate_workflow` after manual connection edits
- Check execution preview to ensure all expected nodes are in `executedNodes`
- For splitInBatches loops, verify connection format is `"main"` not numeric

## Related

- Workflow: Keitaro Poller (0TrVJOtHiNEEAsTN)
- Tables: raw_metrics_current, daily_metrics_snapshot
- Downstream: Snapshot Creator, Learning Loop
