# QA Notes: Issue #284 - Excessive decisions on single idea

## Problem
E2E test detected 1 idea with 8 decisions (expected max 3).

**Affected idea_id:** `86ce27f1-8f81-4e2c-95fd-916cae445928`

## Root Cause
1. No idempotency check in `make_decision()` — каждый вызов создавал новый decision
2. No UNIQUE constraint on `(idea_id, decision_epoch)` — БД разрешала дубликаты

## Fix Applied

### Code Changes
- `src/services/supabase.py`:
  - Added `get_existing_decision(idea_id, decision_epoch)` — проверка существующего решения
  - Added `get_decision_trace(decision_id)` — загрузка trace для existing decision

- `src/services/decision_engine.py`:
  - Added idempotency guard at start of `make_decision()`
  - If decision exists for (idea_id, epoch) → return cached result with `idempotent: True` flag
  - Added `CURRENT_DECISION_EPOCH` constant

### DB Migration (027)
- Deleted duplicate decisions (kept oldest for each idea_id+epoch)
- Added UNIQUE constraint `decisions_idea_epoch_unique`

## Test Results

### Duplicate cleanup verified
```sql
-- Before: 8 decisions for idea 86ce27f1...
-- After: 1 decision
SELECT COUNT(*) FROM genomai.decisions
WHERE idea_id = '86ce27f1-8f81-4e2c-95fd-916cae445928';
-- Result: 1
```

### UNIQUE constraint works
```sql
INSERT INTO genomai.decisions (id, idea_id, decision, decision_epoch)
VALUES (gen_random_uuid(), '86ce27f1-8f81-4e2c-95fd-916cae445928', 'approve', 1);
-- ERROR: duplicate key value violates unique constraint "decisions_idea_epoch_unique"
```

## Files Changed
- `decision-engine-service/src/services/decision_engine.py`
- `decision-engine-service/src/services/supabase.py`
- `infrastructure/migrations/027_decisions_unique_idea_epoch.sql`

## Deployment Notes
- Migration already applied to production DB
- Code requires deploy to Render
