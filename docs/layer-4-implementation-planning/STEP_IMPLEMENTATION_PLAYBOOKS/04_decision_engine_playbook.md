# 04_decision_engine_playbook.md

**STEP 04 — Decision Engine (MVP, Skeleton)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `03_idea_registry_playbook.md` (Idea зарегистрирована)

**Следующий шаг:** `05_hypothesis_factory_playbook.md`

**⚠️ ВАЖНО:** Decision Engine мигрирован на Render. См. `DECISION_ENGINE_RENDER_MIGRATION.md` для деталей.

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

## 2. Архитектура (Render + n8n)

**Decision Engine реализован как REST API сервис на Render.**

**n8n Workflow:**
- Оркестрация: загрузка данных, вызов API, обработка ответа
- Вызывает Render API для принятия решений

**Render Service:**
- Принимает решение на основе детерминированных правил
- Сохраняет Decision и Decision Trace в Supabase
- Возвращает результат в n8n

## 3. n8n Workflow

**Workflow name:** `decision_engine_mvp`

### 3.1 Trigger

- **Node:** Event Trigger
- **Event:** `IdeaRegistered`

### 3.2 Load Idea

- **Node:** Supabase Select (operation: `getAll`)
- **Таблица:** `genomai.ideas`
- **Filters:**
  - `id` = `={{ $json.idea_id }}`

**Важно:** Supabase node с `getAll` может возвращать:
- **Объект** `{id: "...", status: "..."}` — когда найдена одна запись
- **Массив** `[{id: "...", status: "..."}]` — когда найдено несколько записей
- **Пустой массив** `[]` — когда ничего не найдено

### 3.3 Load System State

- **Node:** Supabase Select (operation: `getAll`)
- **Таблица:** `genomai.ideas`
- **Filters:**
  - `status = 'active'`
- **Count:** количество активных идей для risk cap

### 3.4 Call Render API

- **Node:** HTTP Request
- **Method:** POST
- **URL:** `={{ $env.DECISION_ENGINE_API_URL }}/api/decision`
- **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer {{ $env.DECISION_ENGINE_API_KEY }}`
- **Body:**
```json
{
  "idea_id": "={{ $json.idea_id }}",
  "idea": "={{ $('Load Idea').first().json }}",
  "system_state": {
    "current_state": "exploit",
    "risk_budget": 1000,
    "max_active_ideas": 100,
    "active_ideas_count": "={{ $('Load System State').count() }}"
  },
  "fatigue_state": {},
  "death_memory": {}
}
```

**Обработка ошибок:**
- **onError:** `continueRegularOutput`
- При ошибке → emit `DecisionAborted` event

### 3.5 Handle Response

- **Node:** IF (typeVersion: 2.3)

**Проверка успешности:**
```json
{
  "conditions": {
    "combinator": "and",
    "conditions": [
      {
        "id": "success-check",
        "leftValue": "={{ $json.success }}",
        "rightValue": true,
        "operator": {
          "type": "boolean",
          "operation": "equals"
        }
      }
    ]
  }
}
```

**Выходы:**
- **TRUE (output[0]):** → Emit DecisionMade Event
- **FALSE (output[1]):** → Emit DecisionAborted Event

### 3.6 Emit DecisionMade Event

- **Node:** Supabase Insert
- **Таблица:** `genomai.event_log`
- **Fields:**
  - `event_type`: `DecisionMade`
  - `entity_type`: `decision`
  - `entity_id`: `={{ $json.decision.decision_id }}`
  - `payload`: `={{ JSON.stringify($json.decision) }}`
  - `occurred_at`: `={{ $now }}`
  - `idempotency_key`: `={{ "decision:" + $json.decision.decision_id }}`

**Примечание:** Decision и Decision Trace уже сохранены Render API в Supabase.

## 4. Render Service Implementation

**См. `DECISION_ENGINE_RENDER_MIGRATION.md` для деталей реализации.**

**Основные компоненты:**
1. FastAPI server с endpoint `POST /api/decision`
2. Decision Engine logic (все 9 checks, для MVP только 4)
3. Supabase client для чтения/записи
4. Decision Trace generation
5. Error handling и валидация

## 5. Хранилище

**Примечание:** Decision и Decision Trace сохраняются Render API в Supabase.

### 5.1 Таблица decisions

```sql
CREATE TABLE IF NOT EXISTS genomai.decisions (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idea_id         uuid NOT NULL,
  decision        text NOT NULL CHECK (decision IN ('approve', 'reject', 'defer', 'allow_with_constraints')),
  decision_epoch  int NOT NULL DEFAULT 1,
  created_at      timestamp NOT NULL DEFAULT now()
);
```

### 5.2 Таблица decision_traces

```sql
CREATE TABLE IF NOT EXISTS genomai.decision_traces (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id   uuid NOT NULL,
  checks        jsonb NOT NULL,
  result        text NOT NULL,
  created_at    timestamp NOT NULL DEFAULT now()
);
```

## 6. События

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

## 7. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ Render service развернут и работает
- ✅ n8n workflow вызывает Render API
- ✅ Decision создаётся для каждой Idea
- ✅ Decision детерминирован
- ✅ Decision Trace сохраняется
- ✅ Событие `DecisionMade` эмитится
- ✅ Все тесты проходят (unit, integration, e2e)
- ✅ Не используется:
  - LLM
  - ML
  - confidence
  - fatigue
  - novelty

## 8. Типовые ошибки (PR-блокеры)

❌ **использование LLM**  
❌ **любые числовые скоринги**  
❌ **скрытая логика в промптах**  
❌ **отсутствие decision_trace**  
❌ **недетерминированный порядок проверок**  
❌ **кеширование состояния между вызовами**  
❌ **глобальные переменные или shared state**

## 9. Ручные проверки (обязательные)

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

## 10. Выход шага

На выходе гарантировано:

**Система умеет отказывать и умеет разрешать,**
**но не умеет оптимизировать.**

## 11. Жёсткие запреты

❌ fatigue  
❌ confidence  
❌ ML  
❌ LLM  
❌ любые эвристики "качества"  
❌ кеширование состояния  
❌ глобальные переменные

## 12. Готовность к следующему шагу

Можно переходить к `05_hypothesis_factory_playbook.md`, если:
- ✅ Render service развернут и работает
- ✅ n8n workflow вызывает Render API
- ✅ Decisions создаются корректно
- ✅ Decision trace всегда есть
- ✅ Approve / reject / defer работают
- ✅ Все тесты проходят

## 13. Дополнительные ресурсы

- `DECISION_ENGINE_RENDER_MIGRATION.md` — полный план миграции
- `TECH_DECISIONS.md` (v1.3) — технологические решения
- `DECISION_ENGINE.md` — спецификация Decision Engine


