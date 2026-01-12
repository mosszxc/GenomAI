# Issue #472: Stuck Creatives — отсутствует состояние 'failed'

## Что изменено

### Миграция БД
- Добавлена колонка `error` TEXT в `creatives` для хранения ошибок
- Добавлена колонка `retry_count` INT DEFAULT 0 для подсчёта попыток
- Добавлена колонка `failed_at` TIMESTAMPTZ для времени ошибки
- Добавлен индекс `idx_creatives_failed_status` для поиска failed creatives

### Activity: update_creative_status
- Принимает опциональный параметр `error`
- При `status='failed'` записывает `error`, `failed_at` в БД
- Error обрезается до 1000 символов

### Workflow: CreativePipelineWorkflow
- При ошибке вызывает `update_creative_status(creative_id, "failed", error)`
- Эмитирует event `CreativeFailed` с информацией об ошибке
- Сохраняет `failed_at_stage` — на каком этапе произошла ошибка

### Activities: maintenance.py
- `find_failed_creatives_for_retry` — находит failed creatives для retry
- `reset_creative_for_retry` — сбрасывает status='registered', инкрементирует retry_count
- `abandon_failed_creative` — помечает как abandoned после max retries

### Workflow: MaintenanceWorkflow
- Добавлен Step 11: Retry failed creatives
- Параметры: `run_failed_retry`, `failed_creative_max_retries`, `failed_creative_min_age_minutes`
- Результаты: `failed_creatives_retried`, `failed_creatives_abandoned`

## State Machine

```
registered -> processing -> processed (happy path)
          \-> failed (error)
                 |-> registered (retry, retry_count++)
                 \-> abandoned (max retries exceeded)
```

## Test

```bash
cd decision-engine-service && python3 -m pytest tests/unit/test_creative_failed_status.py -v --tb=short
```

## Ручная проверка

1. Применить миграцию:
```sql
ALTER TABLE genomai.creatives ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE genomai.creatives ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;
ALTER TABLE genomai.creatives ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;
```

2. Проверить что failed creatives сохраняют error:
```sql
SELECT id, status, error, retry_count, failed_at
FROM genomai.creatives
WHERE status = 'failed'
ORDER BY failed_at DESC
LIMIT 5;
```

## Риски

- Нет — добавлены только новые колонки и логика
- Backward compatible — существующие creatives не затронуты
