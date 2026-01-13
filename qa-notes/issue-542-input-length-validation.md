# Issue #542: Missing input length validation

## Что изменено

- Добавлена константа `MAX_FEEDBACK_LENGTH = 500` в `telegram.py`
- Добавлена валидация максимальной длины для `/feedback` текста
- При превышении лимита пользователю показывается сообщение об ошибке

## Файлы

- `decision-engine-service/src/routes/telegram.py`

## Test

```bash
grep -n "MAX_FEEDBACK_LENGTH" decision-engine-service/src/routes/telegram.py && grep -n "len(feedback_text) > MAX_FEEDBACK_LENGTH" decision-engine-service/src/routes/telegram.py && echo "OK: validation added"
```
