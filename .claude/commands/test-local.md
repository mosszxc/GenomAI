# /test-local — Тест issue на локальных сервисах

Тестирует изменения из текущего issue на локальной среде.

## Алгоритм

1. **Определи issue номер** из текущей ветки или спроси пользователя
2. **Проверь что локальные сервисы запущены:**
   ```bash
   curl -s http://localhost:8233/api/v1/namespaces 2>/dev/null && echo "Temporal OK" || echo "Temporal NOT RUNNING"
   curl -s http://localhost:10000/health 2>/dev/null || curl -s http://localhost:$(cat /tmp/genomai-dev/server-*.pid 2>/dev/null | head -1 | xargs -I{} basename {} .pid | sed 's/server-//')/health 2>/dev/null && echo "FastAPI OK" || echo "FastAPI NOT RUNNING"
   ```
3. **Если сервисы не запущены** — скажи пользователю `make up`
4. **Определи тип изменений** по файлам в коммитах:
   - `temporal/workflows/` или `temporal/activities/` → Workflow тест
   - `src/routes/` или `main.py` → API тест
   - `migrations/` → Migration тест
   - `telegram.py` → Telegram тест

5. **Выполни соответствующий тест:**

### Workflow тест
```bash
# Найди какой workflow изменился
git diff origin/develop --name-only | grep temporal/workflows

# Триггерни через Temporal UI или CLI
temporal workflow start --task-queue <queue> --type <WorkflowName> --input '{}'
```

### API тест
```bash
# Определи какой endpoint изменился
git diff origin/develop --name-only | grep src/routes

# Вызови endpoint
curl -X POST http://localhost:10000/api/<endpoint> -H "Content-Type: application/json" -d '{...}'
```

### Migration тест
```sql
-- Проверь что таблица/колонка существует
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = '<table>';
```

### Telegram тест
```bash
# Симулируй webhook
curl -X POST http://localhost:10000/telegram/webhook -H "Content-Type: application/json" -d '{
  "update_id": 1,
  "message": {
    "message_id": 1,
    "from": {"id": 123, "first_name": "Test"},
    "chat": {"id": 123, "type": "private"},
    "text": "/start"
  }
}'
```

6. **Покажи результат:**
```
LOCAL TEST: [PASSED/FAILED]
  Type: <тип>
  Command: <команда>
  Result: <вывод>
```

## Пример использования

```
User: /test-local
Assistant:
Определяю issue из текущей ветки...
Issue: #506 (feat: add new endpoint)

Проверяю локальные сервисы...
✓ Temporal running
✓ FastAPI running on :10000

Анализирую изменения...
Тип: API (изменён src/routes/learning.py)

Выполняю тест...
curl -X POST http://localhost:10000/learning/process -d '{"idea_id": "test"}'

LOCAL TEST: PASSED
  Type: API
  Command: curl -X POST http://localhost:10000/learning/process
  Result: {"status": "ok", "processed": 1}
```
