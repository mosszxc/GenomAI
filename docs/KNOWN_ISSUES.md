# Known Issues & Resolutions

Документация известных проблем и их решений для предотвращения регрессий.

**Последнее обновление:** 2025-12-30

---

## Critical Issues

### #91: Decision Engine Cold Start (503 Error)

**Component:** `decision_engine_mvp` (YT2d7z5h9bPy1R4v), Decision Engine API
**Root Cause:** Render Free Tier спит после 15 мин неактивности → первый запрос получает 503/timeout
**Related Issues:** #101 (тестирование)

**Resolution:**
1. Добавлен `keep_alive_decision_engine` workflow (ClXUPP2IvWRgu99y)
   - Schedule: каждые 10 минут
   - Пингует `/health` endpoint
2. Retry logic в `decision_engine_mvp`:
   ```json
   {
     "retryOnFail": true,
     "maxTries": 3,
     "waitBetweenTries": 15000,
     "options": { "timeout": 60000 }
   }
   ```

**Prevention:**
- Keep-alive workflow должен быть АКТИВЕН в n8n UI (Schedule triggers не активируются через API)
- Мониторинг: check n8n executions для `keep_alive_decision_engine`

**Test:** `tests/integration/test_cold_start_recovery.py`

---

### #75-84: Learning Loop v2 Validation Errors

