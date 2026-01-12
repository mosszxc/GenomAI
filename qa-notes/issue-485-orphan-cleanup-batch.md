# Issue #485 - Orphan cleanup batch size

## Что изменено

- Увеличен batch size с 50 до 500 записей за раз
- Добавлено логирование ошибок удаления (было silent ignore)
- Добавлена метрика общего количества orphans в логах
- Логируется: deleted, failed, remaining

## Файлы

- `temporal/activities/hygiene_cleanup.py:176-212`

## Test

```bash
grep -q "list(orphan_trackers)\[:500\]" .worktrees/issue-485-*/decision-engine-service/temporal/activities/hygiene_cleanup.py && grep -q "Failed to delete orphan" .worktrees/issue-485-*/decision-engine-service/temporal/activities/hygiene_cleanup.py && echo "OK: batch=500, error_logging=yes"
```
