# Issue #586 - buyer_interactions message_type constraint

## Что изменено
- Добавлен тип `'feedback'` в constraint `buyer_interactions_message_type_check`
- Создана миграция `042_buyer_interactions_feedback_type.sql`

## Применение миграции
Выполнить в Supabase Dashboard SQL Editor:
```sql
ALTER TABLE genomai.buyer_interactions DROP CONSTRAINT IF EXISTS buyer_interactions_message_type_check;
ALTER TABLE genomai.buyer_interactions ADD CONSTRAINT buyer_interactions_message_type_check
  CHECK (message_type IN ('text', 'video', 'photo', 'document', 'command', 'callback', 'system', 'feedback'));
```

## Test
```bash
echo "Migration file exists" && test -f infrastructure/migrations/042_buyer_interactions_feedback_type.sql && echo "OK"
```
