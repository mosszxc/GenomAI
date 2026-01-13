# Issue #546: Fix TOCTOU Race Condition in component_learning.py

## Что изменено

1. **Новая миграция** `043_upsert_component_learnings.sql`:
   - PostgreSQL функция `upsert_component_learnings_batch(JSONB)`
   - Использует `INSERT ... ON CONFLICT DO UPDATE` для атомарного upsert
   - Accumulates sample_size, win_count, loss_count, total_spend, total_revenue

2. **Обновлён** `component_learning.py`:
   - `batch_upsert_component_learnings()` теперь вызывает RPC вместо Check-Then-Act
   - Убран TOCTOU race condition (SELECT + INSERT/UPDATE → атомарный upsert)
   - Удалён неиспользуемый импорт `validate_safe_string`

## Проблема

Check-Then-Act паттерн создавал race condition:
```
Process A: SELECT (row not found)
Process B: SELECT (row not found)
Process A: INSERT (success)
Process B: INSERT (duplicate or conflict error)
```

## Решение

Атомарный upsert через PostgreSQL `ON CONFLICT DO UPDATE`:
```sql
INSERT INTO component_learnings (...)
VALUES (...)
ON CONFLICT (component_type, component_value, geo, avatar_id)
DO UPDATE SET sample_size = sample_size + 1, ...
```

## Test

```bash
cd decision-engine-service && python -c "from src.services.component_learning import batch_upsert_component_learnings; print('OK: module loads')"
```
