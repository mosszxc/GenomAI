# Issue #578: Non-idempotent retry в hygiene_cleanup

## Что изменено

- `retry_failed_hypotheses()` теперь идемпотентна
- Conditional update на `retry_count` перед отправкой Telegram
- При Temporal retry: claim fails → Telegram skip → no duplicates
- `retry_count` использует абсолютное значение (не increment)

## Механизм идемпотентности

```
1. Вычисляем target_retry_count = current + 1
2. PATCH hypotheses WHERE id=X AND retry_count=current → SET retry_count=target
3. Если 0 rows affected → это retry, пропускаем Telegram
4. Если 1 row affected → отправляем Telegram
5. Обновляем status/last_error (retry_count уже установлен)
```

## Test

```bash
grep -q "retry_count=eq" decision-engine-service/temporal/activities/hygiene_cleanup.py && grep -q "claimed_rows" decision-engine-service/temporal/activities/hygiene_cleanup.py && grep -q "target_retry_count" decision-engine-service/temporal/activities/hygiene_cleanup.py && echo "OK: idempotency pattern found"
```
