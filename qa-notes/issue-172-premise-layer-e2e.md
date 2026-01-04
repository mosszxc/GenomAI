# QA Notes: Issue #172 - E2E Premise Layer Validation

**Date:** 2026-01-04
**Issue:** [#172](https://github.com/mosszxc/GenomAI/issues/172)
**Status:** Completed with fix

---

## Test Results

### Validation Checklist

| Check | Status | Details |
|-------|--------|---------|
| premises table has seed data | ✅ PASS | 13 premises (11 active, 2 emerging) |
| /premise/select returns premise | ✅ PASS | Returns "Tibetan Monks Secret" (exploitation mode) |
| /premise/active returns list | ✅ PASS | Returns 5 active premises |
| /premise/top returns winners | ℹ️ EMPTY | No premise_learnings with sample_size >= 10 yet |
| hypothesis.premise_id populated | ✅ PASS | 3/3 hypotheses have premise_id (100%) |
| premise_learnings updated after outcome | ⚠️ BUG FIXED | See below |

---

## Bug Found & Fixed

### Problem

`get_hypothesis_for_creative()` in `premise_learning.py` only looked up hypothesis via `creatives.hypothesis_id` direct link.

Many creatives have `hypothesis_id = null` but have `idea_id` set, with hypothesis linked via `hypotheses.idea_id`.

**Result:** Learning Loop processed outcomes but `premise_updates = 0` with error:
```
"No hypothesis found for creative cf85839f-..."
```

### Fix

Added fallback lookup path in `premise_learning.py`:
1. `creatives.hypothesis_id` → `hypotheses.id` (original)
2. `creatives.idea_id` → `hypotheses.idea_id` (new fallback)

**Commit:** `c616594` on branch `vk/cea3-172-issue`

---

## Test Data Created

| Entity | ID | Purpose |
|--------|-----|---------|
| Test outcome | `15dfa1f5-51fa-47d7-9cac-3a87d05f429c` | E2E test |

**Cleanup:** Delete test outcome after merge:
```sql
DELETE FROM genomai.outcome_aggregates
WHERE id = '15dfa1f5-51fa-47d7-9cac-3a87d05f429c';
```

---

## API Endpoints Tested

### POST /premise/select
```json
Request: {"idea_id": "00000000-0000-0000-0000-000000000001"}
Response: {
  "premise_id": "f03746aa-c5fb-4bc6-b996-6fcbbebcc3c1",
  "premise_type": "secret",
  "name": "Tibetan Monks Secret",
  "is_new": false,
  "selection_reason": "exploitation"
}
```

### GET /premise/active?limit=5
```json
Response: {"premises": [...5 items...], "count": 5}
```

### GET /premise/top
```json
Response: {"premises": [], "count": 0}
```
*Expected: Empty until premise_learnings has data with sample_size >= 10*

---

## Premises in Database

| Name | Type | Status | Source |
|------|------|--------|--------|
| Tibetan Monks Secret | secret | active | - |
| Suppressed Stanford Study | breakthrough | active | - |
| Hollywood Elite Method | discovery | active | - |
| Метод лимонной косточки | method | active | manual |
| Метод гуавы | method | active | manual |
| Домашний метод | method | active | manual |
| Техника монахов | secret | active | manual |
| Признание врача | confession | active | manual |
| Один ингредиент | ingredient | active | manual |
| Скрытая причина | mechanism | active | manual |
| Случайное открытие ученого | discovery | active | manual |
| Открытие Сибирских Исследователей | breakthrough | emerging | llm_generated |
| Секрет утреннего ритуала | transformation | emerging | llm_generated |

---

## Post-Merge Verification

After merging to main and deploy:

1. Reset test outcome:
```sql
UPDATE genomai.outcome_aggregates
SET learning_applied = false
WHERE id = '15dfa1f5-51fa-47d7-9cac-3a87d05f429c';
```

2. Trigger Learning Loop:
```bash
curl -X POST "https://genomai.onrender.com/learning/process" \
  -H "Authorization: Bearer $API_KEY"
```

3. Verify premise_updates > 0:
```json
{"premise_updates": 1}  // Expected
```

4. Check premise_learnings:
```sql
SELECT * FROM genomai.premise_learnings
WHERE premise_id = 'f65afe97-2afc-4888-a1d8-be4b6cb1aa7e';
```

---

## Edge Cases

1. **Creative without hypothesis_id or idea_id** → Returns `None`, no error
2. **Hypothesis without premise_id** → Returns early, no update
3. **Multiple hypotheses for same idea** → Uses first one (LIMIT 1)

---

## Related Issues

- #166: Premise Layer Schema
- #167: Premise Learning Integration
- #168: Premise Selector
- #169: Premise API
