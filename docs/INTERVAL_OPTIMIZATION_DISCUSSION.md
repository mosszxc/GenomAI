# Обсуждение оптимизации интервалов Temporal Workflows

**Дата:** 2026-01-11

## Контекст

Пересмотр всех интервалов в системе. Staleness Detector каждые 6 часов — слишком часто для метрик которые меняются днями.

## Текущие интервалы

| Workflow | Интервал | Проблема |
|----------|----------|----------|
| keitaro-poller | 10 мин | Возможно часто |
| metrics-processor | 30 мин | OK |
| learning-loop | 1 час | Double-trigger! |
| daily-recommendations | 09:00 UTC | OK |
| maintenance | 6 часов | Staleness избыточно |

## Выявленные проблемы

### 1. Learning Loop Double-Trigger
- Schedule: каждый час (24 раза/день)
- Child workflow из MetricsProcessor: ~48 раз/день (когда outcomes > 0)
- Итого: до 72 запусков/день

### 2. Staleness Detection
- Метрики: 7d MA vs 30d MA, days_since_new_component (порог 14 дней)
- Меняются днями, не часами
- 4 проверки/день избыточны

## Обсуждение: Learning Loop

**Варианты:**
- A: Удалить schedule (только child) — ~48 запусков/день
- B: Оставить как есть — ~72 запусков/день
- C: Schedule как страховка (реже) — баланс

**Решение в процессе:**
- Концепция C понравилась
- 54 запуска всё равно много
- Обсуждаем: schedule раз в день (23:00 UTC) как страховка или убрать + alerting

## Следующие шаги

1. Решить по Learning Loop (schedule раз в день vs убрать + alerting)
2. Обсудить Keitaro Poller (10 → 15 мин?)
3. Обсудить Maintenance/Staleness (разделить на daily)
4. Обсудить Metrics Processor (batch_limit 50 → 100?)

## Файлы для изменения

- `decision-engine-service/temporal/schedules.py` — основные изменения
- `docs/TEMPORAL_WORKFLOWS.md` — документация

## План (черновик)

Полный план в: `/Users/mosszxc/.claude/plans/cozy-riding-fountain.md`
