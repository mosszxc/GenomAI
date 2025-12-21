# 04_decision_engine_playbook.md

**STEP 04 — Decision Engine (MVP, Skeleton)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `03_idea_registry_playbook.md` (Idea зарегистрирована)

**Следующий шаг:** `05_hypothesis_factory_playbook.md`

## 0. Назначение шага

Decision Engine — это **детерминированный фильтр допустимости**.

Он не выбирает "лучшее".  
Он отвечает только на вопрос: **можно / нельзя / подожди**.

На MVP этапе Decision Engine:
- тупой,
- жёсткий,
- предсказуемый.

**И это архитектурно правильно.**

## 1. Входные данные

### 1.1 Источник

- событие `IdeaRegistered`

### 1.2 Контракт входа

```json
{
  "idea_id": "uuid"
}
```

## 2. n8n Workflow

**Workflow name:** `decision_engine_mvp`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `IdeaRegistered`

### 2.2 Load Idea

- **Node:** Supabase Select

```sql
SELECT id, status
FROM ideas
WHERE id = :idea_id;
```

**Если не найдено:**
- abort
- emit `DecisionAborted` (optional)
- STOP

### 2.3 Hard Constraints Check (MVP)

- **Node:** Function (rules)

**Проверки (строго в этом порядке):**

1️⃣ **Idea exists**
- (если workflow дошёл сюда — уже ок)

2️⃣ **No HARD_DEAD**
- В MVP:
  - `HARD_DEAD = status = 'dead'`
  - если dead → reject

3️⃣ **No active global ban**
- В MVP:
  - заглушка (always false)
  - оставляем хук, но логики нет

4️⃣ **Basic risk cap**
- В MVP:
  - `max_active_ideas = фиксированное число` (например, 100)
  - если превышено → defer

📌 **Никаких других проверок.**

### 2.4 Decision Output

**Возможные значения:**
- `approve`
- `reject`
- `defer`

Decision определяется только rules above.

### 2.5 Persist Decision

- **Node:** Supabase Insert
- **Таблица:** `decisions`

**Поля:**
- `id` (uuid)
- `idea_id`
- `decision` (approve | reject | defer)
- `decision_epoch = 1`
- `created_at`

### 2.6 Persist Decision Trace

- **Node:** Supabase Insert
- **Таблица:** `decision_traces`

**Поля:**
- `id` (uuid)
- `decision_id`
- `checks` (jsonb)
- `result`
- `created_at`

📌 **Decision Trace — обязателен, даже если решение тривиально.**

### 2.7 Emit Event

**DecisionMade**

```json
{
  "decision_id": "uuid",
  "idea_id": "uuid",
  "decision": "approve | reject | defer",
  "epoch": 1
}
```

## 3. Хранилище

### 3.1 Таблица decisions

```sql
decisions (
  id              uuid primary key,
  idea_id         uuid not null,
  decision        text not null,
  decision_epoch  int not null,
  created_at      timestamp not null
)
```

### 3.2 Таблица decision_traces

```sql
decision_traces (
  id            uuid primary key,
  decision_id   uuid not null,
  checks        jsonb not null,
  result        text not null,
  created_at    timestamp not null
)
```

## 4. События

**Обязательные:**

### DecisionMade

```json
{
  "decision_id": "uuid",
  "idea_id": "uuid",
  "decision": "approve | reject | defer",
  "epoch": 1
}
```

**Допустимые (abort):**

### DecisionAborted

```json
{
  "idea_id": "uuid",
  "reason": "idea_not_found"
}
```

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ Decision создаётся для каждой Idea
- ✅ Decision детерминирован
- ✅ Decision Trace сохраняется
- ✅ событие `DecisionMade` эмитится
- ✅ не используется:
  - LLM
  - ML
  - confidence
  - fatigue
  - novelty

## 6. Типовые ошибки (PR-блокеры)

❌ **использование LLM**  
❌ **любые числовые скоринги**  
❌ **скрытая логика в промптах**  
❌ **отсутствие decision_trace**  
❌ **недетерминированный порядок проверок**

## 7. Ручные проверки (обязательные)

### Check 1 — Approve
- Idea status = active
- risk cap не превышен
- decision = approve

### Check 2 — Reject
- Idea status = dead
- decision = reject

### Check 3 — Defer
- искусственно превысить risk cap
- decision = defer

### Check 4 — Determinism
- одинаковый input → одинаковый decision

## 8. Выход шага

На выходе гарантировано:

**Система умеет отказывать и умеет разрешать,**
**но не умеет оптимизировать.**

## 9. Жёсткие запреты

❌ fatigue  
❌ confidence  
❌ ML  
❌ LLM  
❌ любые эвристики "качества"

## 10. Готовность к следующему шагу

Можно переходить к `05_hypothesis_factory_playbook.md`, если:
- ✅ decisions создаются корректно
- ✅ decision_trace всегда есть
- ✅ approve / reject / defer работают

