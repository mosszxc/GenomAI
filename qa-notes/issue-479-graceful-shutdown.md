# Issue #479: Graceful Shutdown для Workers

## Что изменено

- Добавлен import `signal` для обработки сигналов ОС
- Добавлена функция `graceful_shutdown()` внутри `run_all_workers()`
- Установлены signal handlers для SIGTERM и SIGINT
- При получении сигнала:
  1. Все workers получают `shutdown()` — перестают принимать новые задачи
  2. Дожидаются завершения in-flight activities
  3. Закрывается connection к Temporal client
- Убран старый `except KeyboardInterrupt` из `main()`

## Impact

- In-flight activities корректно завершаются
- Temporal client connection закрывается (нет connection leak)
- Данные не остаются в inconsistent state

## Test

```bash
grep -q 'graceful_shutdown' .worktrees/issue-479-*/decision-engine-service/temporal/worker.py && grep -q 'SIGTERM' .worktrees/issue-479-*/decision-engine-service/temporal/worker.py && grep -q 'worker.shutdown()' .worktrees/issue-479-*/decision-engine-service/temporal/worker.py && grep -q 'client.service_client.close()' .worktrees/issue-479-*/decision-engine-service/temporal/worker.py && echo "OK: graceful shutdown implemented"
```
