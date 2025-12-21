# Тестовые Payload'ы

**Версия:** v1.0  
**Назначение:** Реальные тестовые сценарии для проверки системы

## 📋 Сценарии для STEP 01 — Ingestion

### ✅ 1. Happy Path (`happy_path.json`)

**Назначение:** Проверка успешного ingestion валидного креатива

**Payload:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ✅ Creative создан в `genomai.creatives`
- ✅ Событие `CreativeReferenceReceived` записано в `event_log`
- ✅ Событие `CreativeRegistered` записано в `event_log`
- ✅ HTTP 200/201
- ✅ Возвращается `creative_id`

**Проверки:**
- Creative существует в БД
- 2 события в event_log
- `status = 'registered'`
- `source_type = 'user'`

---

### 🔄 2. Idempotency (`idempotency.json`)

**Назначение:** Проверка идемпотентности — повторный ingestion того же креатива

**Payload:** (тот же, что и `happy_path.json`)
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ✅ Дубль НЕ создаётся
- ✅ Возвращается существующий `creative_id`
- ✅ Событие `CreativeRegistered` эмитится (но creative не создаётся заново)
- ✅ HTTP 200 (не 201)

**Проверки:**
- Количество creatives с такими `video_url` + `tracker_id` = 1
- Возвращённый `creative_id` совпадает с первым запросом
- В event_log нет дублей событий

**📌 Критично:** Повтор ≠ ошибка!

---

### ⚠️ 3. Edge Case: Один video_url, разные tracker_id (`edge_same_video_different_tracker.json`)

**Назначение:** Проверка, что один video_url с разными tracker_id создаёт разные creatives

**Payload 1:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-111111",
  "source_type": "user"
}
```

**Payload 2:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-222222",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ✅ Создаются 2 разных creative
- ✅ У них разные `creative_id`
- ✅ Оба имеют одинаковый `video_url`
- ✅ У них разные `tracker_id`

**Проверки:**
- COUNT(*) WHERE video_url = '...' = 2
- Все creative_id уникальны
- UNIQUE constraint (video_url, tracker_id) работает корректно

**📌 Важно:** Это не дубль! Разные tracker_id = разные креативы.

---

### ⚠️ 4. Edge Case: Разные video_url, один tracker_id (`edge_different_video_same_tracker.json`)

**Назначение:** Проверка, что разные video_url с одним tracker_id создают разные creatives

**Payload 1:**
```json
{
  "video_url": "https://example.com/video/11111",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Payload 2:**
```json
{
  "video_url": "https://example.com/video/22222",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ✅ Создаются 2 разных creative
- ✅ У них разные `video_url`
- ✅ Оба имеют одинаковый `tracker_id`

**Проверки:**
- COUNT(*) WHERE tracker_id = 'KT-123456' = 2
- Все creative_id уникальны

---

### ❌ 5. Invalid: Отсутствующие обязательные поля (`invalid_missing_fields.json`)

**Назначение:** Проверка отклонения payload без обязательных полей

**Вариант 1 — отсутствует `video_url`:**
```json
{
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Вариант 2 — отсутствует `tracker_id`:**
```json
{
  "video_url": "https://example.com/video/12345",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ❌ HTTP 400 Bad Request
- ❌ Creative НЕ создаётся
- ✅ Событие `CreativeIngestionRejected` записано в event_log
- ✅ Workflow останавливается

**Проверки:**
- В creatives нет новых записей
- В event_log есть событие с `event_type = 'CreativeIngestionRejected'`
- Payload события содержит причину отклонения

---

### ❌ 6. Invalid: Пустые обязательные поля (`invalid_empty_fields.json`)

**Назначение:** Проверка отклонения payload с пустыми строками

**Вариант 1 — пустой `video_url`:**
```json
{
  "video_url": "",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Вариант 2 — пустой `tracker_id`:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "",
  "source_type": "user"
}
```

**Ожидаемое поведение:**
- ❌ HTTP 400 Bad Request
- ❌ Creative НЕ создаётся
- ✅ Событие `CreativeIngestionRejected`

**Проверки:**
- Пустые строки считаются невалидными
- В creatives нет новых записей

---

### ❌ 7. Invalid: Неверный source_type (`invalid_wrong_source_type.json`)

**Назначение:** Проверка отклонения payload с неверным `source_type`

**Payload:**
```json
{
  "video_url": "https://example.com/video/12345",
  "tracker_id": "KT-123456",
  "source_type": "system"
}
```

**Ожидаемое поведение:**
- ❌ HTTP 400 Bad Request
- ❌ Creative НЕ создаётся
- ✅ Событие `CreativeIngestionRejected`

**Причина:** В STEP 01 `source_type` должен быть строго `"user"`.  
`source_type = "system"` будет использоваться позже для system-generated creatives.

**Проверки:**
- В creatives нет записей с `source_type = 'system'` на этом этапе
- В event_log есть событие отклонения

---

### ❌ 8. Garbage Input (`garbage_input.json`)

**Назначение:** Проверка обработки мусорного JSON

**Вариант 1 — невалидный JSON:**
```
{ "video_url": "https://example.com/video/12345", "tracker_id": "KT-123456" }
```

**Вариант 2 — не JSON вообще:**
```
This is not JSON at all!
```

**Вариант 3 — массив вместо объекта:**
```json
[
  {
    "video_url": "https://example.com/video/12345",
    "tracker_id": "KT-123456"
  }
]
```

**Ожидаемое поведение:**
- ❌ HTTP 400 Bad Request
- ❌ Creative НЕ создаётся
- ✅ Событие `CreativeIngestionRejected`

**Проверки:**
- Система не падает на мусорных данных
- Ошибка обрабатывается gracefully

---

## 🧪 Последовательность тестирования

### Рекомендуемый порядок:

1. **Happy Path** — убедиться, что базовая функциональность работает
2. **Idempotency** — проверить, что повтор не создаёт дубль
3. **Edge Cases** — проверить граничные случаи
4. **Invalid Inputs** — проверить обработку ошибок

### Полный тест-ран:

```bash
# 1. Happy path
curl -X POST $WEBHOOK_URL -d @happy_path.json

# 2. Idempotency (тот же payload)
curl -X POST $WEBHOOK_URL -d @idempotency.json

# 3. Edge case: один video_url, разные tracker_id
curl -X POST $WEBHOOK_URL -d @edge_same_video_different_tracker_1.json
curl -X POST $WEBHOOK_URL -d @edge_same_video_different_tracker_2.json

# 4. Edge case: разные video_url, один tracker_id
curl -X POST $WEBHOOK_URL -d @edge_different_video_same_tracker_1.json
curl -X POST $WEBHOOK_URL -d @edge_different_video_same_tracker_2.json

# 5. Invalid: missing fields
curl -X POST $WEBHOOK_URL -d @invalid_missing_fields.json

# 6. Invalid: empty fields
curl -X POST $WEBHOOK_URL -d @invalid_empty_fields.json

# 7. Invalid: wrong source_type
curl -X POST $WEBHOOK_URL -d @invalid_wrong_source_type.json

# 8. Garbage input
curl -X POST $WEBHOOK_URL -d @garbage_input.json
```

## 📝 Примечания

- Все payload'ы должны быть в формате JSON
- Используйте реальные URL для video_url (или тестовые домены)
- tracker_id должен соответствовать формату Keitaro (KT-XXXXXX)
- После каждого теста проверяйте event_log


