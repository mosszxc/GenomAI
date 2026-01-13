# Issue #589: fix LogInteractionInput.message_type docstring

## Что изменено
- Исправлен комментарий для `message_type` в `LogInteractionInput`
- Старое значение: `"bot", "user", "system", "command"` (неверно)
- Новое значение: `"text", "video", "photo", "document", "command", "callback", "system"` (соответствует constraint в БД)

## Test
```bash
grep -q '"text", "video", "photo", "document", "command", "callback", "system"' decision-engine-service/temporal/activities/buyer.py && echo "OK: docstring matches DB constraint"
```
