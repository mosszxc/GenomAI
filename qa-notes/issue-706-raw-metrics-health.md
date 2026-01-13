# Issue #706: /health/metrics возвращает 404

## Что изменено

- `circuit_breaker.py`: Изменён `get_metrics_staleness()` — использует прямой запрос к таблице с `Accept-Profile: genomai` header

## Причина

- Таблица `raw_metrics_current` находится в схеме `genomai`
- PostgREST по умолчанию ищет в `public` схеме
- Для доступа к `genomai` нужен header `Accept-Profile: genomai`

## Файлы

- `decision-engine-service/temporal/circuit_breaker.py` — изменён `get_metrics_staleness()`

## Test

```bash
curl -sf localhost:10000/health/metrics | grep -q '"status"' && echo "OK: endpoint works" || echo "FAIL"
```
