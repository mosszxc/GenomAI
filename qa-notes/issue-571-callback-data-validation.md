# Issue #571: Валидация callback_data в Telegram handlers

## Что изменено

- Добавлена функция `parse_callback_data()` с валидацией:
  - Проверка на пустоту
  - Ограничение длины (64 символа - Telegram limit)
  - Regex-валидация формата (только `a-z_` для action, `a-zA-Z0-9-` для id)
  - Защита от SQL/XSS injection
- Обновлён `handle_callback_query()` для использования валидации
- Добавлено логирование невалидных callback_data
- Добавлены unit тесты (13 тестов)

## Файлы

- `decision-engine-service/src/routes/telegram.py`
- `decision-engine-service/tests/unit/test_callback_data_validation.py`

## Test

```bash
cd decision-engine-service && python3 -m pytest tests/unit/test_callback_data_validation.py -v --tb=short
```
