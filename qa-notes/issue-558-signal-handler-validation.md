# Issue #558: Signal handler без валидации telegram_id в buyer_onboarding

## Что изменено

- Добавлено обязательное поле `telegram_id` в модель `BuyerMessage`
- Добавлена валидация `telegram_id` в signal handler `user_message`:
  - Проверяет что `message.telegram_id == self._telegram_id`
  - Логирует warning и игнорирует сообщение при несовпадении
- Обновлён отправитель signal в `telegram.py` — передаёт `telegram_id` из `message.user_id`

## Security Fix

Злоумышленник больше не может отправить signal с чужим telegram_id — workflow игнорирует сообщения от неправильных пользователей.

## Test

```bash
grep -n "message.telegram_id != self._telegram_id" decision-engine-service/temporal/workflows/buyer_onboarding.py && echo "OK: validation present"
```
