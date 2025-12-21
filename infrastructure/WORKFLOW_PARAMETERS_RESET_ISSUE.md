# Проблема: Параметры workflow "слетают" при обновлении

**Дата:** 2025-12-21  
**Проблема:** При обновлении workflow через API параметры nodes "слетают" (исчезают)

## 🔍 Причина проблемы

### Основная причина: Частичное обновление через `update_partial_workflow`

**Проблема:**  
Когда используется `n8n_update_partial_workflow` с операцией `updateNode`, n8n API может **заменять** все параметры node на указанные, а не **объединять** их с существующими.

**Пример:**
```javascript
// ❌ ПЛОХО: Обновляем только один параметр
{
  "type": "updateNode",
  "nodeId": "persist-transcript-1",
  "updates": {
    "parameters": {
      "useCustomSchema": true  // Только один параметр!
    }
  }
}
```

**Результат:**  
n8n может **удалить** все остальные параметры (`schema`, `resource`, `operation`, `tableId`, `fieldsUi`), оставив только `useCustomSchema`.

### Почему это происходит?

1. **n8n API интерпретирует `parameters` как полную замену**
   - Если указан `parameters: { useCustomSchema: true }`
   - n8n может заменить ВСЕ параметры на только этот один
   - Вместо объединения с существующими

2. **Отсутствие явного указания всех параметров**
   - При обновлении нужно указывать **ВСЕ** параметры node
   - Нельзя обновлять только часть параметров

3. **Проблема с вложенными объектами**
   - `tableId` - это объект `{__rl: true, value: "...", mode: "name"}`
   - `fieldsUi` - это объект `{fieldValues: [...]}`
   - При частичном обновлении эти объекты могут быть потеряны

## 📋 Что именно "слетает"

### 1. Supabase nodes теряют:
- ❌ `useCustomSchema`
- ❌ `schema`
- ❌ `resource`
- ❌ `operation`
- ❌ `tableId` (объект)
- ❌ `dataToSend`
- ❌ `fieldsUi` (объект с массивом)

### 2. LLM nodes теряют:
- ❌ `prompt` (объект с массивом messages)
- ❌ `resource`
- ❌ `operation`
- ❌ `model`

### 3. Event log nodes теряют:
- ❌ `useCustomSchema`
- ❌ `schema`
- ❌ `resource`
- ❌ `operation`
- ❌ `tableId`
- ❌ `dataToSend`
- ❌ `fieldsUi`

## ✅ Решение

### Правило 1: Всегда указывать ВСЕ параметры при обновлении

**НЕПРАВИЛЬНО:**
```javascript
// Обновляем только useCustomSchema
{
  "type": "updateNode",
  "nodeId": "persist-transcript-1",
  "updates": {
    "parameters": {
      "useCustomSchema": true
    }
  }
}
```

**ПРАВИЛЬНО:**
```javascript
// Указываем ВСЕ параметры
{
  "type": "updateNode",
  "nodeId": "persist-transcript-1",
  "updates": {
    "parameters": {
      "useCustomSchema": true,
      "schema": "genomai",
      "resource": "row",
      "operation": "create",
      "tableId": {
        "__rl": true,
        "value": "transcripts",
        "mode": "name"
      },
      "dataToSend": "defineBelow",
      "fieldsUi": {
        "fieldValues": [
          {"fieldId": "id", "fieldValue": "={{ $generateUUID() }}"},
          {"fieldId": "creative_id", "fieldValue": "={{ $json.creative_id }}"},
          {"fieldId": "version", "fieldValue": "=1"},
          {"fieldId": "transcript_text", "fieldValue": "={{ $json.transcript_text }}"}
        ]
      }
    }
  }
}
```

### Правило 2: Использовать `update_full_workflow` для полного обновления

**Если нужно обновить несколько nodes:**
- Использовать `n8n_update_full_workflow` с полной структурой workflow
- Это гарантирует, что все параметры сохранятся

### Правило 3: Сначала читать текущее состояние, потом обновлять

**Процесс:**
1. Прочитать текущий workflow через `n8n_get_workflow` с `mode: "full"`
2. Извлечь все параметры из nodes
3. Обновить только нужные параметры
4. Указать ВСЕ параметры при обновлении

## 🔧 Рекомендуемый процесс обновления

### Шаг 1: Прочитать текущее состояние
```javascript
const workflow = await n8n_get_workflow({id: "mv6diVtqnuwr7qev", mode: "full"});
const node = workflow.nodes.find(n => n.id === "persist-transcript-1");
const currentParams = node.parameters; // Сохранить все текущие параметры
```

### Шаг 2: Обновить только нужные параметры
```javascript
const updatedParams = {
  ...currentParams,  // Сохранить все существующие
  useCustomSchema: true,  // Обновить только нужное
  schema: "genomai"
};
```

### Шаг 3: Обновить node с ВСЕМИ параметрами
```javascript
await n8n_update_partial_workflow({
  id: "mv6diVtqnuwr7qev",
  operations: [{
    type: "updateNode",
    nodeId: "persist-transcript-1",
    updates: {
      parameters: updatedParams  // ВСЕ параметры, не только новые
    }
  }]
});
```

## 🎯 Итог

**Проблема:**  
n8n API при частичном обновлении может заменять все параметры на указанные, а не объединять их.

**Решение:**  
✅ Всегда указывать **ВСЕ** параметры node при обновлении  
✅ Сначала читать текущее состояние  
✅ Сохранять существующие параметры  
✅ Обновлять только нужные поля  

**Альтернатива:**  
✅ Использовать `n8n_update_full_workflow` для полного обновления workflow

## 📝 Чеклист перед обновлением node

- [ ] Прочитан текущий workflow через `n8n_get_workflow` с `mode: "full"`
- [ ] Извлечены все параметры из node
- [ ] Сохранены все существующие параметры
- [ ] Обновлены только нужные параметры
- [ ] При обновлении указаны **ВСЕ** параметры (старые + новые)
- [ ] Проверен результат через `n8n_validate_workflow`


