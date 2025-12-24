# Render Migration - Изменения в процессах и workflows

**Дата создания:** 2025-01-22  
**Статус:** ✅ Актуально  
**Приоритет:** Высокий

## 📋 Executive Summary

После миграции Decision Engine на Render изменились следующие процессы:

1. **STEP 04 (Decision Engine)** — требует обновления workflow для вызова Render API
2. **STEP 03 (Idea Registry)** — не требует изменений, но эмитит событие, которое триггерит Decision Engine
3. **STEP 01, 02, 07** — не требуют изменений (не используют Decision Engine)

---

## 🔄 Изменения в процессах

### Процесс 1: Decision Engine (STEP 04)

**До миграции:**
```
IdeaRegistered Event
    ↓
Load Idea (Supabase)
    ↓
Idea Found Check (IF)
    ↓
Hard Constraints Check (Function node)
    ↓
Decision Output
    ↓
Persist Decision (Supabase)
    ↓
Persist Decision Trace (Supabase)
    ↓
Emit DecisionMade Event
```

**После миграции:**
```
IdeaRegistered Event
    ↓
Load Idea (Supabase)
    ↓
Load System State (Supabase)
    ↓
Load Config (genomai.config) - API URL и ключ
    ↓
HTTP Request → Render API (POST /api/decision)
    ↓
Handle Response (IF node)
    ↓
Emit DecisionMade Event (если success)
```

**Ключевые изменения:**
- ✅ Логика Decision Engine перенесена на Render
- ✅ n8n workflow теперь вызывает Render API через HTTP Request
- ✅ Decision и Decision Trace сохраняются Render API (не n8n)
- ✅ Нужна настройка config в БД для API URL и ключа

---

## 📝 Workflows, требующие изменений

### 1. `decision_engine_mvp` (STEP 04)

**Workflow ID:** `YT2d7z5h9bPy1R4v` (старый) или новый ID после обновления

**✅ ОПТИМИЗИРОВАНО:** Упрощенный workflow - только загрузка config и вызов API.

**Что нужно изменить:**

#### 1.1 Добавить узел "Load Config"

**Перед вызовом Render API:**

- **Node:** Supabase
- **Operation:** `getAll`
- **Use Custom Schema:** ✅ enabled
- **Schema:** `genomai`
- **Table:** `={{ "config" }}`
- **Filters:** Нет (загружаем все конфигурации)

**✅ ОПТИМИЗИРОВАНО:** Не нужно загружать Idea и System State - Render API сделает это сам.

#### 1.2 Добавить узел "Extract Config Values" (оптимизировано)

**Node:** Function

**Code (оптимизированный):**
```javascript
const allItems = $input.all();
const config = {};

allItems.forEach(item => {
  const key = item.json.key;
  const value = item.json.value;
  config[key] = value;
});

return [{
  json: {
    api_url: config.decision_engine_api_url || 'https://genomai.onrender.com',
    api_key: config.decision_engine_api_key || 'REPLACE_WITH_YOUR_API_KEY',
    // ОПТИМИЗИРОВАНО: Передаем только idea_id, Render API загрузит все остальное
    idea_id: $('Event Trigger').first().json.idea_id
  }
}];
```

**✅ Преимущества:**
- Меньше запросов к Supabase (3 запроса → 1 запрос)
- Проще workflow (убраны узлы Load Idea и Load System State)
- Меньше дублирования логики

#### 1.3 Заменить локальную логику на HTTP Request (оптимизировано)

**Удалить:**
- ❌ "Load Idea" (Supabase Select)
- ❌ "Load System State" (Supabase Select)
- ❌ "Idea Found Check" (IF node)
- ❌ "Hard Constraints Check" (Function node)
- ❌ "Persist Decision" (Supabase Insert)
- ❌ "Persist Decision Trace" (Supabase Insert)

**Добавить:**
- ✅ "Call Render API" (HTTP Request node)

**HTTP Request Node (оптимизированный):**
- **Method:** POST
- **URL:** `={{ $json.api_url }}/api/decision`
- **Headers:**
  - `Content-Type`: `application/json`
  - `Authorization`: `Bearer {{ $json.api_key }}`
