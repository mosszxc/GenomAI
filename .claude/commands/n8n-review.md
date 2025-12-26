# n8n Workflow Review

> **Note:** Для валидации всего процесса используй `/valid {process}`

Проверь n8n workflow на типичные ошибки и анти-паттерны.

## Входные данные

Workflow ID: $ARGUMENTS (обязательно)

## Инструкции

### 1. Загрузи workflow

```
mcp__n8n-mcp__n8n_get_workflow(id: $ARGUMENTS, mode: "full")
```

### 2. Проверь на известные проблемы

#### 2.1 Check→If Anti-pattern (КРИТИЧНО)
**Проблема:** Supabase `getAll` → If node → Create/Update. Когда getAll возвращает пустой массив, downstream nodes не получают данные.

**Как найти:**
- Ищи паттерн: Supabase(getAll) → If → Supabase(create/update)
- If node проверяет `$json.id ? true : false` или подобное

**Решение:**
- Обойти If node, использовать Supabase create напрямую с `onError: continueRegularOutput`
- Или добавить прямое соединение от триггера к create node

#### 2.2 SplitInBatches неправильный output
**Проблема:** SplitInBatches имеет 2 выхода:
- Output 0 = "done" (когда все batch обработаны)
- Output 1 = "loop" (для обработки каждого item)

**Как найти:**
- Проверь connections от SplitInBatches
- Если processing node подключен к output 0 — это ошибка

**Решение:**
- Подключить processing node к output 1 (loop)

#### 2.3 Неправильный webhook URL/path
**Проблема:** HTTP Request вызывает webhook другого workflow с неправильным:
- Host (unighaz vs kazamaqwe)
- Path (learning-loop vs learning-loop-v2)

**Как найти:**
- Проверь все HTTP Request nodes
- Сравни URL с реальными webhook paths других workflows

**Решение:**
- Исправить URL на правильный host: `kazamaqwe.app.n8n.cloud`
- Проверить webhook path в целевом workflow

#### 2.4 $env заблокирован в n8n Cloud
**Проблема:** `$env.VARIABLE` не работает в n8n Cloud (заблокировано)

**Как найти:**
- Ищи `$env.` в expressions

**Решение:**
- Загружать конфиг из Supabase `genomai.config` таблицы
- Или использовать Supabase credentials

#### 2.5 HTTP Request без method/body после partial update
**Проблема:** При n8n_update_partial_workflow обновление URL может сбросить method на GET и убрать body

**Как найти:**
- HTTP Request node с sendBody: false но вызывает webhook

**Решение:**
- Всегда проверять полную конфигурацию HTTP Request после update
- Включать method, sendBody, jsonBody в partial update

#### 2.6 Supabase Update без filter (КРИТИЧНО)
**Проблема:** Supabase update node требует `filters.conditions` — без них ошибка "At least one select condition must be defined"

**Как найти:**
- Supabase node с `operation: "update"`
- Проверить наличие `filters.conditions` массива

**Решение:**
```json
"filters": {
  "conditions": [
    {"keyName": "id", "condition": "eq", "keyValue": "={{ $json.id }}"}
  ]
}
```

#### 2.7 Missing Credentials
**Проблема:** Nodes без credentials падают с "credentials not found"

**Как найти:**
- Проверить все Supabase, Telegram, HTTP nodes
- Должен быть `credentials: { supabaseApi: { id: "...", name: "..." } }`

**Решение:**
- Добавить credentials используя ID из рабочих nodes
- Supabase: `RNItSRYOCypd9H1a` / Telegram: `06SWHhdUxiQNwDWD`

#### 2.8 If Node Connection (branch naming)
**Проблема:** n8n partial update для If node требует `branch: "true"/"false"`, не `sourceIndex`

**Как найти:**
- If node в workflow
- Connections используют index вместо branch name

**Решение:**
```json
{
  "type": "addConnection",
  "from": "Check Buyer",
  "to": "Load Buyer",
  "branch": "true"   // НЕ sourceIndex: 0
}
```

#### 2.9 Null/Undefined в expressions
**Проблема:** `={{ $json.field }}` падает если field = null

**Как найти:**
- Expressions без fallback
- Nodes после условных branch

**Решение:**
- Добавить Check node перед использованием
- Или fallback: `={{ $json.field || 'default' }}`

### 3. Выведи результат

```markdown
## Workflow Review: [name]

### Статус: [OK / ISSUES FOUND]

### Найденные проблемы

| # | Тип | Node | Описание | Fix |
|---|-----|------|----------|-----|
| 1 | Anti-pattern | node_name | описание | как исправить |

### Рекомендации
- рекомендация 1
- рекомендация 2

### Структура workflow
[описание flow]
```

### 4. Предложи исправления

Если найдены проблемы, спроси:
"Хотите применить исправления автоматически? (y/n)"

При согласии используй `n8n_update_partial_workflow` для исправления.

## Примеры вызова

```
/n8n-review 0TrVJOtHiNEEAsTN   # проверить Keitaro Poller
/n8n-review 243QnGrUSDtXLjqU   # проверить Outcome Aggregator
```
