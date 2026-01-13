# Issue #604: DE Advisory Mode (Warnings for Buyers)

## Что изменено

- Добавлен параметр `mode` в API (`strict` / `advisory`)
- В advisory mode проверки death_memory и fatigue_constraint возвращают warnings вместо reject
- Создан новый decision type `approve_with_warnings`
- Warnings сохраняются в decision trace и возвращаются в API response

## Измененные файлы

- `src/utils/validators.py` - валидация параметра mode
- `src/services/decision_engine.py` - логика advisory mode
- `tests/unit/test_advisory_mode.py` - 14 тестов

## API Response (advisory mode)

```json
{
  "success": true,
  "decision": {
    "decision_type": "approve_with_warnings",
    "decision_reason": "approved_with_warnings"
  },
  "warnings": [
    {
      "check": "death_memory",
      "message": "Idea marked as dead (state: soft_dead)",
      "severity": "high",
      "details": {}
    }
  ]
}
```

## Test

```bash
cd decision-engine-service && uv run pytest tests/unit/test_advisory_mode.py -v && echo "OK: advisory mode tests passed"
```
