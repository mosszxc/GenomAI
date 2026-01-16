# Issue #743: Отключить онбоардинг в Telegram боте

## Что изменено

- `/start` команда теперь отправляет ссылку на сайт Cockpit вместо запуска BuyerOnboardingWorkflow
- Добавлена inline-кнопка для перехода на сайт регистрации
- Обновлено help сообщение с новой ссылкой на сайт
- Обновлены сообщения "не зарегистрирован" с ссылкой на Cockpit

## Изменённые файлы

- `decision-engine-service/src/routes/telegram.py`
  - `handle_start_command()` - редирект на Cockpit
  - `handle_help_command()` - обновлён текст
  - Сообщения о регистрации в `handle_stats_command()` и `handle_video_url()`

## Test

```bash
# Проверяем что код содержит URL Cockpit
grep -q "cockpit.genomai.com/onboarding" decision-engine-service/src/routes/telegram.py && echo "OK: Cockpit URL found"
```
