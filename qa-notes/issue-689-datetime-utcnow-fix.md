# Issue #689: Fix datetime.utcnow() in tracing.py

## Что изменено

Исправлено использование `datetime.utcnow()` в `temporal/tracing.py:41`.

## Проблема

`_add_timestamp()` processor в structlog использовал `datetime.datetime.utcnow()`,
что запрещено в Temporal workflow sandbox (non-deterministic operation).

Ошибка:
```
Cannot access datetime.datetime.utcnow.__call__ from inside a workflow
```

## Решение

Добавлена проверка контекста:
- В workflow: используем `workflow.now()` (deterministic)
- Вне workflow: используем `datetime.now(timezone.utc)`

## Test

```bash
python3 -m py_compile decision-engine-service/temporal/tracing.py && echo "OK: syntax valid"
```
