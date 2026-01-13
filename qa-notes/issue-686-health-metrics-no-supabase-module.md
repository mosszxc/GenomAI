# Issue #686: /health/metrics returns 'No module named supabase' error

## Что изменено

- Заменён `supabase` Python SDK на httpx + REST API в `temporal/circuit_breaker.py`
- Функции `get_circuit_state()`, `save_circuit_state()`, `get_metrics_staleness()` теперь используют httpx
- Удалена зависимость от пакета `supabase`, который не был установлен в production

## Причина бага

Модуль `circuit_breaker.py` использовал `from supabase import create_client`, но пакет `supabase` не был добавлен в `pyproject.toml`. Остальные части приложения используют httpx + REST API напрямую.

## Test

```bash
curl -sf localhost:10000/health/metrics | jq -e '.status' && echo "OK: endpoint works"
```
