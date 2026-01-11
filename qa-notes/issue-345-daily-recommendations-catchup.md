# Issue #345: daily-recommendations schedule missed execution

## Problem
`daily-recommendations` schedule showed 29h staleness. Last `RecommendationGenerated` event was from Jan 10 05:11.

## Root Cause
1. **catchup_window too short**: 5 minutes catchup window meant that if workers were unavailable during scheduled time (e.g., during deploy at 09:00 UTC), the schedule was permanently skipped.
2. **Blocking bug found during verification**: `get_active_buyers` activity requested non-existent columns `geo` and `vertical` (only `geos` and `verticals` arrays exist in `buyers` table), causing 400 Bad Request.

## Fix
1. `schedules.py`: Increase `catchup_window` to 24h for cron schedules (daily runs)
2. Schedule needed to be recreated (delete + create) to apply new settings
3. **Issue #390**: Fixed `get_active_buyers` to remove non-existent columns from SELECT

## Verification Steps

### 1. Schedule Recreation
```bash
# Delete old schedule
python -c "from temporal.schedules import delete_schedule..."
# 2026-01-11 17:35:36 - Deleted schedule: daily-recommendations

# Create with new settings
python -c "from temporal.schedules import create_schedule..."
# 2026-01-11 17:35:45 - Created schedule: daily-recommendations
```

### 2. Initial Trigger (FAILED)
```
daily-recommendations-2026-01-11T14:35:52Z: status=FAILED
Error: 400 Bad Request - geo,vertical columns don't exist
```

### 3. Fix #390 Deployed
```
PR #391 merged: fix(#390): remove non-existent columns
Deploy: dep-d5hrd3juibrs73ahl1t0, status=live at 14:42:59
```

### 4. Re-trigger (PASSED)
```
python -m temporal.schedules trigger daily-recommendations
# 2026-01-11 17:43:47 - Triggered

Workflow: daily-recommendations-2026-01-11T14:43:47Z
Status: COMPLETED
```

### 5. Event Verification
```sql
SELECT event_type, entity_id, occurred_at
FROM genomai.event_log
WHERE event_type = 'RecommendationGenerated'
ORDER BY occurred_at DESC LIMIT 1;

-- Result:
-- RecommendationGenerated
-- 6f9e7581-273d-4ae3-92bc-8bd761c92f69
-- 2026-01-11 14:43:55.253859
```

## Production Test Result
**PASSED**

| Check | Result |
|-------|--------|
| Schedule recreated | Yes, with 24h catchup_window |
| Workflow triggered | Success |
| Workflow completed | COMPLETED |
| Event in event_log | RecommendationGenerated at 14:43:55 |

## Related Issues
- #390: BUG: get_active_buyers requests non-existent columns geo,vertical (found and fixed during this verification)

## Commits
- `10d14b0`: fix(#345): catchup_window 24h for cron
- `248bd0a`: fix(#390): remove non-existent columns from get_active_buyers query
