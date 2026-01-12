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
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-485-arch-medium-orphan-cleanup-обрабатывает-/decision-engine-service && grep -q 'batch_size = 500' temporal/activities/hygiene_cleanup.py && grep -q 'Failed to delete orphan' temporal/activities/hygiene_cleanup.py && grep -q 'total_orphans' temporal/activities/hygiene_cleanup.py && echo 'OK: batch=500, error_logging=yes, metrics=yes'
```
