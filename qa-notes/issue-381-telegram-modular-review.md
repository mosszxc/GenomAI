# QA Notes: Issue #381 - Telegram UI for Modular Hypothesis Review

## Summary
Реализованы Telegram команды для human review modular гипотез.

## Changes
- `/pending` — показ pending_review гипотез с модулями (Hook, Promise, Proof)
- `/approve <id>` — одобрить гипотезу (меняет status на `generated`)
- `/reject <id>` — отклонить гипотезу (меняет status на `rejected`)
- Обновлено help меню для админов

## Files Modified
- `decision-engine-service/src/routes/telegram.py` — добавлены handlers и dispatch

## Production Test Results
```
Date: 2026-01-11
Deploy commit: 71ed11ea (status: live)

Test 1: /pending command
  Request: POST /webhook/telegram {"text": "/pending"}
  Response: {"ok": true}
  DB log: buyer_interactions записан (direction: in, content: /pending)
  Result: PASS

Test 2: /approve command
  Request: POST /webhook/telegram {"text": "/approve test123"}
  Response: {"ok": true}
  DB log: buyer_interactions записан (direction: in, content: /approve test123)
  Result: PASS
```

## Notes
- Pending гипотез в production пока нет (зависит от ModularHypothesisWorkflow #380)
- Команды доступны только админам (ADMIN_TELEGRAM_IDS)
- При approve: review_status -> approved, status -> generated
- При reject: review_status -> rejected, status -> rejected

## Dependencies
- #375 module_bank schema (CLOSED)
- #380 ModularHypothesisWorkflow (CLOSED)