**Component:** `learning_loop_v2` (fzXkoG805jQZUR3S)
**Root Cause:** Несколько ошибок валидации в workflow:
- Webhook missing `onError` property (#84)
- Guard Check missing `combinator` field (#83)

**Resolution:**
```json
// Webhook node
{ "onError": "continueRegularOutput" }

// If node
{ "combineConditions": "and" }
```

**Prevention:**
- Validate workflow перед деплоем: `mcp__n8n-mcp__n8n_validate_workflow`
- Contract schema: `infrastructure/contracts/learning_loop_input.json`

---

### #76-77: Supabase Node Configuration Errors

**Component:** `buyer_creative_registration` (d5i9dB2GNqsbfmSD), `hypothesis_factory_generate` (oxG1DqxtkTGCqLZi)
**Root Cause:** Supabase nodes используют:
- Неверную операцию `insert` вместо `create`
- Отсутствует `tableId` field
- Missing schema headers

**Resolution:**
```json
{
  "operation": "create",  // НЕ "insert"
  "tableId": "table_name",
  "options": {
    "customHeaders": {
      "Accept-Profile": "genomai",
      "Content-Profile": "genomai"
    }
  }
}
```

**Prevention:**
- Все Supabase nodes должны использовать `operation: create` для INSERT
- Обязательные headers для schema `genomai`

---

### #78: Keitaro Poller Expression Format Errors

**Component:** `keitaro_poller` (0TrVJOtHiNEEAsTN)
**Root Cause:** Code nodes с неправильным форматом expressions:
- `{{ }}` вместо `$json.field`
- Missing `=` prefix в expressions

**Resolution:**
```javascript
// Было
{{ $json.data }}

// Стало
={{ $json.data }}
```

**Prevention:**
- Expression format: всегда начинать с `=` для n8n expressions
- Validate перед деплоем

---

## High Priority Issues

### #79: Creatives Stuck Without Decomposition

**Component:** `creative_decomposition_llm` (mv6diVtqnuwr7qev)
**Root Cause:** Pipeline прерывается между transcription и decomposition
**Symptoms:** 9 creatives в БД без связанных decomposed_creatives

**Resolution:**
- Chain call fix: `creative_transcription` → `creative_decomposition_llm` → `idea_registry_create`
- Добавлен explicit httpRequest call после transcription

**Detection Query:**
```sql
SELECT c.id, c.tracker_id, c.status
FROM genomai.creatives c
LEFT JOIN genomai.decomposed_creatives dc ON c.id = dc.creative_id
WHERE dc.id IS NULL AND c.status = 'transcribed';
```

**Prevention:**
- Integration test: `test_creative_pipeline.py`
- Monitoring: scheduled check for stuck creatives

---

### #80: DecisionAborted - idea_not_found

**Component:** `decision_engine_api`
**Root Cause:** `idea_registry_create` не создаёт идею до вызова Decision Engine
**Symptoms:** 12 events с `reason: idea_not_found`

**Resolution:**
- Исправлена цепочка: decomposition → idea_registry → decision_engine
- Добавлена валидация idea_id перед вызовом DE

**Detection Query:**
```sql
SELECT * FROM genomai.event_log
WHERE event_type = 'DecisionAborted'
AND payload->>'reason' = 'idea_not_found'
ORDER BY created_at DESC;
```

**Prevention:**
- Guard check в `decision_engine_mvp`: verify idea exists before API call

---

## Medium Priority Issues

### #58: $env Blocked in n8n Cloud

**Component:** Все workflows с `$env.` expressions
**Root Cause:** n8n Cloud блокирует доступ к environment variables

**Resolution:**
- Загружать конфигурацию из Supabase `genomai.config` таблицы
- Использовать Supabase credentials (node credentials, не env vars)

**Prevention:**
- Никогда не использовать `$env.` в expressions
- Config pattern: Load Config node → Extract Values → Use in API calls

---

### #55-57: Telegram Hypothesis Delivery Errors

**Component:** `telegram_hypothesis_delivery` (5q3mshC9HRPpL6C0)
**Root Cause:**
- Invalid operation в Supabase nodes
- Expression format errors
- entity_id expects UUID

**Resolution:**
1. Supabase: `operation: create`
2. Expressions: `={{ $json.field }}`
3. entity_id: use idea.id (UUID) not video_url

**Prevention:**
- Contract: `infrastructure/contracts/telegram_delivery_input.json`

---

## Anti-patterns Discovered

### Check → If Anti-pattern

**Problem:** `Supabase(getAll) → If($json.id) → Create/Update`
Когда getAll возвращает пустой массив, downstream nodes не получают данные.

**Solution:**
- Bypass If node
- Или: `onError: continueRegularOutput` на create node

**Affected Workflows:**
- Keitaro Poller
- Snapshot Creator
- Outcome Aggregator

---

### SplitInBatches Wrong Output

**Problem:** Processing node подключен к output 0 (done) вместо output 1 (loop)

**Solution:**
```json
"connections": {
  "Loop Over Items": {
    "main": [
      [{ "node": "Done Handler" }],    // output 0 - done
      [{ "node": "Process Item" }]     // output 1 - loop ← correct!
    ]
  }
}
```

---

### Partial Update Resets Parameters

**Problem:** `n8n_update_partial_workflow` обновление одного параметра сбрасывает другие

**Solution:** Включать все связанные параметры:
```json
{
  "parameters": {
    "method": "POST",
    "url": "new-url",
    "sendBody": true,
    "jsonBody": "..."
  }
}
```

---

## Quick Reference: Issue → Prevention

| Issue | Component | Prevention |
|-------|-----------|------------|
| Cold start | DE API | keep_alive workflow active |
| Supabase create | All Supabase nodes | `operation: create`, schema headers |
| Expression format | Code/Set nodes | `={{ }}` prefix |
| $env blocked | All | Load from config table |
| Stuck creatives | Pipeline | Integration tests |
| idea_not_found | DE API | Guard check before call |
| Empty array → If skip | Supabase getAll | Bypass pattern |

---

## Medium Priority Issues (continued)

### #183: Double-encoded JSON payload in decomposed_creatives

**Component:** `creative_decomposition_llm` (mv6diVtqnuwr7qev)
**Root Cause:** `Persist Decomposed Creative` node used `JSON.stringify()` on payload field. Supabase node already serializes objects to JSONB, causing double-encoding.

**Symptoms:** `jsonb_typeof(payload) = 'string'` instead of `'object'`

**Resolution:**
1. Removed `JSON.stringify()` wrapper from payload expression
2. Fixed corrupted data: `SET payload = (payload #>> '{}')::jsonb`

**Detection Query:**
```sql
SELECT id, jsonb_typeof(payload) as payload_type
FROM genomai.decomposed_creatives
WHERE jsonb_typeof(payload) != 'object';
```

**Prevention:**
- Never use `JSON.stringify()` when passing objects to Supabase n8n node JSONB fields
- Node handles serialization automatically

---

## Lessons Learned

### Don't Double-Serialize JSONB

**Context:** E2E quality check found `invalid_payload_type` in decomposed_creatives (Issue #183).

**Mistake:** Used `JSON.stringify()` on payload object before passing to Supabase node JSONB field.

**Reality:** Supabase n8n node automatically serializes objects to JSONB. Adding `JSON.stringify()` creates a JSON string inside JSONB: `'"{\\"key\\":\\"value\\"}"'`.

**Correct Approach:**
```javascript
// WRONG - double-encoded
"fieldValue": "={{ JSON.stringify(myObject) }}"

// CORRECT - direct object
"fieldValue": "={{ myObject }}"
```

**Rule:** Never use `JSON.stringify()` for Supabase node JSONB fields. The node handles serialization.

---

### Always Measure, Never Assume

**Context:** Pipeline Health Monitor отправлял ложные "DE is DOWN" алерты из-за cold start.

**Mistake:** Поставил wait = 45s "на глаз" / по документации Render, не измерив реальное время.

**Reality:** Cold start занял 85 секунд. Workflow проверял здоровье до того как DE запустился.

**Correct Approach:**
```bash
# 1. Измерить реальное значение
curl -w "Time: %{time_total}s" --max-time 120 https://genomai.onrender.com/health
# Результат: 85s

# 2. Добавить запас 10-20%
# Wait = 90-100s

# 3. Тестировать в реальных условиях (после того как сервис "уснёт")
```

**Rule:** Для любых таймаутов, интервалов, лимитов — сначала измерь реальные значения, потом добавь запас. Не полагайся на документацию или предположения.

---

### Supabase Node useCustomSchema Ignored via API

**Context:** Issue #185 - Buyer State Cleanup workflow не находил таблицу buyer_states.

**Mistake:** Использовал Supabase node с `options.useCustomSchema: true` и `options.schema: "genomai"`, обновляя через n8n API.

**Reality:** Supabase node при обновлении через API игнорирует `options.useCustomSchema`. Active version workflow получает `useCustomSchema: false` → ищет таблицу в public schema.

**Correct Approach:**
```javascript
// WRONG - Supabase node через API
{
  "type": "n8n-nodes-base.supabase",
  "parameters": {
    "operation": "getAll",
    "tableId": "buyer_states",
    "options": { "useCustomSchema": true, "schema": "genomai" }
  }
}

// CORRECT - HTTP Request с headers
{
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "GET",
    "url": "https://PROJECT.supabase.co/rest/v1/table_name",
    "authentication": "predefinedCredentialType",
    "nodeCredentialType": "supabaseApi",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        { "name": "Content-Profile", "value": "genomai" },
        { "name": "Accept-Profile", "value": "genomai" }
      ]
    }
  }
}
```

**Rule:** Для работы с custom schema через API — используй HTTP Request с headers `Content-Profile` и `Accept-Profile` вместо Supabase node.

---

### n8n "Success" Doesn't Mean Complete

**Context:** Keitaro Poller показывал status "success" но данные не записывались (Issue #186).

**Mistake:** Доверял статусу execution "success" без проверки executedNodes count.

**Reality:** Broken connection (`"type": "0"` вместо `"type": "main"`) заставил n8n пропустить узел. Workflow завершился успешно, но Loop Over Campaigns → Get Campaign Metrics никогда не выполнялся.

**Correct Approach:**
```javascript
// При анализе execution всегда проверять:
// 1. executedNodes count == expected nodes
// 2. Все critical nodes в списке executed
// 3. Данные в БД после успешного execution
```

**Rule:** Workflow execution "success" != все узлы выполнились. Всегда проверяй executedNodes count и данные в БД.

---

## Adding New Issues

При закрытии issue, обновите этот файл:

```markdown
### #XX: Short Title

**Component:** workflow_name (ID)
**Root Cause:** Краткое описание причины
**Resolution:** Что было сделано для исправления
**Prevention:** Как предотвратить в будущем (тест, check, pattern)
**Detection Query:** SQL для обнаружения проблемы (если применимо)
```
