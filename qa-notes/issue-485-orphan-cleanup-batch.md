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
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-485-arch-medium-orphan-cleanup-обрабатывает-/decision-engine-service && python -c "
from temporal.activities.hygiene_cleanup import cleanup_orphan_raw_metrics
import inspect
source = inspect.getsource(cleanup_orphan_raw_metrics)

# Check batch size increased
assert 'batch_size = 500' in source, 'batch_size should be 500'

# Check error logging
assert 'activity.logger.warning' in source, 'Should log warnings'
assert 'Failed to delete orphan' in source, 'Should have failure message'

# Check orphan count metric
assert 'total_orphans' in source, 'Should track total orphans'
assert 'remaining=' in source, 'Should log remaining count'

print('OK: batch=500, error_logging=yes, metrics=yes')
"
```
