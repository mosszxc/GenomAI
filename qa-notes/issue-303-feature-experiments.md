# QA Notes: Issue #303 - Feature Experiments Infrastructure

## Summary
Создана инфраструктура для экспериментов с ML фичами: таблицы БД и Python service.

## Changes
1. **Migration** `033_feature_experiments.sql`:
   - `feature_experiments` — реестр фичей с lifecycle (shadow → active → deprecated)
   - `derived_feature_values` — вычисленные значения фичей для entities

2. **Service** `feature_registry.py`:
   - `add_feature()` — добавление фичи в shadow статусе
   - `get_feature()`, `list_features()` — чтение
   - `can_promote()` — валидация перед promotion
   - `promote_feature()` — shadow → active
   - `deprecate_feature()` — любой статус → deprecated
   - `update_feature_metrics()` — обновление sample_size и correlation
   - `store_feature_value()`, `get_feature_value()` — работа с derived values

## Governance Rules
```python
FEATURE_RULES = {
    "min_sample_size": 100,
    "min_abs_correlation": 0.08,
    "max_active_features": 10,
    "deprecate_after_days": 30,
}
```

## Tests Executed
| Test | Result |
|------|--------|
| Add feature (shadow) | ✓ |
| Update metrics | ✓ |
| Promote to active | ✓ |
| Deprecate | ✓ |
| derived_feature_values insert | ✓ |

## Verification Queries
```sql
-- Check feature_experiments
SELECT name, status, sample_size, correlation_cpa
FROM genomai.feature_experiments;

-- Check derived_feature_values
SELECT * FROM genomai.derived_feature_values LIMIT 5;
```

## Related
- Epic: #302 (ML Feature Engineering System)
- Next: #304 (Feature Computation Workflow)
