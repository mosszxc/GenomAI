# n8n Test Workflow для GenomAI

**Версия:** v1.0  
**Статус:** REFERENCE  
**Назначение:** Тестовый workflow для проверки подключения к Supabase

## 🧪 Тестовый Workflow: "Test Supabase Connection"

### Описание

Простой workflow для проверки подключения к Supabase и доступа к схеме `genomai`.

### Структура Workflow

```
1. Manual Trigger (для ручного запуска)
   ↓
2. Supabase Node - Test Connection (проверка через Supabase API)
   ↓
3. Set Node - Format Response
   ↓
4. Return Response
```

### Конфигурация Nodes

#### 1. Manual Trigger
- **Type:** Manual Trigger
- **Settings:** Default

#### 2. Supabase Node - Test Connection
- **Type:** Supabase
- **Operation:** Get Many
- **Credential:** GenomAI Supabase API
- **Schema:** `genomai` (Use Custom Schema: enabled)
- **Table:** `event_log`
- **Purpose:** Проверка подключения через Supabase API (читает данные из таблицы)

#### 3. Set Node - Format Response
- **Fields:**
  - `status`: `success`
  - `tables_found`: `{{ $json.length }}`
  - `tables`: `{{ $json }}`
  - `message`: `Connection successful! Found {{ $json.length }} tables in genomai schema.`

#### 4. Return Response (Success)
- **Type:** Respond to Webhook / Set
- **Data:** Output from Set Node

### Ожидаемый результат

```json
{
  "status": "success",
  "records_found": 2,
  "sample_data": [
    {
      "id": "...",
      "event_type": "CreativeReferenceReceived",
      "entity_type": "creative",
      "occurred_at": "2025-12-21T..."
    }
  ],
  "message": "Supabase connection successful! Read 2 records from genomai.event_log."
}
```

## 🔧 Дополнительные тесты

### Тест 2: Проверка записи в event_log

**Supabase Node:**
- **Operation:** Create
- **Table:** `event_log`
- **Schema:** `genomai`
- **Data:**
```json
{
  "event_type": "ManualTestEvent",
  "entity_type": "test",
  "payload": {"manual_test": true},
  "idempotency_key": "manual-test-{{ $now }}"
}
```

### Тест 3: Проверка чтения из других таблиц

**Supabase Node:**
- **Operation:** Get Many
- **Table:** `creatives` (или любая другая)
- **Schema:** `genomai`

## 📝 Инструкция по созданию

1. Войдите в n8n: `https://kazamaqwe.app.n8n.cloud`
2. Перейдите в проект **Unighaz**
3. Создайте новый workflow: **Workflows** → **Add Workflow**
4. Назовите: `Test Supabase Connection` (без префикса, просто актуальное название)
4. Добавьте nodes согласно структуре выше
5. Настройте Postgres credential (см. N8N_SETUP.md)
6. Сохраните workflow
7. Запустите вручную (Manual Trigger)
8. Проверьте результат

## ✅ Критерии успеха

- ✅ Workflow выполняется без ошибок
- ✅ Supabase node успешно читает данные из `genomai.event_log`
- ✅ Credential настроен правильно
- ✅ Схема `genomai` доступна через Supabase API
- ✅ Запись в `event_log` через Supabase node успешна (опционально)

## 🐛 Troubleshooting

### Ошибка: "relation genomai.event_log does not exist"
- Проверьте, что миграции применены
- Убедитесь, что используете правильное имя таблицы в Supabase node
- Проверьте, что "Use Custom Schema" включен и указана схема `genomai`

### Ошибка: "permission denied" или "401 Unauthorized"
- Проверьте правильность Supabase API key
- Убедитесь, что используете правильный credential
- Проверьте, что API key имеет доступ к схеме `genomai` (может потребоваться настройка в Supabase Dashboard)

