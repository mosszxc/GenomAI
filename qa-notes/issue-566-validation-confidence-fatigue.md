# Issue #566: No validation confidence/fatigue values in learning_loop

## Что изменено

- Добавлена константа `MAX_FATIGUE = 1000.0` для контроля overflow
- Добавлен логгер для warning при overflow
- В `get_current_confidence`: валидация confidence из БД в диапазон [0.0, 1.0]
- В `get_current_fatigue`: валидация fatigue из БД >= 0
- В `process_single_outcome`: валидация new_fatigue >= 0 и warning при overflow

## Test

```bash
grep -n 'MAX_FATIGUE\|max(0.0, min(1.0\|max(0.0, raw_fatigue\|max(0.0, new_fatigue' decision-engine-service/src/services/learning_loop.py && echo OK
```
