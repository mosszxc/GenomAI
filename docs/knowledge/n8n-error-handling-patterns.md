# n8n Error Handling Patterns

## onError Options

| Option | Behaviour |
|--------|-----------|
| `stopWorkflow` | Default. Workflow stops on error. |
| `continueRegularOutput` | Error ignored, continues with empty/error data in main output. |
| `continueErrorOutput` | Routes to error output (red connector). |

## Pattern: Handle HTTP Conflict (409)

При INSERT в Supabase с UNIQUE constraint — 409 Conflict.

```
HTTP Request (onError: continueRegularOutput)
    → IF ($json.id exists)
        ├─ true → success flow
        └─ false → handle duplicate/error
```

**Key:** Supabase returns `{"id": "uuid"}` on success, `{"code": "23505"}` on conflict.

## Pattern: Check Duplicate Before Insert

Альтернатива — проверить перед INSERT:

```
HTTP Request (SELECT where video_url=X AND tracker_id=Y)
    → IF (result.length > 0)
        ├─ true → already exists
        └─ false → INSERT
```

**Trade-off:** +1 запрос, но точнее определяет дубликат.

## Expression Format

Mixed literal + expression REQUIRES `=` prefix:

```javascript
// WRONG
"text": "Hello {{ $json.name }}"

// CORRECT
"text": "=Hello {{ $json.name }}"
```

## n8n_update_partial_workflow

Для добавления error handling:

```javascript
{type: "updateNode", nodeName: "HTTP Request", updates: {onError: "continueRegularOutput"}}
```

Для IF node routing:

```javascript
{type: "addConnection", source: "IF", target: "Success", branch: "true"}
{type: "addConnection", source: "IF", target: "Error", branch: "false"}
```

## Debugging Lessons (Issue #178)

### 1. Системный анализ перед фиксом

**Проблема:** Инкрементальные фиксы создают каскад новых ошибок.

**Правило:** Перед исправлением:
1. Прочитать весь workflow (`mode: "full"`)
2. Проверить все целевые endpoints (URL, method, expected payload)
3. Проверить data flow — какие данные приходят на каждую ноду

### 2. Partial Update сбрасывает параметры

**Проблема:**
```javascript
// Обновил только method
updateNode("Call Transcription", {parameters: {method: "POST"}})
// Результат: URL стал пустым!
```

**Правило:** При partial update передавать ВСЕ критичные параметры:
```javascript
updateNode("Call Transcription", {
  parameters: {
    method: "POST",
    url: "https://...",  // обязательно!
    sendBody: true,
    jsonBody: "..."
  }
})
```

### 3. Проверять output перед написанием expression

**Проблема:**
```javascript
$('Insert Spy Creative').first().json[0].id  // предполагал массив
$('Insert Spy Creative').first().json.id     // реальность — объект
```

**Правило:** Перед написанием expression — проверить реальный output ноды через execution details.

### 4. Проверять структуру входных данных

**Проблема:**
```javascript
routerData.text       // ожидал
routerData.message.text  // реальность
```

**Правило:** Смотреть на output предыдущей ноды, не предполагать структуру.

### 5. Проверять целевой endpoint

**Проблема:** Изменил домен, но не проверил:
- Правильный ли path?
- Какой HTTP method ожидает webhook?

**Правило:** Перед вызовом webhook — открыть целевой workflow и проверить:
- Webhook path
- HTTP method (GET/POST)
- Ожидаемые headers

### Чеклист перед изменением workflow

```markdown
- [ ] Прочитал весь workflow (mode: "full")
- [ ] Проверил output всех upstream нод
- [ ] Проверил целевые endpoints (path, method)
- [ ] При partial update передаю ВСЕ критичные параметры
- [ ] Тестирую после КАЖДОГО изменения
```
