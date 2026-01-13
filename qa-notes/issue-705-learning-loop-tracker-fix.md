# Issue #705: Learning Loop tracker_id fix

## Что изменено

Изменён Keitaro polling для использования `campaign_id` вместо `sub_id_1`:

- `get_all_trackers()` — dimension `sub_id_1` → `campaign_id`
- `get_tracker_metrics()` — filter `sub_id_1` → `campaign_id`
- `get_batch_metrics()` — dimension и lookup по `campaign_id`

## Причина

- `creatives.tracker_id` = `campaign_id` из Keitaro (10228, 10230)
- Старый polling использовал `sub_id_1` (9788, 9790, 9869)
- Новые кампании не имеют настроенного `sub_id_1`, поэтому связь терялась

## Файлы

- `decision-engine-service/temporal/activities/keitaro.py`
- `docs/layer-4-implementation-planning/KEITARO_API_DATA_CLASSIFICATION.md`

## Test

```bash
curl -s -X POST "https://genomai.onrender.com/api/schedules/keitaro-poller-schedule/trigger" -H "X-API-Key: ccb3800e2a7e146c0238daeb6af32f85" && echo " OK: Polling triggered"
```

## Верификация после deploy

1. Триггернуть Keitaro poller
2. Проверить новые snapshots:
```sql
SELECT tracker_id, date FROM genomai.daily_metrics_snapshot ORDER BY created_at DESC LIMIT 5;
```
Должны появиться tracker_id = 10228, 10230

3. Проверить outcomes:
```sql
SELECT COUNT(*) FROM genomai.outcome_aggregates;
```
Должно быть > 0 после следующего цикла polling
