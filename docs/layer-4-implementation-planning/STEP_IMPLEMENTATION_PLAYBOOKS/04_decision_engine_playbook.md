# 04_decision_engine_playbook.md

**STEP 04 — Decision Engine (MVP)**

**Статус:** IMPLEMENTED
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

- После IdeaRegistered (внутри workflow)

### 1.2 Контракт входа

```json
{
  "idea_id": "uuid"
}
```

## 2. Реализация (Temporal + FastAPI)

**Workflow:** `CreativePipelineWorkflow` (Step 5)
**Файл:** `temporal/workflows/creative_pipeline.py`
**Service:** `decision-engine-service/src/services/decision_engine.py`
**API:** `POST /api/decision`

### 2.1 Trigger

Автоматически после Step 4 (Idea Registry) в CreativePipelineWorkflow

### 2.2 Decision Engine Checks (4 checks)

**Service:** `DecisionEngine.evaluate()`

| Check | Файл | Результат |
|-------|------|-----------|
| Schema Validity | `schema_validity.py` | REJECT if invalid |
| Death Memory | `death_memory.py` | REJECT if dead |
| Fatigue Constraint | `fatigue_constraint.py` | REJECT if fatigued |
| Risk Budget | `risk_budget.py` | DEFER if over budget |

**Все pass = APPROVE**

### 2.3 Persist Decision

**Service:** `DecisionEngine.save_decision()`
**Таблица:** `decisions`

**Поля:**
- `id` (uuid)
- `idea_id`
- `decision` (approve/reject/defer)
- `decision_epoch`
- `created_at`

### 2.4 Persist Decision Trace

**Таблица:** `decision_traces`

**Поля:**
- `id` (uuid)
- `decision_id`
- `checks` (jsonb)
- `result`
- `created_at`

### 2.5 Emit Event

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
CREATE TABLE genomai.decisions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id         uuid NOT NULL,
  decision        text NOT NULL CHECK (decision IN ('approve', 'reject', 'defer')),
  decision_epoch  int NOT NULL DEFAULT 1,
  created_at      timestamp NOT NULL DEFAULT now()
);
```

### 3.2 Таблица decision_traces

```sql
CREATE TABLE genomai.decision_traces (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id   uuid NOT NULL,
  checks        jsonb NOT NULL,
  result        text NOT NULL,
  created_at    timestamp NOT NULL DEFAULT now()
);
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
- Decision создаётся для каждой Idea
- Decision детерминирован
- Decision Trace сохраняется
- Событие `DecisionMade` эмитится
- Все тесты проходят
- Не используется: LLM, ML, confidence

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
- risk cap превышен
- decision = defer

### Check 4 — Determinism
- одинаковый input → одинаковый decision

## 8. Выход шага

На выходе гарантировано:

**Система умеет отказывать и умеет разрешать,**
**но не умеет оптимизировать.**

## 9. Жёсткие запреты

❌ fatigue (beyond simple check)
❌ confidence
❌ ML
❌ LLM
❌ любые эвристики "качества"

## 10. Готовность к следующему шагу

Можно переходить к `05_hypothesis_factory_playbook.md`, если:
- Decisions создаются корректно
- Decision trace всегда есть
- Approve / reject / defer работают
- Все тесты проходят

## 11. Дополнительные ресурсы

- `docs/layer-1-logic/DECISION_ENGINE.md` — спецификация Decision Engine
- `docs/TEMPORAL_WORKFLOWS.md` — Temporal workflows reference
