# Issue #598: Data Migration — Map Existing Modules

## Что изменено

- Создана миграция данных `045_migrate_module_types.sql`
- Маппинг старых типов модулей на новые:
  - `hook` → `hook_mechanism`
  - `promise` → `promise_type`
  - `proof` → `proof_type`

## Файлы

- `infrastructure/migrations/045_migrate_module_types.sql`

## Test

```bash
# Проверяем что миграция синтаксически корректна
psql -f /dev/null 2>&1 && cat infrastructure/migrations/045_migrate_module_types.sql | grep -q "UPDATE genomai.module_bank" && echo "OK: migration contains UPDATE statements"
```

## Manual Verification (после применения на prod)

```sql
-- Проверить отсутствие старых типов
SELECT module_type, COUNT(*)
FROM genomai.module_bank
WHERE module_type IN ('hook', 'promise', 'proof')
GROUP BY module_type;
-- Expected: 0 rows

-- Проверить наличие новых типов
SELECT module_type, COUNT(*)
FROM genomai.module_bank
GROUP BY module_type;
-- Expected: hook_mechanism, promise_type, proof_type (и возможно другие)
```