- **Body (оптимизированный):**
```json
{
  "idea_id": "={{ $json.idea_id }}"
}
```

**✅ ОПТИМИЗИРОВАНО:** Передаем только `idea_id`. Render API автоматически загрузит:
- Idea из `genomai.ideas`
- System State (количество активных идей)
- Fatigue State (если нужно)
- Death Memory (если нужно)

- **onError:** `continueRegularOutput`

#### 1.4 Обновить обработку ответа

**Node:** IF (typeVersion: 2.3)

**Проверка успешности:**
```json
{
  "conditions": {
    "combinator": "and",
    "conditions": [
      {
        "id": "success-check",
        "leftValue": "={{ $json.success }}",
        "rightValue": true,
        "operator": {
          "type": "boolean",
          "operation": "equals"
        }
      }
    ]
  }
}
```

**Выходы:**
- **TRUE (output[0]):** → Emit DecisionMade Event
- **FALSE (output[1]):** → Emit DecisionAborted Event

**Примечание:** Decision и Decision Trace уже сохранены Render API в Supabase, поэтому не нужно их сохранять в n8n.

---

## ✅ Workflows, НЕ требующие изменений

### 1. `creative_ingestion_webhook` (STEP 01)

**Workflow ID:** `dvZvUUmhtPzYOK7X`

**Статус:** ✅ Не требует изменений

**Причина:** Не использует Decision Engine, работает независимо.

---

### 2. `creative_decomposition_llm` (STEP 02)

**Workflow name:** `creative_decomposition_llm`

**Статус:** ✅ Не требует изменений

**Причина:** Не использует Decision Engine, работает независимо.

---

### 3. `idea_registry_create` (STEP 03)

**Workflow name:** `idea_registry_create`

**Статус:** ✅ Не требует изменений

**Причина:** Только эмитит событие `IdeaRegistered`, которое триггерит Decision Engine. Сама логика не изменилась.

**Примечание:** Убедитесь, что workflow эмитит событие `IdeaRegistered` с полем `idea_id`.

---

### 4. `Outcome Ingestion Keitaro` (STEP 07)

**Workflow ID:** `zMHVFT2rM7PpTiJj`

**Статус:** ✅ Не требует изменений

**Причина:** Не использует Decision Engine, работает независимо.

---

## 🔧 Настройка конфигурации

### 1. Создать таблицу config (если не создана)

**Файл:** `infrastructure/migrations/create_config_table.sql`

**Проверка:**
```sql
SELECT * FROM genomai.config WHERE key IN ('decision_engine_api_url', 'decision_engine_api_key');
```

### 2. Настроить API URL и ключ

**API URL (публичный):**
```sql
INSERT INTO genomai.config (key, value, description, is_secret)
VALUES ('decision_engine_api_url', 'https://genomai.onrender.com', 'Decision Engine API URL', false)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

**API Key (секрет):**
```sql
INSERT INTO genomai.config (key, value, description, is_secret)
VALUES ('decision_engine_api_key', 'YOUR_ACTUAL_API_KEY_HERE', 'Decision Engine API Key for authentication', true)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

**⚠️ ВАЖНО:** Замените `YOUR_ACTUAL_API_KEY_HERE` на реальный API ключ из Render.

**Как получить API ключ:**
1. Откройте Render Dashboard
2. Перейдите в ваш сервис `decision-engine-service`
3. Откройте Environment Variables
4. Найдите переменную `API_KEY` (или создайте её)
5. Скопируйте значение

---

## 📊 Сравнение: До и После

### До миграции

| Компонент | Реализация |
|-----------|------------|
| Decision Engine Logic | n8n Function node |
| Decision Storage | n8n Supabase Insert |
| Decision Trace Storage | n8n Supabase Insert |
| Тестируемость | Ограничена (n8n workflow) |
| Версионирование | Через n8n workflow версии |
| Масштабируемость | Ограничена n8n планом |

### После миграции

