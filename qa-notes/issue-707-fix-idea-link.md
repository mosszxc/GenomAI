# Issue #707: Fix decomposed_creatives.idea_id linking

## Проблема
RPC функция `upsert_idea_with_link` связывала `idea_id` только для **новых** ideas.
Для существующих ideas (когда `v_upsert_status = 'existing'`) `idea_id` оставался NULL.

**Root cause:** Строка 120 в миграции 045:
```sql
IF p_decomposed_creative_id IS NOT NULL AND v_upsert_status = 'created' THEN
```

## Решение
1. Исправлена RPC функция - теперь связывает `idea_id` **всегда** (для новых и существующих ideas)
2. Добавлен ретроактивный фикс для существующих записей через `canonical_hash` в payload

## Файлы
- `infrastructure/migrations/046_fix_upsert_idea_link_existing.sql`

## Применение миграции

⚠️ **Миграцию нужно применить вручную через Supabase Dashboard:**

1. Открыть https://supabase.com/dashboard/project/ftrerelppsnbdcmtcwya/sql
2. Скопировать содержимое `046_fix_upsert_idea_link_existing.sql`
3. Выполнить SQL

## Legacy данные
4 записи остались без `idea_id` - это старые данные без `canonical_hash` в payload.
Их невозможно автоматически связать. Новые записи будут всегда связаны.

## Test

```bash
curl -sf localhost:10000/health && echo "OK: service healthy"
```
