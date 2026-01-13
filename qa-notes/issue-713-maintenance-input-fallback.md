# Issue #713: MaintenanceInput backwards compatibility

## Что изменено

- Добавлен `getattr()` fallback для `stuck_transcription_timeout_minutes` (default=30)
- Добавлен `getattr()` fallback для `stuck_decomposition_timeout_minutes` (default=30)
- Добавлен `getattr()` fallback для `stuck_recovery_force_threshold_minutes` (default=120)

## Причина

Temporal schedules хранят сериализованный input. Когда schedule был создан **до** добавления новых атрибутов (Issue #696), старый input не содержит эти поля. При десериализации Python не может найти атрибут → AttributeError.

## Решение

Использование `getattr(input, "attr_name", default)` вместо прямого доступа `input.attr_name` обеспечивает обратную совместимость с любым сериализованным input.

## После деплоя

Рекомендуется пересоздать schedule для использования актуального input:

```bash
python -m temporal.schedules delete maintenance
python -m temporal.schedules create
```

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-713-high-maintenanceworkflow-падает-maintena && python -c "
from temporal.workflows.maintenance import MaintenanceInput, MaintenanceWorkflow
from dataclasses import asdict

# Simulate old input without new attributes
class OldInput:
    recommendation_expiry_days = 7
    failed_creative_retention_days = 7
    run_integrity_checks = True
    run_staleness_check = True
    run_cleanup = True
    import_queue_retention_days = 7
    knowledge_retention_days = 30
    staleness_archive_days = 90
    run_hypothesis_retry = True
    hypothesis_max_retries = 3
    run_orphan_detection = True
    agent_heartbeat_timeout_minutes = 10
    run_stuck_recovery = True
    run_orphan_hypothesis_cleanup = True
    run_failed_retry = True
    failed_creative_max_retries = 3
    failed_creative_min_age_minutes = 30
    run_weekly_snapshots = True
    _processed_stuck_ids = []
    _processed_failed_ids = []
    _accumulated_stuck_recovered = 0
    _accumulated_stuck_failed = 0
    _accumulated_failed_retried = 0
    _accumulated_failed_abandoned = 0

old_input = OldInput()

# Test getattr fallbacks
stuck_timeout = getattr(old_input, 'stuck_transcription_timeout_minutes', 30)
decomp_timeout = getattr(old_input, 'stuck_decomposition_timeout_minutes', 30)
force_threshold = getattr(old_input, 'stuck_recovery_force_threshold_minutes', 120)

assert stuck_timeout == 30, f'Expected 30, got {stuck_timeout}'
assert decomp_timeout == 30, f'Expected 30, got {decomp_timeout}'
assert force_threshold == 120, f'Expected 120, got {force_threshold}'

print('OK: getattr fallbacks work correctly')
"
```
