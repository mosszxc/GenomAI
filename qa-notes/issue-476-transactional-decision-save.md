# Issue #476: Decision + Trace Transactional Save

## Что изменено

- Создана RPC функция `genomai.save_decision_with_trace()` для атомарного сохранения
- Добавлена функция `save_decision_with_trace()` в `supabase.py`
- Обновлена `_create_decision()` в `decision_engine.py` для использования транзакционного сохранения
- Удалён ручной rollback код (больше не нужен)

## Проблема

Decision и Decision Trace сохранялись отдельными запросами без транзакции:
```python
await save_decision(decision)  # Успешно
await save_decision_trace(trace)  # Может упасть
```

При worker crash между операциями → orphaned decision без trace.

## Решение

Supabase RPC с транзакцией:
```sql
CREATE FUNCTION genomai.save_decision_with_trace(...)
RETURNS JSONB AS $$
BEGIN
    INSERT INTO decisions ...;
    INSERT INTO decision_traces ...;
    RETURN jsonb_build_object(...);
END;
$$ LANGUAGE plpgsql;
```

Теперь: либо оба записываются, либо ни один.

## Файлы

- `infrastructure/migrations/041_save_decision_with_trace.sql` - RPC функция
- `decision-engine-service/src/services/supabase.py:308-365` - Python wrapper
- `decision-engine-service/src/services/decision_engine.py:206-207` - использование

## Deploy steps

1. Применить миграцию `041_save_decision_with_trace.sql` в Supabase SQL Editor
2. Deploy код через `./scripts/deploy.sh`

## Test

```bash
make test-unit && echo "PASSED"
```
