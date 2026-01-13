# Issue #602: Dashboard Meta API (HOT/COLD/GAPS)

## Что изменено

- Создан `src/routes/dashboard.py` с endpoint `GET /api/dashboard/meta`
- Создан `src/services/dashboard_service.py` с логикой HOT/COLD/GAPS классификации
- Зарегистрирован роутер в `main.py`
- Добавлены unit тесты в `tests/unit/test_dashboard.py`

## Endpoint

`GET /api/dashboard/meta?geo=DE&vertical=POT`

## Логика классификации

- **HOT**: `win_rate >= 0.35` и `sample_size >= 10`
- **COLD**: `win_rate <= 0.15` и `sample_size >= 10`
- **GAPS**: `sample_size < 5`

## Response Format

```json
{
  "success": true,
  "data": {
    "geo": "DE",
    "vertical": "POT",
    "week": 2,
    "hot": [...],
    "cold": [...],
    "gaps": [...],
    "summary": {
      "total_components": 0,
      "hot_count": 0,
      "cold_count": 0,
      "gaps_count": 0
    }
  }
}
```

## Test

```bash
curl -sf localhost:10000/api/dashboard/meta -H "Authorization: Bearer $API_KEY" | jq -e '.success == true'
```
