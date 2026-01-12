# Issue #493: Buyer chat history показывает все связанные сообщения

## Проблема
При нажатии кнопки "💬 Чат" в `/buyers` показывало "Сообщений нет", хотя существовали системные уведомления о креативах/гипотезах баера.

**Причина:** `buyer_interactions` искала только по `telegram_id`, а системные сообщения отправлялись админу с его telegram_id, без связи с баером.

## Решение
1. Добавлена колонка `buyer_id` в `buyer_interactions` (FK → buyers.id)
2. `log_buyer_interaction()` теперь принимает опциональный `buyer_id`
3. `handle_chat_history()` ищет по `telegram_id` ИЛИ `buyer_id`

## Миграция БД
```sql
ALTER TABLE genomai.buyer_interactions
ADD COLUMN buyer_id UUID REFERENCES genomai.buyers(id);

CREATE INDEX idx_buyer_interactions_buyer_id
ON genomai.buyer_interactions(buyer_id);
```

## Тестирование
- Добавлена тестовая запись с buyer_id для баера Tu
- Запрос PostgREST с OR успешно находит записи

## Файлы
- `decision-engine-service/src/routes/telegram.py`

## PR
- https://github.com/mosszxc/GenomAI/pull/496
