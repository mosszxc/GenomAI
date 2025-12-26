# Known Issues & Resolutions

Документация известных проблем и их решений для предотвращения регрессий.

**Последнее обновление:** 2025-12-26

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
