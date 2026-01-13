# Issue #538: Overly broad exception handling swallows errors

## Что изменено

- Заменен bare `except Exception: pass` на специфичную обработку исключений в `check_active_onboarding()`
- Добавлен импорт `RPCError` и `RPCStatusCode` из `temporalio.service`
- `RPCError` с `NOT_FOUND` статусом игнорируется (ожидаемое поведение - workflow не существует)
- Другие `RPCError` логируются как warning
- Остальные исключения логируются как error

## Файлы

- `decision-engine-service/src/routes/telegram.py:334-343`

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI && python3 -m ruff check decision-engine-service/src/routes/telegram.py && echo "OK: no lint errors"
```
