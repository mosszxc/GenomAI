# 01_ingestion_playbook.md

**STEP 01 — Ingestion + Validation (MVP)**

**Статус:** ✅ **COMPLETED & TESTED**  
**Scope:** MVP  
**Зависимости:** отсутствуют  
**Следующий шаг:** 02_decomposition_playbook.md

## ✅ Статус выполнения

**Epic:** #1 - закрыт  
**Все Issues:** #2, #3, #4, #5, #6, #7, #8, #9 - закрыты  
**Gate Check:** STEP 01 → STEP 02 - ✅ PASSED

**Реализовано:**
- ✅ Workflow: `creative_ingestion_webhook` (ID: `dvZvUUmhtPzYOK7X`) - активен
- ✅ Таблица: `genomai.creatives` - создана и протестирована
- ✅ Таблица: `genomai.event_log` - создана и протестирована
- ✅ Все события реализованы и протестированы
- ✅ Все проверки из playbook пройдены

**Тестирование:**
- ✅ Happy path - пройден
- ✅ Idempotency - пройден (UNIQUE constraint работает)
- ✅ Invalid input - пройден (NOT NULL и CHECK constraints работают)
- ✅ Garbage input - пройден (CreativeIngestionRejected создаётся)
- ✅ Запрещённые сущности - не создаются (ideas, decisions, learning state)

## 0. Назначение шага

Этот шаг отвечает только за факт попадания внешнего объекта в систему.

Creative на этом этапе — сырой факт существования,
не идея, не гипотеза, не объект анализа.

**Шаг не делает:**
- выводов,
- оценок,
- решений,
- интерпретаций.

## 1. Входной контракт

### 1.1 Payload (Webhook)

```json
{
  "video_url": "https://...",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

### 1.2 Правила

- `video_url` — обязательный, non-empty string
- `tracker_id` — обязательный, non-empty string
- `source_type` — жёстко `user`
- любые дополнительные поля → игнорируются

## 2. n8n Workflow

**Workflow name:** `creative_ingestion_webhook`

### 2.1 Webhook Trigger

- **Node:** Webhook
- **Method:** POST
- **Path:** `/ingest/creative`

### 2.2 Schema Validation

- **Node:** Function / JSON Schema Validate

**Проверки:**
- payload — валидный JSON
- все обязательные поля присутствуют
- `source_type === "user"`

**On fail:**
- Emit event `CreativeIngestionRejected`
- HTTP 400
- workflow STOP

### 2.3 Idempotency Check

- **Node:** Supabase Select

**Запрос:**
```sql
SELECT id
FROM creatives
WHERE video_url = :video_url
  AND tracker_id = :tracker_id
LIMIT 1;
```

**Ветки:**
- найдено → idempotent path
- не найдено → create path

📌 **Повтор ≠ ошибка**

### 2.4 Create Creative (если не найден)

- **Node:** Supabase Insert
- **Таблица:** `creatives`

**Поля:**
- `id` — uuid (генерируется)
- `video_url`
- `tracker_id`
- `source_type = 'user'`
- `status = 'registered'`
- `created_at = now()`

### 2.5 Emit Events

#### 2.5.1 CreativeReferenceReceived

Эмитится всегда после успешной валидации, до записи в БД.

```json
{
  "video_url": "...",
  "tracker_id": "...",
  "source_type": "user"
}
```

#### 2.5.2 CreativeRegistered

Эмитится:
- после insert
- или при idempotent case

```json
{
  "creative_id": "uuid",
  "video_url": "...",
  "tracker_id": "...",
  "source_type": "user"
}
```

## 3. Хранилище

### 3.1 Таблица creatives

**Минимальная схема:**

```sql
creatives (
  id          uuid primary key,
  video_url   text not null,
  tracker_id  text not null,
  source_type text not null check (source_type = 'user'),
  status      text not null,
  created_at  timestamp not null,
  unique (video_url, tracker_id)
)
```

### 3.2 Инварианты

- UPDATE запрещён (кроме status, если понадобится позже)
- DELETE запрещён
- один creative = один внешний объект

## 4. События

**Обязательные события:**
- `CreativeReferenceReceived`
- `CreativeRegistered`

**Не допускаются:**
- любые decision-related events
- любые learning-related events

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ webhook принимает payload
- ✅ невалидный payload → reject
- ✅ повторный payload → не создаёт дубль
- ✅ запись появляется в `creatives`
- ✅ события записаны в `event_log`
- ✅ не создаются:
  - ideas
  - transcripts
  - hypotheses
  - learning state

## 6. Типовые ошибки (и почему это баг)

❌ **создание ideas**  
→ нарушение порядка разработки

❌ **проверки "плохой / хороший креатив"**  
→ логика в ingestion запрещена

❌ **auto-enrichment (добавление полей)**  
→ нарушение Canonical Schema

❌ **retry на invalid payload**  
→ ошибка клиента ≠ ошибка системы

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- отправить валидный payload
- creative появился
- 2 события в event_log

### Check 2 — Idempotency
- отправить тот же payload
- новая запись не появилась
- `CreativeRegistered` эмитится корректно

### Check 3 — Invalid input
- убрать `tracker_id`
- HTTP 400
- creative не появился

### Check 4 — Garbage input
- мусорный JSON
- reject
- event `CreativeIngestionRejected`

## 8. Выход шага

На выходе шага гарантировано:

**Creative существует в системе,**
**но система о нём ничего не думает.**

Это единственное допустимое состояние.

## 9. Жёсткие запреты (PR-блокеры)

❌ LLM  
❌ Decision Engine  
❌ Learning  
❌ Quality checks  
❌ Enrichment

**Любое из этого = отклонение PR.**

## 10. Готовность к следующему шагу

Можно переходить к `02_decomposition_playbook.md` только если:
- ✅ этот шаг задеплоен
- ✅ прошёл ручные проверки
- ✅ зафиксирован коммитом
