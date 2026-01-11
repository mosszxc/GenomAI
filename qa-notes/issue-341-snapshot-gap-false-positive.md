# Issue #341: E2E Warning - Daily Metrics Snapshot Gap

## Status: Works As Designed (False Positive)

## Investigation Summary

### Problem Statement
E2E тест Phase 2C.3 показал что `daily_metrics_snapshot` последний раз создан за 2026-01-10, а сегодня 2026-01-11.

### Root Cause Analysis

**Это не баг — система работает по дизайну.**

KeitaroPollerWorkflow настроен с `interval="yesterday"`:
```python
# temporal/schedules.py:59
"args": [KeitaroPollerInput(interval="yesterday", create_snapshots=True)]
```

Логика:
1. Keitaro Poller запускается каждые 10 минут
2. Получает метрики за **вчерашний** день (`interval="yesterday"`)
3. Создаёт snapshot с датой **вчерашнего** дня
4. Метрики за текущий день не полные — snapshot создастся завтра

### DB Verification

```sql
SELECT
  last_snapshot_date,
  today,
  days_since_last
FROM genomai.daily_metrics_snapshot;

-- Result:
-- last_snapshot_date: 2026-01-10
-- today: 2026-01-11
-- days_since_last: 1
```

`days_since_last = 1` — это **нормальное состояние** для системы.

### E2E Criteria Check

Phase 2C.3 критерий: `days_since_last <= 1`
- Текущее значение: 1
- Статус: **PASS**

## Resolution

1. Добавлено пояснение в `.claude/commands/e2e.md` Phase 2C.3
2. Issue закрыт как "works as designed"

## Files Changed

- `.claude/commands/e2e.md` — добавлена Note про interval="yesterday"

## Lessons Learned

- Snapshot за текущий день не ожидается — это by design
- `days_since_last = 1` — нормальное состояние
- E2E критерий `<= 1` корректен, WARNING появляется только при `> 1`
