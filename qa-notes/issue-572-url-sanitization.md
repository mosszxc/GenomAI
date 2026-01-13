# Issue #572: URL parameter interpolation без санитизации

## Что изменено

- Добавлена функция `validate_safe_string()` в `temporal/models/validators.py`:
  - Проверяет что строка содержит только безопасные символы (alphanumeric, `_`, `-`)
  - Предотвращает URL injection и PostgREST query manipulation
  - Добавлен параметр `max_length` для ограничения длины

- Добавлена функция `validate_optional_safe_string()` для Optional[str] параметров

- Применена валидация в `src/services/premise_selector.py`:
  - `validate_uuid()` для premise_id, avatar_id, idea_id
  - `validate_optional_safe_string()` для geo, vertical

- Применена валидация в `src/services/component_learning.py`:
  - `validate_uuid()` для creative_id, idea_id, buyer_id, record_id
  - `validate_safe_string()` для component_type, component_value

- Добавлены unit-тесты для новых валидаторов (15 тестов):
  - SQL injection attempts
  - URL manipulation attempts
  - PostgREST operator injection
  - Special characters validation
  - Max length validation

## Severity

**HIGH** - исправлена потенциальная injection-уязвимость

## Test

```bash
cd decision-engine-service && python3 -m pytest tests/unit/test_activity_validators.py::TestValidateSafeString -v --tb=short
```
