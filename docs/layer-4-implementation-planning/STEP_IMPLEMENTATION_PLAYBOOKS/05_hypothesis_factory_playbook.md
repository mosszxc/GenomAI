# 05_hypothesis_factory_playbook.md

**STEP 05 — Hypothesis Factory (MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `04_decision_engine_playbook.md` (Decision = approve)

**Следующий шаг:** `06_telegram_output_playbook.md`

## 0. Назначение шага

Этот шаг превращает разрешённую идею в текстовые гипотезы.

Hypothesis Factory **не выбирает лучшую гипотезу**
и **не оценивает качество**.

Она просто генерирует варианты.

## 1. Входные данные

### 1.1 Источник

- событие `DecisionMade`

### 1.2 Условие запуска

- `decision === "approve"`

**Если:**
- reject → STOP
- defer → STOP

📌 **Hypothesis Factory никогда не запускается сама.**

### 1.3 Контракт входа

```json
{
  "decision_id": "uuid",
  "idea_id": "uuid",
  "decision": "approve",
  "epoch": 1
}
```

## 2. n8n Workflow

**Workflow name:** `hypothesis_factory_generate`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `DecisionMade`
- **Guard:**
  - `if (decision !== 'approve') STOP`

### 2.2 Load Idea Context

- **Node:** Supabase Select

```sql
SELECT i.id,
       dc.payload AS decomposed_payload
FROM ideas i
JOIN decomposed_creatives dc
  ON dc.creative_id = (
    SELECT creative_id
    FROM idea_creative_map
    WHERE idea_id = :idea_id
    LIMIT 1
  )
WHERE i.id = :idea_id;
```

📌 **Используется только структура, без learning.**

### 2.3 Prompt Assembly (Deterministic)

- **Node:** Function

**Вход:**
- decomposed_payload
- schema_version
- fixed prompt template (v1)

**Правила:**
- prompt version фиксирован
- никакой динамики
- никакого branching

📌 **Одинаковый input → одинаковый prompt.**

### 2.4 LLM Call (Generation Only)

- **Node:** LLM

**Инструкции:**
- "Сгенерируй N вариантов текста"
- "Не оценивай"
- "Не объясняй"
- "Не сравнивай варианты"

**Параметры:**
- `temperature = фиксированное значение` (например, 0.7)
- `N = 1–3` (фиксировано)

### 2.5 Persist Hypotheses

- **Node:** Supabase Insert (batch)
- **Таблица:** `hypotheses`

**Поля:**
- `id` (uuid)
- `idea_id`
- `decision_id`
- `prompt_version`
- `content` (text)
- `created_at`

📌 **Все варианты сохраняются.**

### 2.6 Emit Event

**HypothesisGenerated**

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "count": 3
}
```

## 3. Хранилище

### Таблица hypotheses

```sql
hypotheses (
  id              uuid primary key,
  idea_id         uuid not null,
  decision_id     uuid not null,
  prompt_version  text not null,
  content         text not null,
  created_at      timestamp not null
)
```

### Инварианты

- hypotheses append-only
- UPDATE / DELETE запрещены
- одна decision → несколько hypotheses

## 4. События

**Обязательные:**

### HypothesisGenerated

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "count": 3
}
```

**Запрещённые:**

- любые optimization events
- любые ranking events

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ Hypothesis Factory запускается только при approve
- ✅ генерируется 1–3 гипотезы
- ✅ все гипотезы сохраняются
- ✅ `HypothesisGenerated` эмитится
- ✅ не происходит:
  - отбор "лучшей"
  - фильтрация
  - скоринг

## 6. Типовые ошибки (PR-блокеры)

❌ **автоматический выбор "лучшей" гипотезы**  
❌ **динамический prompt**  
❌ **использование learning данных**  
❌ **использование performance**  
❌ **попытка оптимизировать temperature**

## 7. Ручные проверки (обязательные)

### Check 1 — Trigger guard
- Decision = reject
- workflow не запускается

### Check 2 — Happy path
- Decision = approve
- 3 гипотезы созданы
- event эмитится

### Check 3 — Determinism
- одинаковый decomposed payload
- одинаковый prompt
- одинаковая структура ответа

## 8. Выход шага

На выходе гарантировано:

**Есть набор текстовых гипотез,**
**без понимания, какая из них лучше.**

## 9. Жёсткие запреты

❌ ranking  
❌ scoring  
❌ learning  
❌ performance-based logic  
❌ "умные" эвристики

## 10. Готовность к следующему шагу

Можно переходить к `06_telegram_output_playbook.md`, если:
- ✅ hypotheses стабильно создаются
- ✅ нет скрытой логики отбора
- ✅ события эмитятся корректно
