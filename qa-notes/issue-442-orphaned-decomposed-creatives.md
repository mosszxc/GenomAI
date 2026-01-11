# QA Notes: Issue #442 - Orphaned decomposed_creatives

## Problem
E2E тест выявил 2 `decomposed_creatives` с `idea_id = null`:
- `dd6243b8-6e36-4275-961e-1a7b381d807e` (creative: c7818783)
- `c42b3004-31ae-4649-9861-53e6c262265d` (creative: e51f6bb7)

## Root Cause Analysis

| Creative | Decomposed | Status | Transcript | Events | Root Cause |
|----------|------------|--------|------------|--------|------------|
| e51f6bb7 | c42b3004 | `pending` | id=13 | TranscriptCreated, CreativeDecomposed | Workflow прервался после decomposition |
| c7818783 | dd6243b8 | `transcription_failed` | НЕТ | НЕТ | Anomaly: decomposed без transcript |

**Общая причина:** CreativePipelineWorkflow создаёт `decomposed_creative` ДО `idea` registration.
Если workflow прерывается между этими шагами — остаётся orphaned record.

## Data Fix Applied

### 1. Created Ideas
```sql
-- Idea 1 (for decomposed dd6243b8)
INSERT INTO genomai.ideas (id, canonical_hash, status)
VALUES ('d01916f8-a8e6-4a96-b48b-39907f0b289d',
        '6d3db98ddc484ec1bafaeb47b9cb325b328017fa35547b60a45fe9cf9997b968',
        'active');

-- Idea 2 (for decomposed c42b3004)
INSERT INTO genomai.ideas (id, canonical_hash, status)
VALUES ('33d6a2b1-ee63-4202-a4c2-f2603817a510',
        'f55bc05e311d3a31d33429e9a93f19ab69e13559b7284c90875b0a87917864f5',
        'active');
```

### 2. Linked decomposed_creatives
```sql
UPDATE genomai.decomposed_creatives
SET idea_id = 'd01916f8-a8e6-4a96-b48b-39907f0b289d'
WHERE id = 'dd6243b8-6e36-4275-961e-1a7b381d807e';

UPDATE genomai.decomposed_creatives
SET idea_id = '33d6a2b1-ee63-4202-a4c2-f2603817a510'
WHERE id = 'c42b3004-31ae-4649-9861-53e6c262265d';
```

## Production Test

**Query:**
```sql
SELECT id FROM genomai.decomposed_creatives WHERE idea_id IS NULL;
```

**Result:** `[]` (empty - no orphaned records)

**Status:** PASSED

## Recommendations

1. **Monitoring:** Добавить alert на orphaned decomposed_creatives:
   ```sql
   SELECT COUNT(*) FROM genomai.decomposed_creatives WHERE idea_id IS NULL;
   ```

2. **Code improvement (optional):** Рассмотреть атомарную транзакцию для decomposition + idea creation, но это сложно в Temporal workflow.

## Summary

- **Type:** Data fix (no code changes)
- **Records fixed:** 2 decomposed_creatives
- **Ideas created:** 2
- **Test:** PASSED
