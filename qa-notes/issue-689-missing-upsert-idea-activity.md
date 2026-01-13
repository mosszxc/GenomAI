# Issue #689: Missing upsert_idea activity in worker

## Что изменено

Добавлена регистрация `upsert_idea` activity в worker.py:
- `temporal/worker.py:62` - импорт activity из temporal.activities.supabase
- `temporal/worker.py:279` - регистрация в run_worker()
- `temporal/worker.py:353` - регистрация в run_all_workers() creative_worker

## Проблема

`HistoricalVideoHandlerWorkflow` застревал в статусе `processing` потому что:
1. Workflow запускает child workflow `CreativePipelineWorkflow`
2. `CreativePipelineWorkflow` вызывает activity `upsert_idea` (строка 308)
3. `upsert_idea` **НЕ была зарегистрирована** в worker.py
4. Temporal ставит task в очередь, но worker не может его обработать
5. Workflow ждёт до timeout → статус остаётся `processing`

## Решение

Добавлена регистрация `upsert_idea` activity во всех местах, где регистрируется creative_worker:
- `run_worker()` - для standalone creative pipeline worker
- `run_all_workers()` - для объединённого worker

## Затронутые файлы

- `decision-engine-service/temporal/worker.py`

## Test

```bash
grep -q "upsert_idea," decision-engine-service/temporal/worker.py && python3 -m py_compile decision-engine-service/temporal/worker.py && echo "OK: upsert_idea registered"
```
