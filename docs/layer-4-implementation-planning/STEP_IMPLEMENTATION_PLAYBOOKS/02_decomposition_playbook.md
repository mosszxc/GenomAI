# 02_decomposition_playbook.md

**STEP 02 — Decomposition (LLM, MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `01_ingestion_playbook.md` (creative зарегистрирован)

**Следующий шаг:** `03_idea_registry_playbook.md`

## 0. Назначение шага

Этот шаг превращает сырой текст в структуру по Canonical Schema.

LLM здесь — классификатор, а не интеллект.  
Он не думает, не оценивает, не решает.

Результат шага — структурированное описание,
без смысла, без качества, без решений.

## 1. Входные данные

### 1.1 Источник

- зарегистрированный creative
- полученный transcript_text

### 1.2 Контракт входа

```json
{
  "creative_id": "uuid",
  "transcript_text": "full speech text only"
}
```

### 1.3 Ограничения

- только текст речи
- без визуала
- без primary / description / CTA
- без метаданных

## 2. n8n Workflow

**Workflow name:** `creative_decomposition_llm`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `TranscriptCreated`

### 2.2 Load Canonical Schema

- **Node:** Static / Config node
- `schema_version`: v1
- `schema_definition`: JSON Schema (Idea-level variables)

📌 **Schema — single source of truth.**

### 2.3 LLM Call (Classification Only)

- **Node:** LLM (OpenAI / Anthropic / etc.)

**Prompt правила:**
- "Ты классификатор"
- "Заполняй только поля schema"
- "Если не уверен — используй closest enum"
- "Запрещено добавлять поля"

**Выход LLM:**
- JSON строго соответствующий schema.

### 2.4 Schema Validation (Critical)

- **Node:** JSON Schema Validate

**Проверки:**
- все обязательные поля присутствуют
- типы совпадают
- enum значения допустимы
- нет лишних полей

**On fail:**
- workflow STOP
- emit `CreativeDecompositionRejected`
- нет retries

📌 **Невалидный output LLM = discard.**

### 2.5 Persist Transcript (Immutable)

- **Node:** Supabase Insert
- **Таблица:** `transcripts`

**Поля:**
- `id` (uuid)
- `creative_id`
- `version = 1`
- `transcript_text`
- `created_at`

📌 **UPDATE запрещён.**

### 2.6 Persist Decomposed Creative

- **Node:** Supabase Insert
- **Таблица:** `decomposed_creatives`

**Поля:**
- `id` (uuid)
- `creative_id`
- `schema_version`
- `payload` (jsonb)
- `created_at`

📌 **Результат — чистая структура, не интерпретация.**

## 3. Хранилище

### 3.1 transcripts

```sql
transcripts (
  id              uuid primary key,
  creative_id     uuid not null,
  version         int not null,
  transcript_text text not null,
  created_at      timestamp not null,
  unique (creative_id, version)
)
```

### 3.2 decomposed_creatives

```sql
decomposed_creatives (
  id             uuid primary key,
  creative_id    uuid not null,
  schema_version text not null,
  payload        jsonb not null,
  created_at     timestamp not null
)
```

## 4. События

**Обязательные:**

### TranscriptCreated

```json
{
  "creative_id": "uuid",
  "version": 1
}
```

### CreativeDecomposed

```json
{
  "creative_id": "uuid",
  "schema_version": "v1"
}
```

**Допустимые (error):**

### CreativeDecompositionRejected

```json
{
  "creative_id": "uuid",
  "reason": "schema_validation_failed"
}
```

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ транскрипт сохранён immutable
- ✅ decomposed_creative сохранён
- ✅ payload валиден по schema
- ✅ события заэмитены
- ✅ не созданы:
  - ideas
  - decisions
  - confidence
  - scores

## 6. Типовые ошибки (PR-блокеры)

❌ **добавление "confidence"**  
❌ **добавление "novelty"**  
❌ **любые числовые оценки**  
❌ **логика "если плохо — не сохраняем"**  
❌ **retries LLM при невалидной schema**

**Все это = нарушение роли LLM.**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- отправить transcript
- decomposed_creative появился
- schema валидна

### Check 2 — LLM hallucination
- заставить LLM вернуть лишнее поле
- workflow должен STOP
- данные не сохраняются

### Check 3 — Повтор
- повторный `TranscriptCreated` с той же версией
- duplicate insert запрещён

## 8. Выход шага

На выходе гарантировано:

**Есть структурированное описание идеи**
**без смысла, без качества, без решений.**

## 9. Жёсткие запреты

❌ Decision Engine  
❌ Learning  
❌ Любые оценки  
❌ Любая "умная логика"  
❌ Попытка "починить" output LLM

## 10. Готовность к следующему шагу

Переход к `03_idea_registry_playbook.md` разрешён, если:
- ✅ schema-валидация работает
- ✅ данные сохраняются корректно
- ✅ шаг задеплоен и проверен вручную

