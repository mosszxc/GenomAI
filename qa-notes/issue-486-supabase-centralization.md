# Issue #486: Centralized Supabase Credentials

## Что изменено

- Создан централизованный `SupabaseClient` в `src/core/supabase.py`
- Убрано дублирование `_get_credentials()` из ~25 файлов
- Мигрированы все сервисы, activities и routes на `get_supabase()`
- Добавлены unit тесты для нового клиента

## Затронутые файлы

### Новые файлы
- `decision-engine-service/src/core/supabase.py` - централизованный клиент
- `decision-engine-service/tests/unit/test_supabase_client.py` - unit тесты

### Мигрированные сервисы (~10 файлов)
- `src/services/avatar_service.py`
- `src/services/genome_heatmap.py`
- `src/services/what_if_simulator.py`
- `src/services/drift_detection.py`
- `src/services/staleness_detector.py`
- `src/services/feature_correlation.py`
- `src/services/correlation_discovery.py`
- `src/services/external_inspiration.py`
- `src/services/cross_transfer.py`
- `src/services/module_selector.py`

### Мигрированные activities (~15 файлов)
- `temporal/activities/supabase.py`
- `temporal/activities/maintenance.py`
- `temporal/activities/hygiene_cleanup.py`
- `temporal/activities/hygiene_health.py`
- `temporal/activities/recommendation.py`
- `temporal/activities/modular_generation.py`
- `temporal/activities/module_extraction.py`
- `temporal/activities/telegram.py`
- `temporal/activities/buyer.py`
- `temporal/activities/transcription.py`
- `temporal/activities/hypothesis_generation.py`
- `temporal/activities/premise_extraction.py`
- `temporal/activities/knowledge_db.py`
- `temporal/activities/learning.py`
- `temporal/activities/metrics.py`
- `temporal/activities/module_learning.py`

### Мигрированные routes (~4 файла)
- `src/routes/telegram.py` (~16 мест)
- `src/routes/premise.py`
- `src/routes/historical.py`
- `src/routes/knowledge.py`

## Паттерн использования

```python
# До
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    ...
}

# После
from src.core.supabase import get_supabase

sb = get_supabase()
headers = sb.get_headers()  # или sb.get_headers(for_write=True)
url = f"{sb.rest_url}/table_name"
```

## Test

```bash
make test && echo "OK"
```
