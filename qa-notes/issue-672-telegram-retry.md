# Issue #672: Retry-логика для send_hypothesis_to_telegram

## Что изменено
- Добавлена retry-логика в `send_hypothesis_to_telegram` activity
- 3 попытки с exponential backoff (1s, 2s, 4s)
- Обработка rate limit (429) и server errors (5xx)
- Обработка таймаутов и HTTP ошибок

## Файлы
- `decision-engine-service/temporal/activities/telegram.py:48-159`

## Детали реализации
- `TELEGRAM_MAX_RETRIES = 3` - максимум попыток
- `TELEGRAM_BASE_DELAY = 1.0` - начальная задержка
- `TELEGRAM_MAX_DELAY = 10.0` - максимальная задержка
- `_should_retry()` - определяет retriable ошибки (429, 5xx)
- `_get_retry_delay()` - exponential backoff с Retry-After

## Test
```bash
grep -q "TELEGRAM_MAX_RETRIES = 3" decision-engine-service/temporal/activities/telegram.py && grep -q "_should_retry" decision-engine-service/temporal/activities/telegram.py && grep -q "for attempt in range(TELEGRAM_MAX_RETRIES)" decision-engine-service/temporal/activities/telegram.py && echo "OK: retry logic present"
```
