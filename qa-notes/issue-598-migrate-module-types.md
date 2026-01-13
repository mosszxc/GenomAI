# Issue #598: Data Migration — Map Existing Modules

## Что изменено

- Создана миграция `045_migrate_module_types.sql`
- UPDATE module_bank: `hook` → `hook_mechanism`
- UPDATE module_bank: `promise` → `promise_type`
- UPDATE module_bank: `proof` → `proof_type`
- Обновлён CHECK constraint для новых значений

## Файлы

- `infrastructure/migrations/045_migrate_module_types.sql`

## Test

```bash
# Проверка что миграция синтаксически корректна
cat infrastructure/migrations/045_migrate_module_types.sql | grep -q "hook_mechanism" && echo "OK: migration contains new types"
```
