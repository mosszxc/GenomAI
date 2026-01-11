# QA Notes: Issue #342 - RawMetricsObserved events not emitting

## Problem
`KeitaroPollerWorkflow` обновляет `raw_metrics_current`, но событие `RawMetricsObserved` не эмитится в `event_log`.

## Root Cause
В workflow отсутствовал вызов `emit_metrics_event` activity после:
- `upsert_raw_metrics` - обновление метрик
- `create_daily_snapshot` - создание snapshot

## Fix
Добавлены два блока эмиссии событий в `keitaro_polling.py`:

1. **RawMetricsObserved** (строки 165-182):
   - Вызывается после каждого успешного `upsert_raw_metrics`
   - Payload: `tracker_id`, `date`, `interval`

2. **DailyMetricsSnapshotCreated** (строки 202-219):
   - Вызывается после успешного `create_daily_snapshot` (когда `snapshot_result.created = True`)
   - Payload: `tracker_id`, `date`

## Design Decisions
- Event emission is best-effort (`except Exception: pass`)
- Не блокирует основной workflow при ошибках эмиссии
- Использует существующую activity `emit_metrics_event`

## Testing
- [x] Unit tests: 85 passed
- [x] CI checks: all passed
- [ ] E2E validation: post-deploy

## Files Changed
- `decision-engine-service/temporal/workflows/keitaro_polling.py` (+38 lines)
