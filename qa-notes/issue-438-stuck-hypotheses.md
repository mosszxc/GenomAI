# QA Notes: Issue #438 - 3 hypotheses stuck in pending delivery > 1h

## Summary
Data fix для 3 гипотез, застрявших в статусе `pending` более 1 часа.

## Root Cause
**E2E Test Buyer имеет невалидный telegram_id.**

| Field | Value |
|-------|-------|
| Buyer ID | `e2e00370-0000-0000-0000-000000000001` |
| Buyer Name | E2E Test Buyer |
| telegram_id | `999999999` (не существует в Telegram) |
| Error | `Bad Request: chat not found` |

При попытке доставки гипотез Telegram Bot API возвращает ошибку "chat not found", так как chat с ID `999999999` не существует.

## Affected Hypotheses

| ID | Status Before | Status After | Retry Count |
|----|---------------|--------------|-------------|
| `2e26033f-ffdc-4997-8e7e-38fde43453f3` | pending | failed | 2 |
| `a0ec6eaa-53d1-4c5b-b481-2f17f0265e82` | pending | failed | 2 |
| `1da6c5f1-8345-413f-8eae-bfa024888672` | pending | failed | 2 |

## Fix Applied
```sql
UPDATE genomai.hypotheses
SET status = 'failed'
WHERE id IN (
  '2e26033f-ffdc-4997-8e7e-38fde43453f3',
  'a0ec6eaa-53d1-4c5b-b481-2f17f0265e82',
  '1da6c5f1-8345-413f-8eae-bfa024888672'
);
```

## Verification
```
Production test: PASSED
  Command: GET /hypotheses?id=in.(...)&select=id,status,last_error
  Result: All 3 hypotheses now have status='failed'
```

## Notes
- Это data fix, не code change
- `retry_count: 2` означает что система уже пыталась доставить гипотезы дважды
- `last_error` сохранён для диагностики
- E2E Test Buyer используется для интеграционных тестов, его telegram_id намеренно невалидный
- Новые гипотезы для этого buyer также будут падать (expected behavior для тестового окружения)

## Acceptance Criteria
- [x] Все 3 гипотезы обработаны (status = failed)
- [x] Root cause задокументирован
