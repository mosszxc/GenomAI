# Issue #590: Remove deprecated buyer_states table

## Что изменено

- Удалена таблица `buyer_states` (миграция 042_drop_buyer_states.sql)
- Удалена activity `reset_stale_buyer_states` из maintenance.py
- Удалена activity `cleanup_idle_buyer_states` из hygiene_cleanup.py
- Удалены связанные поля из моделей (CleanupStats, CleanupInput, MaintenanceInput, MaintenanceResult)
- Обновлена документация (SCHEMA_REFERENCE, TEMPORAL_WORKFLOWS, E2E_REFERENCE, SPHERES, SYSTEM_CAPABILITIES)

## Причина

Таблица `buyer_states` использовалась для stateful multi-step онбординга.
После перехода на Temporal состояние хранится в workflow, таблица больше не нужна.

## Test

```bash
cd decision-engine-service && python3 -c "from temporal.activities.maintenance import expire_old_recommendations; from temporal.activities.hygiene_cleanup import run_all_cleanup; print('OK: imports work')"
```
