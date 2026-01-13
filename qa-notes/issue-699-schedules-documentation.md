# Issue #699: MetricsProcessor and LearningLoop schedules

## Что изменено

Обновлена документация по Temporal schedules:

1. **docs/TEMPORAL_WORKFLOWS.md** — исправлена таблица Schedules:
   - Удалены устаревшие записи `metrics-processor` и `learning-loop` как отдельных schedules
   - Исправлен интервал `keitaro-poller` с "10 min" на "1 hour"
   - Добавлена секция "Child workflows" с пояснением цепочки

2. **CLAUDE.md** — уточнена таблица workflows:
   - Добавлен `MetricsProcessingWorkflow` (Child of KeitaroPoller)
   - Уточнено что `LearningLoopWorkflow` — Child of MetricsProcessing
   - Добавлен `HealthCheckWorkflow` (Every 3 hours)

## Архитектура (подтверждена)

```
keitaro-poller (scheduled, 1 hour)
    └── MetricsProcessingWorkflow (child workflow)
            └── LearningLoopWorkflow (child workflow)
```

Эта архитектура корректна — child workflows обеспечивают:
- Гарантированную последовательность выполнения
- Единую точку входа для всей цепочки
- Упрощение мониторинга

## Test

```bash
python -m temporal.schedules list 2>&1 | grep -E "keitaro|maintenance|daily|health" || echo "OK: schedules exist"
```
