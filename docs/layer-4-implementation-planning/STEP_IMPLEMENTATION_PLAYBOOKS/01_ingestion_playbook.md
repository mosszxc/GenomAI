# 01_ingestion_playbook.md

**STEP 01 — Ingestion + Validation (MVP)**

**Статус:** IMPLEMENTED
**Scope:** MVP
**Зависимости:** отсутствуют
**Следующий шаг:** 02_decomposition_playbook.md

## Статус выполнения

**Epic:** #1 - закрыт
**Все Issues:** #2, #3, #4, #5, #6, #7, #8, #9 - закрыты
**Gate Check:** STEP 01 → STEP 02 - PASSED

**Реализовано на Temporal:**
- Workflow: `CreativePipelineWorkflow` (Step 1: Video Registration)
- Workflow: `CreativeRegistrationWorkflow` (Telegram → Creative)
- Таблица: `genomai.creatives` - создана и протестирована
- Таблица: `genomai.event_log` - создана и протестирована

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

### 1.1 Payload (Telegram / API)

```json
{
  "video_url": "https://...",
  "buyer_id": "uuid",
  "source_type": "user"
}
```

### 1.2 Правила

- `video_url` — обязательный, non-empty string
- `buyer_id` — опциональный для привязки к buyer
- `source_type` — жёстко `user`
- любые дополнительные поля → игнорируются

## 2. Реализация (Temporal)

**Workflow:** `CreativeRegistrationWorkflow`
**Файл:** `temporal/workflows/creative_registration.py`
**Task Queue:** `telegram`

### 2.1 Trigger

- Telegram: Video URL от пользователя
- API: POST `/api/creative/register`

### 2.2 Schema Validation

**Activity:** `validate_video_url`

**Проверки:**
- payload — валидный
- video_url — корректный URL
- поддерживаемый формат (YouTube, Vimeo, MP4, etc.)

**On fail:**
- Emit event `CreativeIngestionRejected`
- Workflow STOP

### 2.3 Idempotency Check

**Activity:** `check_creative_exists`

**Запрос:**
```sql
SELECT id FROM creatives
WHERE video_url = :video_url
LIMIT 1;
```

**Ветки:**
- найдено → idempotent path
- не найдено → create path

### 2.4 Create Creative

**Activity:** `create_creative`
**Таблица:** `creatives`

**Поля:**
- `id` — uuid (генерируется)
- `video_url`
- `buyer_id`
- `source_type = 'user'`
- `status = 'registered'`
- `created_at = now()`

### 2.5 Emit Events

#### CreativeReferenceReceived

Эмитится после успешной валидации.

#### CreativeRegistered

Эмитится после insert или при idempotent case.

```json
{
  "creative_id": "uuid",
  "video_url": "...",
  "buyer_id": "uuid"
}
```

## 3. Хранилище

### 3.1 Таблица creatives

```sql
creatives (
  id          uuid primary key,
  video_url   text not null,
  buyer_id    uuid,
  source_type text not null check (source_type = 'user'),
  status      text not null,
  created_at  timestamp not null,
  unique (video_url)
)
```

### 3.2 Инварианты

- UPDATE запрещён (кроме status)
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
- webhook/Telegram принимает payload
- невалидный payload → reject
- повторный payload → не создаёт дубль
- запись появляется в `creatives`
- события записаны в `event_log`
- не создаются: ideas, transcripts, hypotheses, learning state

## 6. Типовые ошибки (PR-блокеры)

❌ **создание ideas**
❌ **проверки "плохой / хороший креатив"**
❌ **auto-enrichment (добавление полей)**
❌ **retry на invalid payload**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- отправить валидный video_url в Telegram
- creative появился
- events в event_log

### Check 2 — Idempotency
- отправить тот же video_url
- новая запись не появилась

### Check 3 — Invalid input
- невалидный URL
- reject без создания creative

## 8. Выход шага

На выходе шага гарантировано:

**Creative существует в системе,**
**но система о нём ничего не думает.**

## 9. Жёсткие запреты (PR-блокеры)

❌ LLM
❌ Decision Engine
❌ Learning
❌ Quality checks
❌ Enrichment

## 10. Готовность к следующему шагу

Можно переходить к `02_decomposition_playbook.md` только если:
- этот шаг задеплоен
- прошёл ручные проверки
- зафиксирован коммитом
