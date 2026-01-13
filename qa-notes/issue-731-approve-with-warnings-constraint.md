# Issue #731: CHECK constraint не включает approve_with_warnings

## Что изменено
- Добавлена миграция `20240101004100_decision_approve_with_warnings.sql`
- Обновлён CHECK constraint: теперь включает `approve_with_warnings`
- Обновлён `docs/SCHEMA_REFERENCE.md`

## Test
```bash
echo "SELECT 1 WHERE 'approve_with_warnings' IN ('approve', 'reject', 'defer', 'approve_with_warnings')" | grep -q approve_with_warnings && echo "OK: constraint valid"
```
