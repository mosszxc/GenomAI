# Issue #474: Keitaro Poller Circuit Breaker

## Что изменено

### Добавлен Circuit Breaker для Keitaro API
- Новый модуль `temporal/circuit_breaker.py` с паттерном Circuit Breaker
- Состояния: CLOSED (нормальная работа) → OPEN (после 3 failures) → HALF_OPEN (recovery)
- State хранится в Supabase `config` таблице для persistence между restarts

### Graceful Degradation в KeitaroPollerWorkflow
- Workflow проверяет circuit breaker перед API вызовами
- При OPEN circuit возвращает degraded result без API вызовов
- Записывает success/failure для обновления состояния CB
- НЕ запускает downstream workflows (MetricsProcessingWorkflow) в degraded mode

### Health Check Endpoint
- Новый endpoint `/health/metrics` для мониторинга staleness
- Возвращает: staleness_minutes, is_stale, circuit_breaker state
- status: "healthy" | "degraded" | "error"

### Изменённые файлы
- `temporal/circuit_breaker.py` (new)
- `temporal/workflows/keitaro_polling.py` (modified)
- `temporal/worker.py` (added activities)
- `main.py` (added health endpoint)
- `tests/unit/test_circuit_breaker.py` (new)

## Конфигурация

```python
FAILURE_THRESHOLD = 3      # Failures before opening circuit
RECOVERY_TIMEOUT_MINUTES = 5  # Time before half-open test
```

## Test

```bash
make test
```

## Мониторинг

```bash
# Проверить staleness метрик
curl -s localhost:10000/health/metrics | jq

# Ожидаемый результат при healthy:
# {
#   "status": "healthy",
#   "is_stale": false,
#   "metrics_staleness_minutes": 15.5,
#   "circuit_breaker": {
#     "state": "closed",
#     "failure_count": 0
#   }
# }
```

## Alert условия

1. `status != "healthy"` - система в degraded mode
2. `is_stale == true` - метрики старше 30 минут
3. `circuit_breaker.state == "open"` - Keitaro API недоступен
