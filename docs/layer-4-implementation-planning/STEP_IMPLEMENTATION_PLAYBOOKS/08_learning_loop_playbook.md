# 08_learning_loop_playbook.md

**STEP 08 — Learning Loop (Minimal, MVP)**

**Статус:** IMPLEMENTED
**Scope:** MVP
**Зависимости:**
- `07_outcome_ingestion_playbook.md` (daily snapshots существуют)
- Outcome Aggregation (system outcome с decision_id)

**Следующий шаг:** MVP завершается здесь

## 0. Назначение шага

Этот шаг — **первое касание памяти**.

Learning Loop не делает систему умной.
Он делает её чуть менее слепой.

В MVP learning:
- одношаговый,
- необратимый,
- строго причинно-следственный.

## 1. Входные данные

### 1.1 Источник

- событие `OutcomeAggregated`

### 1.2 Контракт входа

```json
{
  "outcome_id": "uuid",
  "decision_id": "uuid",
  "idea_id": "uuid",
  "origin_type": "system",
  "window_id": "D1_D3",
  "metrics": {
    "leads": 12,
    "spend": 100
  }
}
```

### 1.3 Жёсткие условия допуска

- `origin_type === "system"`
- `decision_id != null`
- outcome ещё не использован для learning

## 2. Реализация (Temporal)

**Workflow:** `LearningLoopWorkflow`
**Файл:** `temporal/workflows/learning_loop.py`
**Task Queue:** `metrics`
**Schedule:** Every 1 hour

### 2.1 Trigger

Schedule Trigger (hourly)

### 2.2 Guard: Eligibility Check

**Activity:** `check_learning_eligibility`

**Проверки:**
- `origin_type === 'system'`
- `decision_id != null`
- `outcome_already_applied === false`

### 2.3 Load Current Score

**Activity:** `load_idea_score`

```sql
SELECT score
FROM idea_scores
WHERE idea_id = :idea_id
ORDER BY created_at DESC
LIMIT 1;
```

Если нет → считаем `score = 0`.

## 3. Learning Rule (MVP)

### 3.1 Правило обновления

Rule-based, формула:

```python
if leads > 0 and roi > threshold:
    score_delta = +1
elif leads == 0 or roi < 0:
    score_delta = -1
else:
    score_delta = 0
```

### 3.2 Persist New Score

**Activity:** `save_idea_score`
**Таблица:** `idea_scores`

**Поля:**
- `id` (uuid)
- `idea_id`
- `score`
- `source_outcome_id`
- `created_at`

### 3.3 Check Death Condition

**Activity:** `check_death_condition`

Если `score <= death_threshold`:
- Update idea status to `dead`
- Emit `IdeaDied` event

### 3.4 Mark Outcome as Applied

**Activity:** `mark_outcome_applied`
**Таблица:** `outcome_aggregates`
**Поле:** `learning_applied = true`

### 3.5 Emit Event

**OutcomeAppliedToLearning**

```json
{
  "idea_id": "uuid",
  "outcome_id": "uuid",
  "new_score": 3
}
```

## 4. Хранилище

### Таблица idea_scores

```sql
idea_scores (
  id                 uuid primary key,
  idea_id            uuid not null,
  score              int not null,
  source_outcome_id  uuid not null,
  created_at         timestamp not null
)
```

### Инварианты

- append-only
- `source_outcome_id` обязателен
- один outcome → один learning update

## 5. События

**Обязательные:**

### OutcomeAppliedToLearning

```json
{
  "idea_id": "uuid",
  "outcome_id": "uuid",
  "new_score": 3
}
```

### IdeaDied (conditional)

```json
{
  "idea_id": "uuid",
  "final_score": -3,
  "reason": "score_threshold"
}
```

**Запрещённые:**

- любые re-learning events
- любые decay events
- любые resurrection events

## 6. Definition of Done (DoD)

Шаг считается выполненным, если:
- learning применяется только к system outcome
- score обновляется append-only
- outcome не используется повторно
- событие `OutcomeAppliedToLearning` эмитится
- death condition проверяется
- не используется: decay, resurrection, ML

## 7. Типовые ошибки (PR-блокеры)

❌ **learning от user outcome**
❌ **повторное применение outcome**
❌ **пересчёт score**
❌ **ручной триггер learning**
❌ **сложные ML формулы**

## 8. Ручные проверки (обязательные)

### Check 1 — Happy path
- system outcome
- score увеличился / уменьшился
- outcome помечен как applied

### Check 2 — Duplicate outcome
- повторное событие
- learning не применяется

### Check 3 — User outcome
- `origin_type = user`
- learning не применяется

### Check 4 — Death condition
- score достиг threshold
- idea помечена как dead

## 9. Выход шага

На выходе гарантировано:

**Система начала помнить,**
**но не начала думать лучше.**

**И это правильный финал MVP.**

## 10. Жёсткие запреты

❌ decay
❌ resurrection
❌ ML
❌ сложные эвристики

## 11. Связанные документы

- `docs/TEMPORAL_WORKFLOWS.md` — Temporal workflows reference
- `docs/layer-1-logic/DECISION_ENGINE.md` — Death memory integration
