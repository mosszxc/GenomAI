# Issue #480: Trace IDs in Logs

## Что изменено

- Добавлен модуль `temporal/tracing.py` с structured logging (structlog)
- Конфигурация JSON-логов с автоматическими trace IDs
- `get_workflow_logger()` — автоматически добавляет workflow_id, run_id, workflow_type
- `get_activity_logger()` — автоматически добавляет activity name, workflow_id, run_id, attempt
- Интегрировано в:
  - `temporal/workflows/creative_pipeline.py` — основной pipeline
  - `temporal/activities/transcription.py` — транскрипция
  - `temporal/activities/module_extraction.py` — извлечение модулей
- Worker инициализирует structlog при старте

## Пример вывода

```json
{
  "timestamp": "2024-01-12T10:30:00.000000Z",
  "level": "INFO",
  "logger": "temporal.tracing",
  "workflow_id": "creative-pipeline-abc123",
  "run_id": "xyz789",
  "creative_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Pipeline started"
}
```

## Test

```bash
cd decision-engine-service && python3 -c "from temporal.tracing import configure_structlog, get_logger; configure_structlog(json_output=True); log = get_logger('test', trace_id='test-123'); log.info('Test')" 2>&1 | grep -q '"trace_id": "test-123"' && echo "OK: trace_id present in logs" || echo "FAIL: trace_id missing"
```

## Дальнейшие шаги

Постепенно мигрировать остальные workflows и activities на structured logging:
- `temporal/workflows/keitaro_polling.py`
- `temporal/workflows/health_check.py`
- `temporal/workflows/premise_extraction.py`
- И другие файлы с `workflow.logger` / `activity.logger`
