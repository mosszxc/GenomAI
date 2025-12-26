# n8n Workflow Test

> **Note:** Для валидации всего процесса используй `/valid {process}`

Запусти и протестируй n8n workflow с проверкой результата в БД.

## Входные данные

```
$ARGUMENTS = workflow_id [table_name] [--field=value]
```

Примеры:
- `/n8n-test 5q3mshC9HRPpL6C0` — только запуск
- `/n8n-test 5q3mshC9HRPpL6C0 hypotheses` — проверить таблицу
- `/n8n-test oxG1DqxtkTGCqLZi ideas --idea_id=abc123` — с payload

## Инструкции

### 1. Получи информацию о workflow

```
mcp__n8n-mcp__n8n_get_workflow(id: workflow_id, mode: "structure")
```

Определи:
- Тип триггера (webhook/schedule/manual)
- Webhook path (если есть)
- Целевые таблицы (какие Supabase nodes есть)

### 2. Запусти workflow

```
mcp__n8n-mcp__n8n_test_workflow(
  workflowId: workflow_id,
  triggerType: "webhook",
  httpMethod: "POST",
  data: { ...payload },
  timeout: 30000
)
```

### 3. Проверь execution

```
mcp__n8n-mcp__n8n_executions(
  action: "list",
  workflowId: workflow_id,
  limit: 1
)
```

Затем детали:
```
mcp__n8n-mcp__n8n_executions(
  action: "get",
  id: execution_id,
  mode: "summary"  // или "error" если status != success
)
```

### 4. Проверь БД (если указана таблица)

```sql
SELECT * FROM genomai.{table_name}
ORDER BY created_at DESC
LIMIT 3;
```

Проверь:
- Новые записи появились?
- Поля заполнены корректно?
- Status изменился?

### 5. Проверь event_log

```sql
SELECT event_type, entity_id, payload, occurred_at
FROM genomai.event_log
ORDER BY occurred_at DESC
LIMIT 5;
```

### 6. Выведи результат

```markdown
## Test Result: [workflow_name]

### Execution
- ID: [execution_id]
- Status: [success/error]
- Duration: [ms]

### Nodes Executed
| Node | Items In | Items Out | Status |
|------|----------|-----------|--------|
| ... | ... | ... | ... |

### Database Check
| Table | Records | Status |
|-------|---------|--------|
| [table] | [count] | OK/FAIL |

### Events Emitted
| Event | Entity | Time |
|-------|--------|------|
| ... | ... | ... |

### Verdict: PASS / FAIL
```

## Типичные проблемы

### Workflow не триггерится
1. Проверь что workflow active
2. Проверь webhook path
3. Попробуй через n8n UI

### Execution failed
1. Используй `mode: "error"` для деталей
2. Проверь credentials
3. Проверь expressions

### Данные не в БД
1. Проверь что node выполнился (itemsOutput > 0)
2. Проверь schema (genomai vs public)
3. Проверь constraints

## Примеры

```
/n8n-test 5q3mshC9HRPpL6C0 hypotheses
# Тест Telegram Delivery → проверка hypotheses.status

/n8n-test oxG1DqxtkTGCqLZi hypotheses --idea_id=cf35817c-d4d5-4a00-b9bc-e0e8b18776fb
# Тест Hypothesis Factory с конкретной idea

/n8n-test 243QnGrUSDtXLjqU event_log
# Тест Outcome Aggregator → проверка событий
```
