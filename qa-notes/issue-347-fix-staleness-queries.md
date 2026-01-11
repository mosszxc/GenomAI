# Issue #347: Fix check_staleness activity queries

## Problem
`check_staleness` activity in MaintenanceWorkflow queried non-existent table/columns:
1. Table `outcomes` does not exist (should be `outcome_aggregates`)
2. Column `fatigue_state` does not exist on `ideas` (should use `fatigue_state_versions` table)

## Evidence (from Render logs)
```
HTTP Request: GET .../outcomes?created_at=gte.2025-12-12... "HTTP/1.1 404 Not Found"
HTTP Request: GET .../ideas?status=eq.active&select=id,fatigue_state... "HTTP/1.1 400 Bad Request"
```

## Solution

### 1. Fix `calculate_win_rate_trend` (staleness_detector.py:150-179)
- Changed table from `outcomes` to `outcome_aggregates`
- Removed avatar_id/geo filters (outcome_aggregates doesn't have these columns directly)
- Query now: `outcome_aggregates?created_at=gte.{date}&select=cpa,created_at`

### 2. Fix `calculate_fatigue_ratio` (staleness_detector.py:233-300)
- Changed from querying non-existent `ideas.fatigue_state` to two-step approach:
  1. Get active ideas: `ideas?status=eq.active&select=id`
  2. Get latest fatigue values: `fatigue_state_versions?idea_id=in.(ids)&order=idea_id,version.desc`
- Deduplicate by idea_id to get latest version
- Count ideas with `fatigue_value > FATIGUE_THRESHOLD`

## Testing

### Unit tests
```bash
cd decision-engine-service && python3 -m pytest tests/unit/ -v
# Result: 85 passed
```

### SQL verification
```sql
-- All queries now return 200 OK (empty result if no data)
SELECT cpa, created_at FROM genomai.outcome_aggregates WHERE created_at >= NOW() - INTERVAL '30 days';
SELECT id FROM genomai.ideas WHERE status = 'active';
SELECT idea_id, fatigue_value, version FROM genomai.fatigue_state_versions ORDER BY idea_id, version DESC;
```

## Acceptance Criteria
- [x] Fix table name: `outcomes` -> `outcome_aggregates`
- [x] Fix fatigue query to use `fatigue_state_versions` table
- [x] All queries in check_staleness return 200 OK
