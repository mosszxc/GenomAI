# 08_learning_loop_playbook.md

**STEP 08 — Learning Loop (Minimal, MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `07_outcome_ingestion_playbook.md` (daily snapshots существуют)
- Outcome Aggregation (system outcome с decision_id)

**Следующий шаг:** ❌ **НЕТ** (MVP завершается здесь)

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

📌 **Если любое условие не выполнено → STOP без ошибки.**

## 2. n8n Workflow

**Workflow name:** `learning_loop_minimal`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `OutcomeAggregated`

### 2.2 Guard: Eligibility Check

- **Node:** Function

**Проверки:**
- `if (origin_type !== 'system') STOP`
- `if (!decision_id) STOP`
- `if (outcome_already_applied) STOP`

📌 **Повтор learning запрещён.**

### 2.3 Load Current Confidence

- **Node:** Supabase Select

```sql
SELECT confidence
FROM idea_confidence_versions
WHERE idea_id = :idea_id
ORDER BY created_at DESC
LIMIT 1;
```

Если нет → считаем `confidence = 0`.

## 3. Learning Rule (MVP)

### 3.1 Правило обновления

Rule-based, бинарное:

**Пример:**
- если `leads > 0` → `+1`
- если `leads = 0` → `-1`

📌 **Формула фиксирована, не обучаемая.**

### 3.2 Persist New Confidence Version

- **Node:** Supabase Insert
- **Таблица:** `idea_confidence_versions`

**Поля:**
- `id` (uuid)
- `idea_id`
- `confidence`
- `source_outcome_id`
- `created_at`

📌 **append-only**  
📌 **UPDATE запрещён**

### 3.3 Mark Outcome as Applied

- **Node:** Supabase Update
- **Таблица:** `outcome_aggregates`
- **Поле:**
  - `learning_applied = true`

📌 **Единственный допустимый UPDATE в этом шаге.**

### 2.6 Emit Event

**OutcomeAppliedToLearning**

```json
{
  "idea_id": "uuid",
  "outcome_id": "uuid",
  "new_confidence": 3
}
```

## 4. Хранилище

### Таблица idea_confidence_versions

```sql
idea_confidence_versions (
  id                 uuid primary key,
  idea_id            uuid not null,
  confidence         int not null,
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
  "new_confidence": 3
}
```

**Запрещённые:**

- любые re-learning events
- любые decay events
- любые fatigue events

## 6. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ learning применяется только к system outcome
- ✅ confidence обновляется append-only
- ✅ outcome не используется повторно
- ✅ событие `OutcomeAppliedToLearning` эмитится
- ✅ не используется:
  - decay
  - fatigue
  - resurrection
  - ML

## 7. Типовые ошибки (PR-блокеры)

❌ **learning от user outcome**  
❌ **повторное применение outcome**  
❌ **пересчёт confidence**  
❌ **ручной триггер learning**  
❌ **сложные формулы**

## 8. Ручные проверки (обязательные)

### Check 1 — Happy path
- system outcome
- confidence увеличился / уменьшился
- outcome помечен как applied

### Check 2 — Duplicate outcome
- повторное событие
- learning не применяется

### Check 3 — User outcome
- `origin_type = user`
- learning не применяется

## 9. Выход шага

На выходе гарантировано:

**Система начала помнить,**
**но не начала думать лучше.**

**И это правильный финал MVP.**

