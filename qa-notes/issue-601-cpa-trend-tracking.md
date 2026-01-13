# Issue #601: CPA & Trend Tracking

## Что изменено

### Schema (migration 045_cpa_tracking.sql)
- `module_bank`: добавлены колонки `total_conversions` и generated `avg_cpa`
- Новая таблица `module_weekly_snapshots` для хранения еженедельных снимков метрик модулей
- Индекс `idx_module_bank_avg_cpa` для CPA-based selection
- Функция `genomai.get_module_trend(module_id, weeks)` для получения тренда

### Activities
- `module_learning.py`: обновлён для учёта conversions при обновлении метрик модулей
- Новый файл `module_snapshots.py` с activities:
  - `create_weekly_snapshots` - создание еженедельных снимков
  - `get_module_trend` - получение тренда для модуля
  - `get_trending_modules` - поиск модулей с улучшающимся/ухудшающимся трендом

### MaintenanceWorkflow
- Добавлен шаг `Step 10b` для создания weekly snapshots (запускается по понедельникам)
- Новые параметры: `run_weekly_snapshots`
- Новые поля результата: `module_snapshots_created`, `module_snapshots_updated`

### Trend calculation
- `win_rate_trend = (current - prev) / prev`
- `cpa_trend = (current - prev) / prev` (negative is better)
- `roi_trend = (current - prev) / prev`

## Acceptance Criteria
- [x] Каждый модуль имеет avg_cpa (generated column)
- [x] Можно получить trend за последние N недель через `get_module_trend`

## Test

```bash
make test
```
