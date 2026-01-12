# Issue #458: Просмотр переписки с байером через /buyers

## Изменения
- `handle_chat_history()` — показ 20 последних сообщений с байером
- `send_telegram_message()` — добавлен `reply_markup` для inline кнопок
- `/buyers` — inline кнопки "💬 Имя" для каждого байера
- `handle_callback_query()` — обработка `chat_{telegram_id}`

## Тестирование
1. `/buyers` — показывает список с кнопками
2. Нажатие кнопки — показывает переписку в формате:
   ```
   💬 Переписка с @username

   12:30 → /start
   12:30 ← Добро пожаловать!
   ```

## Файлы
- `decision-engine-service/src/routes/telegram.py`

## PR
- https://github.com/mosszxc/GenomAI/pull/460
