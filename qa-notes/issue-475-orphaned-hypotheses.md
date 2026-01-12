# Issue #475: Orphaned Hypotheses Fix

## Problem
Hypotheses were being created even when `buyer_id=null`, making them undeliverable.
These orphaned hypotheses accumulated in the database indefinitely.

## Changes

### 1. creative_pipeline.py
- Changed condition from `if decision_result.is_approved:` to `if decision_result.is_approved and input.buyer_id:`
- Now hypothesis generation is skipped if no buyer_id
- Added logging for skipped hypothesis generation

### 2. maintenance.py (activity)
- Added `cleanup_orphaned_hypotheses()` activity
- Finds and deletes hypotheses with `buyer_id IS NULL`

### 3. maintenance.py (workflow)
- Added `run_orphan_hypothesis_cleanup` flag to MaintenanceInput
- Added `orphaned_hypotheses_deleted` to MaintenanceResult
- Added Step 5b to call cleanup activity

## Test

```bash
WORKTREE=".worktrees/issue-475-arch-critical-orphaned-hypotheses--созда" && grep -q "cleanup_orphaned_hypotheses" "$WORKTREE/decision-engine-service/temporal/activities/maintenance.py" && grep -q "run_orphan_hypothesis_cleanup" "$WORKTREE/decision-engine-service/temporal/workflows/maintenance.py" && grep -q "and input.buyer_id" "$WORKTREE/decision-engine-service/temporal/workflows/creative_pipeline.py" && echo "PASS"
```

## SQL Verification (manual)
```sql
-- Should return 0 after cleanup
SELECT COUNT(*) FROM genomai.hypotheses
WHERE buyer_id IS NULL;
```
