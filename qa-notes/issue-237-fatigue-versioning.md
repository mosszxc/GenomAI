# Issue #237: Fatigue State Versioning

## Problem
`fatigue_state_versions` table was empty while `idea_confidence_versions` had 3 records.
Learning Loop was only updating confidence, not fatigue.

## Root Cause
Original MVP playbook explicitly forbade fatigue events. However, versioning for baseline data collection is valuable even without active fatigue constraint logic.

## Solution
Added fatigue versioning to Learning Loop with MVP formula:
- `fatigue_value = exposure_count` (incremented by 1 for each outcome processed)

### Changes Made
File: `decision-engine-service/src/services/learning_loop.py`

1. Added `get_current_fatigue(idea_id)` - reads latest fatigue state
2. Added `insert_fatigue_version(idea_id, fatigue_value, version, outcome_id)` - appends new version
3. Integrated in `process_single_outcome()` after confidence versioning
4. Added `fatigue_updates` field to `LearningResult` dataclass

## Test Plan

### Pre-test Setup
```sql
-- Reset one outcome for testing
UPDATE genomai.outcome_aggregates
SET learning_applied = false
WHERE id = '15dfa1f5-51fa-47d7-9cac-3a87d05f429c';
```

### Test Execution
```bash
# After deploy, trigger learning loop
curl -X POST https://genomai.onrender.com/learning/process
```

### Verification
```sql
-- Check fatigue_state_versions has data
SELECT COUNT(*) FROM genomai.fatigue_state_versions;
-- Expected: > 0

-- Check specific entry
SELECT * FROM genomai.fatigue_state_versions ORDER BY updated_at DESC LIMIT 5;
-- Should show entries with fatigue_value incrementing
```

## Edge Cases
- First outcome for idea: fatigue starts at 1.0 (version 1)
- Subsequent outcomes: fatigue increments by 1.0
- No time decay applied (MVP simplification)

## Future Considerations
- Post-MVP: implement actual fatigue decay formula
- Post-MVP: consider CPA-based fatigue (bad outcomes increase fatigue more)
- Post-MVP: update playbook to reflect fatigue versioning as allowed
