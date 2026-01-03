# Known Issues & Resolutions

Документация известных проблем и их решений для предотвращения регрессий.

**Последнее обновление:** 2026-01-02

---

## Currently Open Issues

### Critical (Data Pipeline Broken)

| Issue | Title | Component | Status |
|-------|-------|-----------|--------|
| #209 | High error rates on idea_registry and decomposition workflows | n8n | INVESTIGATED - See below |
| #199 | Decomposition→Idea pipeline breaks - creatives stuck without idea linking | n8n | OPEN |
| #204 | Decomposed creative missing idea_id link | DB | OPEN |
| #184 | 2 creatives stuck in transcribed status without decomposition | n8n | OPEN |

#### #209 Investigation Results (2026-01-02)

**Reported Error Rates:** idea_registry_create 45% (9/20), creative_decomposition_llm 50% (10/20)

**Actual Root Cause:** The high error rates are **not workflow bugs** but upstream data quality issues:

| Error Type | Count | Root Cause |
|------------|-------|------------|
| TranscriptionFailed | 6 | Invalid Google Drive links returning HTML instead of video |
| HypothesisDeliveryFailed | 3 | Spy creatives without buyer_id |
| skipped_large_file | 7 | Files > 50MB (expected behavior) |

**Pipeline Success Rate (Last 30 days):**
- IdeaRegistered: 5 success
- CreativeDecomposed: 4 success
- TranscriptCreated: 4 success
- DecisionMade: 5 success

**Actual Workflow Error Rate:** ~5-10% (not 45-50%)

**TranscriptionFailed Details:**
```
"Transcoding failed. File does not appear to contain audio. File type is text/html"
```
This occurs when Google Drive share links return error pages (permissions, deleted files, expired links).

**Recommendations:**
1. Add URL validation before sending to transcription pipeline
2. Track `skipped_large_file` separately from errors
3. Handle spy creatives without buyer_id gracefully

**Status:** Root cause identified. No workflow code changes needed. Data quality issue.

### High (Data Integrity)

| Issue | Title | Component | Status |
|-------|-------|-----------|--------|
| #207 | Decision without decision_trace record | DB | OPEN |
| #205 | Avatars with invalid canonical_hash length | DB | OPEN |
| #203 | Decision values case mismatch: APPROVE vs approve | DB | OPEN |

### Medium (Metrics & Delivery)

| Issue | Title | Component | Status |
|-------|-------|-----------|--------|
| #208 | 2 stuck hypothesis deliveries | n8n | OPEN |
| #206 | Keitaro Poller metrics 11h stale | n8n | OPEN |
| #200 | 337 campaigns stuck in historical_import_queue with pending_video | DB | RESOLVED |

### Pending Implementation

| Issue | Title | Component | Status |
|-------|-------|-----------|--------|
| #192 | Use verticals[]/geos[] arrays instead of single values | API | OPEN |
| #174 | Create n8n Premise Generator workflow | n8n | OPEN |
| #172 | End-to-end Premise Layer validation | Test | OPEN |
| #166 | Create migration 021_premise_registry.sql | DB | OPEN |

---

## Critical Issues (Resolved)

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

### #200: 337 Campaigns Stuck in historical_import_queue (RESOLVED)

**Component:** `historical_import_queue` table, Historical Import pipeline
**Root Cause:** Historical campaigns from Keitaro had metrics but no video URLs. Without video, the full pipeline (creative → transcript → decomposition → idea → decision) cannot run.
**Symptoms:** 337 campaigns stuck with `pending_video` status for 3-6 days

**Resolution:**
1. Added `expired` status to `historical_import_queue_status_check` constraint (migration 023)
2. Updated 336 old campaigns (>5 days) to `expired` status
3. Preserved metrics data in expired records for potential future use

**Prevention:**
- Pipeline Health Monitor should auto-expire pending_video campaigns older than 7 days
- Consider filtering out campaigns without video during Historical Loader

**Detection Query:**
```sql
SELECT status, COUNT(*) FROM genomai.historical_import_queue GROUP BY status;
```

---

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

### #178: Spy Creative Registration - Invalid creative_id to Decomposition

