# Issue #698: Clean up test idea with invalid hash

## Что изменено
- Удалена тестовая запись `00000000-0000-0000-0000-000000000003` с невалидным canonical_hash
- Добавлен CHECK constraint `ideas_canonical_hash_length` на таблицу `genomai.ideas`
- Теперь canonical_hash должен быть NULL или ровно 64 символа (SHA256)

## Файлы
- `infrastructure/migrations/046_ideas_hash_constraint.sql`

## Test
```bash
grep -q "CHECK.*LENGTH.*canonical_hash.*64" infrastructure/migrations/046_ideas_hash_constraint.sql && echo "OK: constraint present"
```

## Ручная проверка (после применения миграции)
```sql
-- Проверить что запись удалена
SELECT * FROM genomai.ideas WHERE id = '00000000-0000-0000-0000-000000000003';

-- Проверить constraint
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_schema = 'genomai' AND table_name = 'ideas'
AND constraint_name = 'ideas_canonical_hash_length';
```
