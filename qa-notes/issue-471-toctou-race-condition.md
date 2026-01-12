# Issue #471: TOCTOU Race Condition в Idea Registry

## Что изменено

- Добавлена атомарная activity `upsert_idea` в `temporal/activities/supabase.py`
- Заменён паттерн check-then-create на атомарный upsert в `temporal/workflows/creative_pipeline.py`
- Добавлена функция `upsert_idea` в `src/services/idea_registry.py`
- Обновлена функция `register_idea` для использования атомарного upsert

## Как работает

Вместо:
```python
# TOCTOU - Race Condition!
existing = await check_idea_exists(hash)
if not existing:
    await create_idea(hash)  # Может упасть с 409 если другой процесс успел создать
```

Теперь:
```python
# Атомарно - INSERT ... ON CONFLICT DO NOTHING
idea = await upsert_idea(hash, decomposed_id)
# Всегда возвращает idea (новую или существующую)
```

## Файлы

- `decision-engine-service/temporal/activities/supabase.py` - новая activity `upsert_idea`
- `decision-engine-service/temporal/activities/__init__.py` - экспорт
- `decision-engine-service/temporal/workflows/creative_pipeline.py` - использование upsert_idea
- `decision-engine-service/src/services/idea_registry.py` - функция `upsert_idea` и обновлённая `register_idea`

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.activities.supabase import upsert_idea
import inspect
sig = inspect.signature(upsert_idea)
assert 'canonical_hash' in sig.parameters, 'Missing canonical_hash param'
assert 'decomposed_creative_id' in sig.parameters, 'Missing decomposed_creative_id param'
print('OK: upsert_idea activity signature correct')
" && python3 -c "
from src.services.idea_registry import upsert_idea
import inspect
sig = inspect.signature(upsert_idea)
assert 'canonical_hash' in sig.parameters, 'Missing canonical_hash param'
print('OK: idea_registry.upsert_idea signature correct')
"
```
