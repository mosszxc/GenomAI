# Issue #560: Unhandled child workflow error types в maintenance

## Что изменено

- Удалена хрупкая проверка строк (`"already started" in str(e)`) в обработке ошибок child workflow
- Добавлена явная обработка `asyncio.CancelledError` с re-raise для корректной отмены
- Изменено логирование: `workflow.logger.exception()` для неожиданных ошибок (включает traceback)
- `ChildWorkflowError` теперь всегда увеличивает счётчик неудач и логируется как warning

## Test

```bash
grep -n "asyncio.CancelledError" decision-engine-service/temporal/workflows/maintenance.py && grep -n "workflow.logger.exception" decision-engine-service/temporal/workflows/maintenance.py && echo "OK: error handling improved"
```
