# QA Notes: Issue #267 - Auto-register Keitaro tracker_id

## Problem
`MetricsProcessingWorkflow` returned `IDEA_NOT_FOUND` for all production snapshots because `creative_idea_lookup` view did not find the link between `tracker_id` and `idea_id`.

## Root Cause
The `creative_idea_lookup` VIEW computed `idea_id` only via `get_idea_id_by_creative()` function, which requires a chain: `decomposed_creatives` -> `canonical_hash` -> `ideas`.

It ignored the **direct** `creatives.idea_id` column that was already populated for some creatives.

## Solution
Updated VIEW to use `COALESCE`:
```sql
COALESCE(c.idea_id, genomai.get_idea_id_by_creative(c.id)) AS idea_id
```

Now:
1. Direct `idea_id` from `creatives` takes precedence
2. Falls back to computed `idea_id` via decomposed chain

## Test Verification
```sql
-- Before: tracker_id=8406 returned idea_id=NULL (via function only)
-- After: tracker_id=8406 returns idea_id=86ce27f1-8f81-4e2c-95fd-916cae445928

SELECT * FROM genomai.creative_idea_lookup WHERE tracker_id = '8406';
-- Returns: creative_id, tracker_id=8406, idea_id=86ce27f1...
```

Full chain verified:
- Snapshot: tracker_id=8406, conversions=5, cost=75.5
- Lookup: idea_id=86ce27f1...
- Decision: APPROVE exists for this idea

## Edge Cases
- Creatives without `tracker_id` - not in view (by design)
- Creatives without `idea_id` AND without `decomposed_creatives` - idea_id=NULL (expected for historical imports not processed)
- Only 1 tracker_id exists in both `creatives` AND `daily_metrics_snapshot` (8406) - limited test data

## Key Insight
`tracker_id` = `keitaro_campaign_id` - both are the same Keitaro-assigned campaign ID.

## Files Changed
- `infrastructure/migrations/025_creative_idea_lookup_sync.sql`
