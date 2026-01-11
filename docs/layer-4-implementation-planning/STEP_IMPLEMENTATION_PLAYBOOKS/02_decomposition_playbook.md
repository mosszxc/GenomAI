# 02_decomposition_playbook.md

**STEP 02 — Decomposition (LLM, MVP)**

**Статус:** IMPLEMENTED
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

## 2. Реализация (Temporal)

**Workflow:** `CreativePipelineWorkflow` (Step 2-3)
**Файл:** `temporal/workflows/creative_pipeline.py`
**Task Queue:** `creative-pipeline`

### 2.1 Trigger

Автоматически после Step 1 (Transcription) в CreativePipelineWorkflow

### 2.2 Load Canonical Schema

**Activity:** `get_canonical_schema`
- `schema_version`: v2
- `schema_definition`: JSON Schema (Idea-level variables)

### 2.3 LLM Call (Classification Only)

**Activity:** `decompose_creative`

**Prompt правила:**
- "Ты классификатор"
- "Заполняй только поля schema"
- "Если не уверен — используй closest enum"
- "Запрещено добавлять поля"

**Выход LLM:**
- JSON строго соответствующий schema

### 2.4 Schema Validation (Critical)

**Activity:** `validate_decomposition`

**Проверки:**
- все обязательные поля присутствуют
- типы совпадают
- enum значения допустимы
- нет лишних полей

**On fail:**
- workflow STOP
- emit `CreativeDecompositionRejected`
- нет retries

### 2.5 Persist Decomposed Creative

**Activity:** `save_decomposed_creative`
**Таблица:** `decomposed_creatives`

**Поля:**
- `id` (uuid)
- `creative_id`
- `schema_version`
- `payload` (jsonb)
- `created_at`

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
  "schema_version": "v2"
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
- транскрипт сохранён immutable
- decomposed_creative сохранён
- payload валиден по schema
- события эмитены
- не созданы: ideas, decisions, confidence, scores

## 6. Типовые ошибки (PR-блокеры)

❌ **добавление "confidence"**
❌ **добавление "novelty"**
❌ **любые числовые оценки**
❌ **логика "если плохо — не сохраняем"**
❌ **retries LLM при невалидной schema**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- отправить transcript
- decomposed_creative появился
- schema валидна

### Check 2 — LLM hallucination
- LLM вернул лишнее поле
- workflow должен STOP
- данные не сохраняются

### Check 3 — Повтор
- повторный transcript
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
- schema-валидация работает
- данные сохраняются корректно
- шаг задеплоен и проверен вручную