| Компонент | Реализация |
|-----------|------------|
| Decision Engine Logic | Render Python/FastAPI |
| Decision Storage | Render API → Supabase |
| Decision Trace Storage | Render API → Supabase |
| Тестируемость | ✅ Unit-тесты, Integration-тесты |
| Версионирование | ✅ Git, версионирование кода |
| Масштабируемость | ✅ Независимое масштабирование |

---

## 🚀 Процесс обновления workflow

### Шаг 1: Подготовка

1. ✅ Убедитесь, что Render сервис развернут и работает
2. ✅ Проверьте health check: `GET https://genomai.onrender.com/health`
3. ✅ Настройте config в БД (API URL и ключ)

### Шаг 2: Обновление workflow (оптимизировано)

1. Откройте workflow `decision_engine_mvp` в n8n
2. Добавьте узлы:
   - "Load Config" (Supabase)
   - "Extract Config Values" (Function)
   - "Call Render API" (HTTP Request)
3. Удалите узлы:
   - "Load Idea" (Supabase Select) ✅ ОПТИМИЗИРОВАНО
   - "Load System State" (Supabase Select) ✅ ОПТИМИЗИРОВАНО
   - "Idea Found Check" (IF)
   - "Hard Constraints Check" (Function)
   - "Persist Decision" (Supabase Insert)
   - "Persist Decision Trace" (Supabase Insert)
4. Обновите обработку ответа (IF node)
5. Сохраните workflow

**✅ Преимущества оптимизации:**
- Меньше узлов в workflow (проще поддерживать)
- Меньше запросов к Supabase (быстрее выполнение)
- Меньше дублирования логики (Render API сам загружает данные)

### Шаг 3: Тестирование

1. Запустите workflow через Manual Trigger
2. Проверьте, что:
   - ✅ Config загружается корректно
   - ✅ HTTP Request вызывается с правильными параметрами
   - ✅ Decision создаётся в Supabase
   - ✅ Decision Trace создаётся в Supabase
   - ✅ Событие `DecisionMade` эмитится

### Шаг 4: Валидация

1. Проверьте логи Render сервиса
2. Проверьте данные в Supabase:
   ```sql
   SELECT * FROM genomai.decisions ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM genomai.decision_traces ORDER BY created_at DESC LIMIT 5;
   ```
3. Проверьте события в event_log:
   ```sql
   SELECT * FROM genomai.event_log WHERE event_type = 'DecisionMade' ORDER BY occurred_at DESC LIMIT 5;
   ```

---

## ⚠️ Важные замечания

### 1. Обработка ошибок

**Если Render API недоступен:**
- Workflow должен эмитить событие `DecisionAborted`
- Не должно быть silent failures
- Логи должны содержать причину ошибки

### 2. Retry механизм

**Рекомендуется:**
- Настроить retry в HTTP Request node (3 попытки)
- Exponential backoff между попытками
- Логирование всех попыток

### 3. Мониторинг

**Что мониторить:**
- Время ответа Render API
- Количество успешных/неуспешных решений
- Ошибки в логах Render
- Ошибки в n8n workflow executions

---

## 📚 Связанные документы

- `DECISION_ENGINE_RENDER_MIGRATION.md` — полный план миграции
- `04_decision_engine_playbook.md` — обновленный playbook
- `RENDER_MCP_INTRO.md` — интро по Render MCP
- `RENDER_MCP_SETUP.md` — настройка Render MCP

---

## ✅ Чеклист миграции

- [ ] Render сервис развернут и работает
- [ ] Health check проходит: `GET /health`
- [ ] Config в БД настроен (API URL и ключ)
- [ ] Workflow `decision_engine_mvp` обновлен
- [ ] Тестирование пройдено (Manual Trigger)
- [ ] Проверка данных в Supabase (decisions, decision_traces)
- [ ] Проверка событий (DecisionMade)
- [ ] Мониторинг настроен
- [ ] Документация обновлена

---

**Следующий шаг:** Обновите workflow `decision_engine_mvp` согласно инструкциям выше.

