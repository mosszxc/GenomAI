# Анализ различий: Актуальный workflow vs Валидированный

**Дата:** 2025-12-21  
**Workflow:** `creative_decomposition_llm` (ID: `mv6diVtqnuwr7qev`)

## 🔍 Критическая разница

### Актуальный рабочий workflow использует:

```json
// Supabase nodes
{
  "useCustomSchema": true,
  "schema": "genomai",
  "tableId": "transcripts",  // ← ПРОСТАЯ СТРОКА!
  "fieldsUi": {
    "fieldValues": [...]
  }
}
```

### Я пытался "исправить" на:

```json
// Supabase nodes
{
  "useCustomSchema": true,
  "schema": "genomai",
  "resource": "row",  // ← ДОБАВИЛ
  "operation": "create",  // ← ДОБАВИЛ
  "tableId": {  // ← ИЗМЕНИЛ НА ОБЪЕКТ!
    "__rl": true,
    "value": "transcripts",
    "mode": "name"
  },
  "dataToSend": "defineBelow",  // ← ДОБАВИЛ
  "fieldsUi": {
    "fieldValues": [...]
  }
}
```

## ❌ Что я делал не так

### 1. **Пытался "исправить" то, что уже работало**

Актуальный workflow использует **простой строковый формат** для `tableId`:
- `"tableId": "transcripts"` ✅ **РАБОТАЕТ**

Я пытался заменить на **объектный формат**:
- `"tableId": {"__rl": true, "value": "transcripts", "mode": "name"}` ❌ **НЕ НУЖНО**

### 2. **Добавлял параметры, которые не нужны**

Актуальный workflow **НЕ использует**:
- `resource: "row"` ❌
- `operation: "create"` ❌
- `dataToSend: "defineBelow"` ❌

Эти параметры могут быть **неявными** или **автоматически определяться** n8n на основе других параметров.

### 3. **Не проверял актуальный формат перед "исправлением"**

Я должен был:
1. ✅ Прочитать актуальный workflow
2. ✅ Понять, какой формат используется
3. ✅ Проверить, работает ли он
4. ❌ **НЕ пытаться "исправить" то, что уже работает**

## 📋 Детальное сравнение

### Persist Transcript node

**Актуальный (рабочий):**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "tableId": "transcripts",
  "fieldsUi": {
    "fieldValues": [
      {"fieldId": "id", "fieldValue": "={{ $generateUUID() }}"},
      {"fieldId": "creative_id", "fieldValue": "={{ $json.creative_id }}"},
      {"fieldId": "version", "fieldValue": "=1"},
      {"fieldId": "transcript_text", "fieldValue": "={{ $json.transcript_text }}"}
    ]
  }
}
```

**Что я пытался сделать:**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "resource": "row",  // ← ЛИШНЕЕ
  "operation": "create",  // ← ЛИШНЕЕ
  "tableId": {  // ← ИЗМЕНИЛ ФОРМАТ
    "__rl": true,
    "value": "transcripts",
    "mode": "name"
  },
  "dataToSend": "defineBelow",  // ← ЛИШНЕЕ
  "fieldsUi": {...}
}
```

### Persist Decomposed Creative node

**Актуальный (рабочий):**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "tableId": "decomposed_creatives",
  "fieldsUi": {...}
}
```

**Что я пытался сделать:**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "resource": "row",  // ← ЛИШНЕЕ
  "operation": "create",  // ← ЛИШНЕЕ
  "tableId": {  // ← ИЗМЕНИЛ ФОРМАТ
    "__rl": true,
    "value": "decomposed_creatives",
    "mode": "name"
  },
  "dataToSend": "defineBelow",  // ← ЛИШНЕЕ
  "fieldsUi": {...}
}
```

### Emit TranscriptCreated node

**Актуальный (рабочий):**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "tableId": "event_log",
  "fieldsUi": {...}
}
```

**Что я пытался сделать:**
```json
{
  "useCustomSchema": true,
  "schema": "genomai",
  "resource": "row",  // ← ЛИШНЕЕ
  "operation": "create",  // ← ЛИШНЕЕ
  "tableId": {  // ← ИЗМЕНИЛ ФОРМАТ
    "__rl": true,
    "value": "event_log",
    "mode": "name"
  },
  "dataToSend": "defineBelow",  // ← ЛИШНЕЕ
  "fieldsUi": {...}
}
```

## 🎯 Правильный подход

### ✅ ЧТО НУЖНО ДЕЛАТЬ:

1. **Сначала прочитать актуальный workflow**
   - Использовать `n8n_get_workflow` с `mode: "full"`
   - Изучить реальную структуру параметров

2. **Понять, какой формат используется**
   - Проверить формат `tableId` (строка или объект?)
   - Проверить наличие `resource`, `operation`, `dataToSend`

3. **Проверить, работает ли workflow**
   - Проверить последние executions
   - Проверить данные в БД
   - Убедиться, что workflow действительно работает

4. **НЕ пытаться "исправить" то, что уже работает**
   - Если workflow работает с простым форматом - оставить его
   - Если есть ошибки - тогда исправлять

### ❌ ЧТО НЕ НУЖНО ДЕЛАТЬ:

1. **Не добавлять параметры "на всякий случай"**
   - Если `resource` и `operation` не указаны, но workflow работает - не добавлять их

2. **Не менять формат без необходимости**
   - Если `tableId` - строка и работает - не менять на объект

3. **Не "исправлять" рабочий workflow**
   - Если workflow работает - не трогать его

## 🔍 Почему я ошибался

### Источник ошибки:

Я опирался на **правила из `.cursor/rules/n8n-workflow-patterns.mdc`**, которые говорят:

> "Всегда использовать объектный формат для `tableId`: `{"__rl": true, "value": "table_name", "mode": "name"}`"

Но эти правила были написаны на основе **другого workflow** (`creative_ingestion_webhook`), который использует объектный формат для `getAll` операций.

### Разница между операциями:

- **`getAll` операция** (в `creative_ingestion_webhook`):
  - Требует объектный формат: `{"__rl": true, "value": "creatives", "mode": "name"}`
  - Используется для фильтрации

- **`create` операция** (в `creative_decomposition_llm`):
  - Может работать с простым строковым форматом: `"transcripts"`
  - n8n автоматически определяет операцию по наличию `fieldsUi`

## 📝 Выводы

1. **Актуальный workflow работает правильно** с простым строковым форматом `tableId`
2. **Я пытался "исправить" то, что не требовало исправления**
3. **Правила в `.cursor/rules/n8n-workflow-patterns.mdc` не универсальны** - они описывают один конкретный случай
4. **Нужно всегда проверять актуальный формат перед изменениями**

## ✅ Правило на будущее

**ПЕРЕД ЛЮБЫМИ ИЗМЕНЕНИЯМИ WORKFLOW:**

1. ✅ Прочитать актуальный workflow через `n8n_get_workflow`
2. ✅ Проверить последние executions
3. ✅ Убедиться, что workflow работает
4. ✅ Понять, какой формат используется
5. ✅ **НЕ менять то, что уже работает**

**НИКОГДА НЕ МЕНЯТЬ РАБОЧИЙ WORKFLOW БЕЗ ПРОВЕРКИ АКТУАЛЬНОГО ФОРМАТА!**


