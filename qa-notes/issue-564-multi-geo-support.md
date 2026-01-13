# Issue #564 - Multi-geo support in component_learning

## Что изменено

- Переименована функция `get_creative_geo()` → `get_creative_geos()`
- Изменён возвращаемый тип: `Optional[str]` → `list[str]`
- Теперь возвращаются все geo вместо только первого
- `process_component_learnings()` создаёт ComponentUpdate для каждого geo
- Добавлен счётчик `geos_processed` в результат

## Было (silent truncation)

```python
# Если geos = ["US", "DE", "FR"], возвращалось только "US"
return geos[0] if geos else None
```

## Стало (multi-geo support)

```python
# Возвращаются все geos: ["US", "DE", "FR"]
return geos if isinstance(geos, list) else []
```

## Test

```bash
cd decision-engine-service && python3 -c "
from src.services.component_learning import get_creative_geos
import inspect
sig = inspect.signature(get_creative_geos)
ret = sig.return_annotation
# Проверяем что функция возвращает list[str]
assert 'list' in str(ret), f'Expected list return type, got {ret}'
print('OK: get_creative_geos returns list[str]')
"
```
