# Testing Rules

## ⛔ STOP-GATE: Before Closing Issue

```
╔═══════════════════════════════════════════════════════════════╗
║  НЕТ PRODUCTION ТЕСТА = НЕТ ЗАКРЫТИЯ ISSUE                   ║
║  Unit tests НЕ СЧИТАЮТСЯ. Нужен РЕАЛЬНЫЙ запуск.             ║
╚═══════════════════════════════════════════════════════════════╝
```

## Что НЕ является тестом (антипаттерны)

| ❌ НЕ тест | ✅ Тест |
|-----------|---------|
| `pytest tests/unit/` | `temporal.schedules trigger` + проверка БД |
| "SQL синтаксически корректен" | `execute_sql` SELECT → данные видны |
| "Код компилируется" | `curl` endpoint → HTTP 200 + body |
| "Логика правильная" | Render logs → нет ошибок после deploy |

## Обязательные тесты по типу

### Workflow
```bash
# 1. Trigger workflow
python -m temporal.schedules trigger {workflow-name}

# 2. Проверить логи (ждать 30-60 сек)
mcp__render__list_logs resource=["{service-id}"] limit=20

# 3. Проверить данные в БД
mcp__supabase__execute_sql "SELECT * FROM genomai.{table} ORDER BY created_at DESC LIMIT 5"
```
**Критерий:** Логи без ошибок + данные появились в БД

### API Endpoint
```bash
# 1. Вызвать endpoint
curl -X POST https://genomai.onrender.com/api/{endpoint} \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# 2. Проверить response
# HTTP 200 + правильный body
```
**Критерий:** HTTP 200 + body содержит ожидаемые данные

### Migration
```sql
-- 1. Проверить что таблица/колонка существует
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = '{table}';

-- 2. Проверить constraints
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'genomai.{table}'::regclass;

-- 3. Проверить данные (если applicable)
SELECT * FROM genomai.{table} LIMIT 5;
```
**Критерий:** Schema correct + constraints exist + no errors

### Telegram Command
```bash
# 1. WebFetch к webhook
WebFetch URL: https://genomai.onrender.com/telegram/webhook
Body: {"message": {"text": "/{command}", "chat": {"id": 123}}}

# 2. Проверить логи
mcp__render__list_logs

# 3. Проверить БД (если команда пишет данные)
mcp__supabase__execute_sql
```
**Критерий:** Webhook 200 + логи без ошибок + данные в БД

## ⛔ BLOCKING Checklist

**ПЕРЕД написанием "готово/done/завершено" выполни ВСЕ:**

```
□ PRODUCTION TEST EXECUTED
  └─ Команда: _________________ (вставить реальную команду)
  └─ Результат: _______________ (вставить output)

□ TEST PASSED
  └─ HTTP Status: 200 / Данные в БД: да / Логи: без ошибок

□ qa-notes/issue-{N}-*.md содержит:
  └─ Секция "## Production Test"
  └─ Реальные команды которые были выполнены
  └─ Реальный output

□ Git commit + push выполнен
```

**Если хоть один пункт не выполнен — СТОП. Issue НЕ закрыт.**

## Формат секции Testing в qa-notes

```markdown
## Production Test

### Executed
\`\`\`bash
# Реальная команда которая была выполнена
python -m temporal.schedules trigger maintenance
\`\`\`

### Result
\`\`\`
# Реальный output
Triggered workflow: maintenance-workflow-2026-01-11
\`\`\`

### Verification
\`\`\`sql
-- Запрос в БД
SELECT * FROM genomai.staleness_checks ORDER BY created_at DESC LIMIT 3;
\`\`\`

### Output
\`\`\`
-- Результат запроса
id | check_type | result | created_at
1  | win_rate   | ok     | 2026-01-11 15:00:00
\`\`\`

**Status:** PASSED / FAILED
```

## Нарушение = A006 Critical

Закрытие issue без production теста:
- Записывается в LESSONS.md как антипаттерн A006
- Issue переоткрывается
- Требуется выполнить тест перед повторным закрытием

## Quick Reference

| Изменил | Выполни | Проверь |
|---------|---------|---------|
| Workflow | `temporal.schedules trigger` | `list_logs` + `execute_sql` |
| API | `curl` endpoint | HTTP 200 + body |
| Migration | `execute_sql` DDL | `execute_sql` SELECT |
| Telegram | `WebFetch` webhook | `list_logs` + БД |