**Component:** `Spy Creative Registration` (pL6C4j1uiJLfVRIi)
**Root Cause:** Node `Call Decomposition` made GET request without body instead of POST with `{creative_id, transcript_text, is_spy}`
**Symptoms:** `creative_decomposition_llm` received empty/undefined creative_id, causing UUID validation error

**Resolution:**
1. Changed method GET → POST
2. Added body with proper structure:
```json
{
  "creative_id": "$('Insert Spy Creative').first().json.id",
  "transcript_text": "from Fetch Transcript or fallback",
  "is_spy": true
}
```

**Prevention:**
- When calling webhooks that expect data, always verify: method=POST, sendBody=true, jsonBody set
- Run `n8n_validate_workflow` before closing issue

**Related:** #197 (incomplete fix), `creative_decomposition_llm` (mv6diVtqnuwr7qev)

---

### #202: Learning Loop Not Populating - Supabase GET Empty Array

**Component:** `Snapshot Creator` (Gii8l2XwnX43Wqr4)
**Root Cause:** `Check Snapshot Exists` (Supabase GET) returns 0 items when no record found → `If Not Exists` node never receives data → workflow stops silently
**Symptoms:**
- `daily_metrics_snapshot`: 0 records
- `outcome_aggregates`: 0 records
- `component_learnings`: 0 records
- Keitaro Poller shows 85+ `RawMetricsObserved` events but no downstream processing

**Resolution:**
1. Removed: `Check Snapshot Exists`, `If Not Exists`, `Skip Existing`, `Create Daily Snapshot`
2. Added: `Upsert Snapshot` (HTTP Request with `Prefer: resolution=merge-duplicates`)
3. Added: `Normalize Response` (Code node to extract first item from array)
4. Updated all downstream expression references
5. Added retry to Outcome Aggregator (3 attempts, 5s wait)

**Prevention:**
- Use UPSERT pattern instead of Check→If→Create
- Or use HTTP Request instead of Supabase node for empty array handling
- Always test with data that triggers the "not found" path

**Detection Query:**
```sql
-- Check if Snapshot Creator is working
SELECT COUNT(*) as snapshots, MAX(created_at) as latest
FROM genomai.daily_metrics_snapshot;

-- Compare with Keitaro Poller events
SELECT COUNT(*) as events FROM genomai.event_log
WHERE event_type = 'RawMetricsObserved';
```

---

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

### Check DB Constraints Before Code Fix

**Context:** Issue #189 - Decision values saved as lowercase instead of uppercase.

**Mistake:** Fixed code (`decision_type.lower()` → `.upper()`) without checking if DB constraint would block the new values.

**Reality:** `decisions_decision_check` constraint required lowercase values: `CHECK (decision IN ('approve', 'reject', 'defer'))`. Code fix would have failed at runtime.

**Correct Approach:**
```sql
-- Before any data format change, check constraints:
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'genomai.table_name'::regclass;

-- Then create migration that updates constraint + data together
```

**Rule:** Data format changes require checking constraints. Code fix + constraint migration must be applied together.

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

### Verify Fix Before Closing Issue

**Context:** Issue #178 was closed but fix was incomplete (Issue #197).

**Mistake:** Issue #178 "Spy Creative Registration URL fix" was marked closed without testing that the HTTP Request node actually worked.

**Reality:** Only `jsonBody` was set, but `url`, `method`, `sendHeaders`, `sendBody` were missing. Workflow validation would have caught: `Required property 'URL' cannot be empty`.

**Correct Approach:**
```bash
# Before closing ANY workflow issue:
1. n8n_validate_workflow - check for errors
2. n8n_test_workflow - execute and verify
3. Check DB for expected records
```

**Rule:** Never close workflow issue without: (1) validation passing, (2) test execution, (3) DB verification.

---

### Supabase GET Empty = Workflow Stops Silently

**Context:** Issue #202 - Learning Loop not populating tables despite Keitaro Poller working.

**Mistake:** Used pattern `Supabase GET → If (id not exists) → Create`. When GET returns 0 items, If node receives no data and workflow silently stops.

**Reality:** Supabase node GET operation returns **empty array** (not null/undefined) when no records found. n8n passes 0 items to next node → workflow ends without error.

