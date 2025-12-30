# QA Notes: Issue #189 - Decision Values Lowercase Bug

## Summary
Decision values were saved as `approve` instead of `APPROVE`, breaking downstream validation.

## Root Cause
`decision_engine.py:94` had explicit `.lower()` call:
```python
'decision': decision_type.lower(),  # BUG
```

## Fix Applied
1. Changed to `.upper()` in `decision_engine.py`
2. Applied migration `fix_decision_case_to_uppercase`:
   - Dropped old constraint (allowed lowercase)
   - Updated 3 existing records to uppercase
   - Added new constraint requiring uppercase

## Affected Records
| ID | Before | After |
|----|--------|-------|
| d7336585-... | approve | APPROVE |
| c8581539-... | approve | APPROVE |
| 75bd6f82-... | approve | APPROVE |

## Gotchas
- **CHECK constraint existed** requiring lowercase values - had to migrate constraint too
- Always check constraints before assuming data format issues are code-only

## Test Verification
- Unit tests: 73 passed
- DB query confirmed all decisions now uppercase
- New constraint: `CHECK (decision IN ('APPROVE', 'REJECT', 'DEFER'))`

## Files Changed
- `decision-engine-service/src/services/decision_engine.py`
- Migration: `fix_decision_case_to_uppercase`
