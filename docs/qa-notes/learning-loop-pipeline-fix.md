# QA Notes: Learning Loop Pipeline Fix (#202)

## Issue
Learning Loop not populating `component_learnings` - 0 records despite outcomes.

## Root Cause
`Snapshot Creator` workflow stopped at `Check Snapshot Exists` node because:
- Supabase GET operation returns **0 items** when no record found
- n8n doesn't pass data to next node when output is empty
- `If Not Exists` never executed because it had no input data

## Fix Applied

### Removed Nodes
- `Check Snapshot Exists` (Supabase GET)
- `If Not Exists` (IF node)
- `Skip Existing` (NoOp)
- `Create Daily Snapshot` (Supabase CREATE)

### Added Nodes
1. **Upsert Snapshot** (HTTP Request)
   - Uses Supabase REST API with `Prefer: resolution=merge-duplicates,return=representation`
   - Always returns data (insert or update)

2. **Normalize Response** (Code node)
   - Extracts first item from Supabase array response
   - Returns normalized `{id, tracker_id, date, metrics}`

### Updated References
All downstream nodes updated to use `$('Normalize Response').item.json` instead of `$('Create Daily Snapshot').first().json[0]`.

### Added Retry
Outcome Aggregator API call now has retry (3 attempts, 5s wait) for when Decision Engine is sleeping.

## Test Results
```
daily_metrics_snapshot: 0 → 4 records
Snapshot Creator: SUCCESS
Outcome Processor: SUCCESS
Outcome Aggregator: SUCCESS (IDEA_NOT_FOUND for test data - expected)
```

## Gotchas

### n8n Supabase Node Behavior
- Supabase GET returns **empty array** (0 items) when no records found
- This stops workflow flow because next node has no input
- Solution: Use HTTP Request with UPSERT or add Code node to handle empty case

### Supabase REST API Array Response
- `Prefer: return=representation` returns array `[{...}]`
- Must extract first item: `response[0]`
- In n8n expression: `$json[0]` or use Code node

### Expression Context
- `$('NodeName').item.json` - current item from named node
- `$('NodeName').first().json` - first item (may not work with array)
- When in doubt, use Code node for data transformation

## Related
- Issue #187: Keitaro Poller connection fix (closed)
- Snapshot Creator calls Outcome Processor and Outcome Aggregator