**Correct Approach:**
```javascript
// WRONG - Check→If pattern with Supabase GET
Supabase GET → If Not Exists → Create
// Silent failure when record doesn't exist!

// CORRECT - UPSERT pattern with HTTP Request
HTTP Request (POST with Prefer: resolution=merge-duplicates) → Normalize Response → Continue
// Always returns data, handles insert/update automatically
```

**Rule:** For "create if not exists" logic, use UPSERT via HTTP Request instead of Check→If→Create with Supabase node. This anti-pattern is already documented above but keeps recurring.

---

### Check MCP Capabilities Before Asserting

**Context:** Пользователь спросил про запуск n8n workflow. Я ответил что нет инструмента для запуска.

**Mistake:** Видел частичный список MCP инструментов в системном промпте (search_nodes, validate_workflow, etc.) и предположил что это полный список.

**Reality:** n8n MCP имеет 19 инструментов, включая 13 n8n API tools. `n8n_test_workflow` существует и позволяет запускать workflows.

**Correct Approach:**
```bash
# Перед утверждением о capabilities MCP сервера:
mcp__n8n-mcp__tools_documentation()  # Получить полный список

# Только после этого утверждать что есть/нет
```

**Rule:** Не делать выводы о capabilities MCP без вызова `tools_documentation()`. Системный промпт показывает только часть инструментов.

---

### Hypothesis Factory Missing buyer_id Propagation

**Context:** Issue #222 - hypothesis застрял в delivery с reason "No buyer_id assigned".

**Mistake:** Workflow `hypothesis_factory_generate` создаёт hypothesis без buyer_id, хотя он есть в creative chain.

**Reality:** buyer_id хранится в `creatives.buyer_id`, но не копируется через цепочку:
```
creative.buyer_id → decomposed_creative → idea → hypothesis
```

**Correct Approach:**
```sql
-- В Hypothesis Factory добавить lookup:
SELECT c.buyer_id
FROM genomai.creatives c
JOIN genomai.decomposed_creatives dc ON c.id = dc.creative_id
WHERE dc.idea_id = :idea_id
```

**Rule:** При создании downstream записей (hypothesis, recommendation) всегда проверять что buyer_id propagates из source (creative).

**Related:** Issue #226 (fix pending)

---

### Test = Run Now, Not Check Old Results

**Context:** Issue #218 - проверял "работает ли workflow" глядя на старые результаты вместо запуска нового теста.

**Mistake:** Посмотрел `updated_at` в БД, увидел свежую запись от предыдущего запуска, сказал "тест пройден".

**Reality:** Это не тест. Тест = запустить сейчас → проверить результат после. Старые данные не доказывают что система работает сейчас.

**Correct Approach:**
```bash
# 1. Зафиксировать состояние ДО
SELECT MAX(updated_at) as before_test FROM table;

# 2. Запустить workflow
curl -X POST "webhook-url"

# 3. Подождать выполнения
sleep 15

# 4. Проверить состояние ПОСЛЕ
SELECT MAX(updated_at) as after_test FROM table;

# 5. Сравнить: after_test > before_test = PASS
```

**Rule:** Тест = действие + проверка результата. Смотреть на старые данные — не тест.

---

### External Service Domain Changes Break Silently

**Context:** Issue #218 - Keitaro Poller не работал 3+ дней, метрики устарели.

**Mistake:** Домен Keitaro (`uniaffburan.com`) изменился на `uniaffzhb.com`, но конфигурация в `genomai.keitaro_config` не была обновлена.

**Reality:** API возвращал 401 Unauthorized на старый домен. Workflow запускался по расписанию, получал ошибку, но система не алертила о проблеме.

**Correct Approach:**
```bash
# 1. При 401/403/5xx от внешних API - сначала проверить базовую доступность
curl -s -w "HTTP:%{http_code}" "https://domain.com/api/endpoint" -H "Api-Key: xxx"

# 2. Если домен недоступен - проверить актуальный домен у провайдера

# 3. Обновить конфиг в БД и протестировать
UPDATE genomai.keitaro_config SET domain = 'https://new-domain.com' WHERE is_active = true;
```

**Rule:** При ошибках авторизации внешних API - сначала проверить что домен не изменился. Добавить health check для external dependencies в Pipeline Health Monitor.

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
