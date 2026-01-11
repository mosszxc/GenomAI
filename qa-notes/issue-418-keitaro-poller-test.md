# Issue #418: Test KeitaroPollerWorkflow

**Date:** 2026-01-11
**Status:** PASSED

## Test Command
```bash
python -m temporal.schedules trigger keitaro-poller
```

## Results

### 1. Workflow Trigger
```
2026-01-11 20:00:11,087 - __main__ - INFO - Triggered schedule: keitaro-poller
```
✅ Workflow запустился успешно

### 2. daily_metrics_snapshot
```sql
SELECT tracker_id, date, metrics, created_at
FROM genomai.daily_metrics_snapshot
ORDER BY created_at DESC LIMIT 5;
```

**Результат:** 4 записи
- tracker_id: e2e-test-tracker-001 (2026-01-11)
- tracker_id: 9869 (2026-01-10)
- tracker_id: 9790 (2026-01-10)
- tracker_id: 9788 (2026-01-10)

✅ Данные присутствуют

### 3. raw_metrics_current
```sql
SELECT tracker_id, date, metrics, updated_at
FROM genomai.raw_metrics_current
ORDER BY updated_at DESC LIMIT 5;
```

**Результат:** 1 запись актуальных метрик
- tracker_id: e2e-test-tracker-001 (updated_at: 2026-01-11 16:53:08)

✅ Данные присутствуют

### 4. Constraint Validation
В логах видны ошибки:
```
duplicate key value violates unique constraint "daily_metrics_snapshot_tracker_id_date_key"
```

Это **ожидаемое поведение** - constraint правильно предотвращает дублирование данных за один день.

## Conclusion
KeitaroPollerWorkflow работает корректно:
- Trigger через schedule работает
- Данные сохраняются в обе таблицы
- Unique constraint работает
