# QA Notes: Issue #291 - Historical Import Fixes

## Summary
Исправление багов в HistoricalImportWorkflow и успешное тестирование на баере TU.

## Test Environment
- **Buyer**: TU (`d7024747-c1c4-4844-ab60-513351cc38cd`)
- **Keitaro Source**: `tu`
- **Date Range**: последние 30 дней (по дате создания кампании)

## Bugs Fixed

### 1. Keitaro API Filter Field
- **Problem**: Использовался фильтр `source` который не существует в Keitaro API
- **Fix**: Изменено на GET /campaigns + фильтрация по имени кампании
- **File**: `temporal/activities/keitaro.py:get_campaigns_by_source`

### 2. Keitaro API Date Format
- **Problem**: `last_30_days` не поддерживается API
- **Fix**: Используются явные даты ISO формата или фильтрация по `created_at`
- **File**: `temporal/activities/keitaro.py`

### 3. Status Constraint Violation
- **Problem**: `CHECK constraint` на `historical_import_queue.status` не включает `pending`
- **Fix**: Изменено на `pending_video` (валидный статус)
- **File**: `temporal/activities/buyer.py:queue_historical_import`

### 4. Duplicate Campaign Conflict
- **Problem**: `409 Conflict` при повторной вставке campaign_id (UNIQUE constraint)
- **Fix**: Добавлен upsert через `on_conflict=campaign_id` + `resolution=merge-duplicates`
- **File**: `temporal/activities/buyer.py:queue_historical_import`

### 5. Continue-as-New Infinite Loop
- **Problem**: Workflow обрабатывал 50 кампаний и перезапускался с теми же параметрами
- **Fix**: Увеличен `MAX_CAMPAIGNS_PER_EXECUTION` с 50 до 500
- **File**: `temporal/workflows/historical_import.py`

## Test Results

### Local Testing
```bash
# Тест upsert
python -m scripts.test_queue_historical
# Result: FIRST INSERT SUCCESS, UPSERT SUCCESS - Same ID
```

### Production Testing
```bash
# Запуск workflow
curl -X POST "https://genomai.onrender.com/api/historical/start-import" \
  -H "Content-Type: application/json" \
  -d '{"buyer_id": "d7024747-c1c4-4844-ab60-513351cc38cd", "keitaro_source": "tu"}'
# Result: {"success": true, "workflow_id": "historical-import-d7024747-..."}
```

### Database Verification
```sql
SELECT COUNT(*), status FROM genomai.historical_import_queue
WHERE buyer_id = 'd7024747-c1c4-4844-ab60-513351cc38cd' GROUP BY status;
-- Result: 383 | pending_video
```

### Workflow Status
```
Status: COMPLETED
```

## Files Changed
| File | Changes |
|------|---------|
| `temporal/activities/keitaro.py` | Rewritten get_campaigns_by_source to fetch all campaigns and filter locally |
| `temporal/activities/buyer.py` | Added upsert headers, changed status to pending_video |
| `temporal/workflows/historical_import.py` | MAX_CAMPAIGNS_PER_EXECUTION: 50 → 500 |
| `src/routes/historical.py` | Fixed status filter in /queue endpoint |

## Commits
- e3539ae fix: increase MAX_CAMPAIGNS_PER_EXECUTION to 500
- bf8490e fix: use upsert for historical_import_queue to handle duplicates
- 0c6f833 fix: use valid status 'pending_video' for historical import queue
- b173410 fix: filter campaigns by creation date (last 30 days)
- 147451f fix: use explicit dates instead of last_30_days in Keitaro
- ecc9ad5 fix: use CONTAINS operator for string filter in Keitaro
- 4c824e5 fix: use sub_id_10 instead of source for buyer filter in Keitaro
- 49dc5d5 feat: add POST /api/historical/start-import endpoint

## Next Steps
1. Баер TU может теперь отправлять видео через Telegram бота
2. После отправки видео запустится CreativePipelineWorkflow
3. Рекомендуется добавить proper pagination в continue_as_new (отложено)
