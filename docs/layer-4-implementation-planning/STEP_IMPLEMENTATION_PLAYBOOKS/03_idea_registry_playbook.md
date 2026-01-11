# 03_idea_registry_playbook.md

**STEP 03 — Idea Registry (MVP)**

**Статус:** IMPLEMENTED
**Scope:** MVP
**Зависимости:**
- `02_decomposition_playbook.md` (decomposed_creative сохранён)

**Следующий шаг:** `04_decision_engine_playbook.md`

## 0. Назначение шага

Этот шаг создаёт каноническую сущность мышления системы — **Idea**.

Idea — это **что сказано**, а не насколько это хорошо.

Шаг:
- не оценивает,
- не сравнивает,
- не объединяет,
- не кластеризует.

## 1. Входные данные

### 1.1 Источник

- событие `CreativeDecomposed` (внутри workflow)

### 1.2 Контракт входа

```json
{
  "creative_id": "uuid",
  "schema_version": "v2"
}
```

## 2. Реализация (Temporal)

**Workflow:** `CreativePipelineWorkflow` (Step 4)
**Файл:** `temporal/workflows/creative_pipeline.py`
**Service:** `decision-engine-service/src/services/idea_registry.py`

### 2.1 Trigger

Автоматически после Step 3 (Decomposition) в CreativePipelineWorkflow

### 2.2 Load Decomposed Creative

**Activity:** `load_decomposed_creative`

```sql
SELECT payload
FROM decomposed_creatives
WHERE creative_id = :creative_id
ORDER BY created_at DESC
LIMIT 1;
```

### 2.3 Canonical Hash (deterministic)

**Service:** `IdeaRegistry.compute_canonical_hash()`

**Правило:**
- берутся только поля Canonical Schema
- сортировка ключей
- сериализация → hash (SHA-256)

### 2.4 Idempotency Check

**Service:** `IdeaRegistry.find_by_hash()`

```sql
SELECT id FROM ideas
WHERE canonical_hash = :canonical_hash
LIMIT 1;
```

**Ветки:**
- найдено → reuse Idea
- не найдено → create Idea

### 2.5 Create Idea (если не найдена)

**Service:** `IdeaRegistry.create()`
**Таблица:** `ideas`

**Поля:**
- `id` (uuid)
- `canonical_hash`
- `created_at`
- `status = active`

### 2.6 Emit Event

**IdeaRegistered**

```json
{
  "idea_id": "uuid",
  "canonical_hash": "sha256...",
  "creative_id": "uuid"
}
```

## 3. Хранилище

### 3.1 Таблица ideas

```sql
ideas (
  id              uuid primary key,
  canonical_hash  text not null unique,
  created_at      timestamp not null,
  status          text not null
)
```

### 3.2 Инварианты

- `canonical_hash` уникален
- UPDATE запрещён
- DELETE запрещён

## 4. События

**Обязательные:**

### IdeaRegistered

```json
{
  "idea_id": "uuid",
  "canonical_hash": "sha256...",
  "creative_id": "uuid"
}
```

**Запрещённые:**

- любые similarity / cluster events
- любые learning events

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- Idea создаётся при первом появлении структуры
- Повторная структура → reuse той же Idea
- canonical_hash детерминирован
- событие `IdeaRegistered` эмитится
- не создаются: clusters, similarity, scores

## 6. Типовые ошибки (PR-блокеры)

❌ **использование embeddings**
❌ **любые similarity checks**
❌ **попытка merge идей**
❌ **добавление полей вне schema**
❌ **недетерминированный hash**

## 7. Ручные проверки (обязательные)

### Check 1 — Determinism
- два одинаковых decomposed_creative
- canonical_hash совпадает
- idea одна

### Check 2 — New structure
- изменить 1 enum
- новый canonical_hash
- новая Idea

### Check 3 — Idempotency
- повтор workflow
- новая Idea не создаётся

## 8. Выход шага

На выходе гарантировано:

**Система знает, о чём идея,**
**но не знает, хороша ли она.**

## 9. Жёсткие запреты

❌ clustering
❌ similarity
❌ embeddings
❌ decision
❌ learning

## 10. Готовность к следующему шагу

Можно переходить к `04_decision_engine_playbook.md`, если:
- идеи создаются детерминированно
- idempotency работает
- нет побочных сущностей
