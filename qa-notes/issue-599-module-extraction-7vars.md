# Issue #599: Module Extraction Update — 7 Variables

## Что изменено

- Обновлён `MODULE_FIELDS` для поддержки 7 типов модулей вместо 3
- Добавлена fallback логика в `extract_module_content()`:
  - `hook_mechanism` ← `opening_type`
  - `angle_type` ← `emotional_trigger`
  - `message_structure` ← `story_type`
  - `ump_type` ← `ums_type`
  - `promise_type` ← `state_before + state_after` (composite)
  - `proof_type` ← `proof_source`
  - `cta_style` ← `risk_reversal_type`
- Обновлён `compute_module_key()` для использования primary_field
- Обновлён `extract_modules_from_decomposition()` для возврата 7 module_id
- Добавлены 24 unit теста для новой логики

## Файлы

- `decision-engine-service/temporal/activities/module_extraction.py`
- `decision-engine-service/tests/unit/test_module_extraction.py`
- `decision-engine-service/tests/integration/test_module_extraction_integration.py`

## Test

```bash
cd decision-engine-service && python3 -m pytest tests/unit/test_module_extraction.py -v --tb=short 2>&1 | tail -5
```

## Variable Mapping Table (из issue)

| Новая переменная | Поле в decomposition | Fallback |
|------------------|---------------------|----------|
| `hook_mechanism` | hook_mechanism | opening_type |
| `angle_type` | angle_type | emotional_trigger |
| `message_structure` | message_structure | story_type |
| `ump_type` | ump_type | ums_type |
| `promise_type` | promise_type | state_before + state_after |
| `proof_type` | proof_type | proof_source |
| `cta_style` | cta_style | risk_reversal_type |
