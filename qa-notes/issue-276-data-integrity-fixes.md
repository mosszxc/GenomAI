# Issue #276: DB Data Integrity Fixes

## Problem
Integration tests failing due to data integrity issues:
1. Decision without trace (`test_decision_has_trace`)
2. Invalid confidence value > 1 (`test_idea_confidence_versions`)

## Root Causes

### 1. Confidence overflow
- `learning_loop.py:463` - confidence calculated as `current + delta` without bounds
- Over multiple learning iterations, confidence accumulated beyond 1.0
- Found value: 1.5898969320461653

### 2. Decision without trace
- `decision_engine.py:117-118` - two separate saves without atomicity
- If `save_decision` succeeds but `save_decision_trace` fails, orphan decision created

## Fixes Applied

### Code fixes
1. **Clamp confidence**: `max(0.0, min(1.0, new_confidence))` in learning_loop.py
2. **Atomic save**: Try/except with rollback in decision_engine.py
3. **Helper function**: `delete_decision()` for rollback

### Data fixes
```sql
DELETE FROM genomai.decisions WHERE id = 'b56ebe47-674a-49c1-bb6d-eb0d74ac1f53';
UPDATE genomai.idea_confidence_versions SET confidence_value = 1.0 WHERE confidence_value > 1;
```

### DB constraints (migration)
```sql
ALTER TABLE genomai.idea_confidence_versions
ADD CONSTRAINT chk_confidence_range CHECK (confidence_value >= 0 AND confidence_value <= 1);

ALTER TABLE genomai.fatigue_state_versions
ADD CONSTRAINT chk_fatigue_positive CHECK (fatigue_value >= 0);
```

## Test Commands
```sql
-- Verify no orphan decisions
SELECT COUNT(*) FROM genomai.decisions d
LEFT JOIN genomai.decision_traces dt ON d.id = dt.decision_id
WHERE dt.id IS NULL;  -- Expected: 0

-- Verify no invalid confidence
SELECT COUNT(*) FROM genomai.idea_confidence_versions
WHERE confidence_value > 1 OR confidence_value < 0;  -- Expected: 0

-- Test constraint blocks invalid data
INSERT INTO genomai.idea_confidence_versions
(idea_id, confidence_value, version, source_outcome_id)
VALUES ('00000000-0000-0000-0000-000000000001', 1.5, 1, '00000000-0000-0000-0000-000000000002');
-- Expected: ERROR chk_confidence_range
```

## Edge Cases
- Confidence at boundaries (0.0, 1.0) - valid
- Negative delta pushing below 0 - clamped to 0
- Multiple failures pushing high positive delta - clamped to 1.0

## Related
- PR #277
- Issue #271 (where tests were added)
