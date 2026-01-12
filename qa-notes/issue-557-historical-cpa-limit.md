# Issue #557: Missing LIMIT in get_historical_cpa query

## What Changed
- Added `&limit=1000` to `get_historical_cpa()` query in `outcome_service.py:293`
- Prevents memory overflow from unbounded result sets

## Why
Without LIMIT, query could return thousands of records causing:
- Memory overflow on server
- Slow response times
- Potential OOM crash

## Test
```bash
grep -q "limit=1000" .worktrees/issue-557-*/decision-engine-service/src/services/outcome_service.py && echo "PASS: LIMIT found"
```
