# QA Notes: Issue #326 - Staleness check error: NoneType.__format__

## Problem
MaintenanceWorkflow reported staleness check error:
```
Staleness check error: unsupported format string passed to NoneType.__format__
```

## Root Cause
In `maintenance.py:469-476`, format string `:.2f` was used on `staleness_score` which could be `None` when metrics calculation failed.

## Fix
1. **maintenance.py:468-471** - Added safe access to `staleness_score`:
   ```python
   staleness_score = result.get("metrics", {}).get("staleness_score")
   if staleness_score is None:
       staleness_score = 0.0
   ```

2. **staleness_detector.py:417-442** - Added try-except for each metric with neutral defaults:
   - `diversity` defaults to 0.5
   - `win_rate_trend` defaults to 0.0
   - `fatigue` defaults to 0.0
   - `days_stale` defaults to DAYS_STALE_THRESHOLD
   - `exploration` defaults to 0.5

## Verification
- [x] Syntax check passed
- [x] CI tests passed (Fast Tests, Slow Tests, Integration Tests)
- [x] PR merged: #329
- [x] Deploy live: dep-d5hm9t8gjchc739n2efg
- [ ] Manual trigger (requires API_KEY) - will be verified on next auto-run

## Next Auto-Run
MaintenanceWorkflow runs every 6 hours. Check `event_log` after next run:
```sql
SELECT payload FROM genomai.event_log
WHERE event_type = 'MaintenanceCompleted'
ORDER BY occurred_at DESC LIMIT 1;
```
Expected: `integrity_issues = 0` or no staleness check errors in `integrity_issues_details`.

## PR
https://github.com/mosszxc/GenomAI/pull/329
