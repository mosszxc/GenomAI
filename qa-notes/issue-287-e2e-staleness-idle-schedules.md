# Issue #287: E2E тест - улучшить логику проверки staleness для idle schedules

## Проблема

E2E тест показывал ERROR для schedules которые работают корректно, но не имеют данных для обработки (idle state). Например, `keitaro-poller` с staleness 14h показывал ERROR, хотя schedule работает - просто нет новых metrics для poll.

## Причина

Оригинальная логика проверяла только staleness по времени, не учитывая:
1. Есть ли вообще данные для обработки
2. Что schedule может быть "idle" - работает, но нет входных данных

## Решение

Добавлены две новые секции в `.claude/commands/e2e.md`:

### 5.0 Schedule Status via Event Log

SQL запрос проверяет последний запуск каждого schedule через `event_log`:

| Schedule | Event Type | Threshold OK | Threshold WARN |
|----------|------------|--------------|----------------|
| keitaro-poller | RawMetricsObserved | 15 min | 30 min |
| metrics-processor | OutcomeAggregated | 45 min | 90 min |
| learning-loop | learning.applied | 90 min | 3 hours |
| maintenance | MaintenanceCompleted | 7 hours | 12 hours |
| daily-recommendations | RecommendationGenerated | 25 hours | 48 hours |

### 5.0.1 Idle Schedule Detection

Дополнительный SQL запрос проверяет наличие pending данных:

```sql
SELECT
  (SELECT COUNT(*) FROM genomai.outcome_aggregates WHERE learning_applied = false) as pending_outcomes,
  (SELECT COUNT(*) FROM genomai.daily_metrics_snapshot WHERE date = current_date) as today_snapshots;
```

**Интерпретация:**
- `STALE` + `pending_outcomes > 0` = ПРОБЛЕМА (есть данные, но не обрабатываются)
- `STALE` + `pending_outcomes = 0` = OK/IDLE (нет данных для обработки)

## Тестирование

```sql
-- Результат теста:
schedule             | staleness_status | pending_outcomes | interpretation
---------------------|------------------|------------------|---------------
daily-recommendations| OK               | 0                | Working
maintenance          | OK               | 0                | Working
keitaro-poller       | STALE            | 0                | IDLE (OK)
learning-loop        | STALE            | 0                | IDLE (OK)
metrics-processor    | STALE            | 0                | IDLE (OK)
```

## Файлы изменены

- `.claude/commands/e2e.md` - добавлены секции 5.0 и 5.0.1

## Связанные issues

- #285: Temporal CLI не подключается к Temporal Cloud локально
- #286: Отсутствует API endpoint для управления Temporal schedules
