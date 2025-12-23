# Decision Engine Migration to Render — Full Analysis

**Версия:** v1.0  
**Статус:** MIGRATION PLAN  
**Дата:** 2025-12-23  
**Приоритет:** Высокий

## 📋 Executive Summary

Миграция Decision Engine с n8n workflow на отдельный REST API сервис на Render.

**Текущее состояние:**
- Decision Engine реализован как n8n workflow (`decision_engine_mvp`, ID: `YT2d7z5h9bPy1R4v`)
- Работает на n8n cloud
- Stateless, детерминированный
- Запускается по событию `IdeaRegistered`

**Целевое состояние:**
- Decision Engine как REST API сервис на Render
- n8n workflow вызывает API вместо локальной логики
- Сохранение всех архитектурных принципов
- Улучшенная тестируемость и масштабируемость

---

## 🎯 Цели миграции

1. **Независимость от n8n** — возможность тестировать и масштабировать отдельно
2. **Производительность** — быстрее, чем n8n workflow
3. **Тестируемость** — unit-тесты, integration-тесты
4. **Версионирование** — код в Git, версионирование правил
5. **Контроль** — полный контроль над логикой Decision Engine

---

## 📊 Текущая архитектура

### Текущий workflow (n8n)

```
IdeaRegistered Event
    ↓
Load Idea (Supabase)
    ↓
Idea Found Check (IF)
    ↓
Hard Constraints Check (Function)
    ↓
Decision Output
    ↓
Persist Decision (Supabase)
    ↓
Persist Decision Trace (Supabase)
    ↓
Emit DecisionMade Event
```

### Текущие проверки (MVP)

1. **Idea exists** — проверка наличия
2. **No HARD_DEAD** — `status = 'dead'` → reject
3. **No active global ban** — заглушка (always false)
4. **Basic risk cap** — `max_active_ideas = 100` → defer если превышено

---

## 🏗️ Новая архитектура (Render)

### Архитектура сервиса

```
Render Service (Python/FastAPI)
    ↓
POST /api/decision
    ↓
Load Idea + System State (Supabase)
    ↓
Execute Decision Logic
    ↓
Persist Decision + Trace (Supabase)
    ↓
Return Decision Response
```

### n8n workflow (обновленный)

```
IdeaRegistered Event
    ↓
Load Idea (Supabase) - для передачи в API
    ↓
HTTP Request → Render API
    ↓
Handle Response
    ↓
Emit DecisionMade Event (если нужно)
```

---

## 📦 Структура проекта

```
decision-engine-service/
├── main.py                    # FastAPI application entry point
├── src/
│   ├── routes/
│   │   └── decision.py        # POST /api/decision route
│   ├── services/
│   │   ├── decision_engine.py  # Core decision logic
│   │   └── supabase.py        # Supabase client
│   ├── checks/
│   │   ├── __init__.py
│   │   ├── schema_validity.py
│   │   ├── death_memory.py
│   │   ├── fatigue_constraint.py
│   │   ├── risk_budget.py
│   │   ├── pseudo_novelty.py (future)
│   │   ├── context_validity.py (future)
│   │   ├── horizon_compatibility.py (future)
│   │   ├── diversity_control.py (future)
│   │   └── epistemic_shock.py (future)
│   └── utils/
│       ├── validators.py
│       └── errors.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .env.example
└── README.md
```

---

## 🔌 API Контракт

### POST /api/decision

**Request:**
```json
{
  "idea_id": "uuid",
  "idea": {
    "id": "uuid",
    "canonical_hash": "string",
    "active_cluster_id": "uuid",
    "angle_type": "enum",
    "core_belief": "enum",
    "promise_type": "enum",
    "state_before": "enum",
    "state_after": "enum",
    "context_frame": "enum",
    "status": "string",
    "risk_level": "enum",
    "horizon": "enum"
  },
  "system_state": {
    "current_state": "enum",
    "risk_budget": "number",
    "max_active_ideas": 100
  },
  "fatigue_state": {
    "idea_id": "uuid",
    "fatigue_level": "enum"
  },
  "death_memory": {
    "idea_id": "uuid",
    "is_dead": "boolean"
  }
}
```

**Response (Success):**
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "idea_id": "uuid",
    "decision_type": "APPROVE" | "REJECT" | "DEFER" | "ALLOW_WITH_CONSTRAINTS",
    "decision_reason": "string",
    "passed_checks": ["check1", "check2"],
    "failed_checks": [],
    "failed_check": null,
    "dominant_constraint": null,
    "cluster_at_decision": "uuid",
    "horizon": "enum",
    "system_state": "enum",
    "policy_version": "v1.0",
    "timestamp": "2025-01-01T00:00:00Z"
  },
  "decision_trace": {
    "id": "uuid",
    "decision_id": "uuid",
    "checks": [
      {
        "check_name": "schema_validity",
        "order": 1,
        "result": "PASSED",
        "details": {}
      }
    ],
    "result": "APPROVE",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": {
    "code": "IDEA_NOT_FOUND" | "INVALID_INPUT" | "SUPABASE_ERROR" | "INTERNAL_ERROR",
    "message": "string",
    "details": {}
  }
}
```

---

## 🔄 Процесс миграции

### Этап 1: Подготовка

1. ✅ Создать структуру проекта
2. ✅ Настроить Supabase client
3. ✅ Создать базовый Express server
4. ✅ Настроить environment variables

### Этап 2: Реализация Decision Logic

1. ✅ Реализовать все 9 checks (для MVP только 4)
2. ✅ Реализовать Decision Resolution Logic
3. ✅ Реализовать Decision Trace generation
4. ✅ Добавить валидацию входных данных

### Этап 3: Интеграция с Supabase

1. ✅ Реализовать чтение Idea из Supabase
2. ✅ Реализовать чтение System State
3. ✅ Реализовать запись Decision
4. ✅ Реализовать запись Decision Trace

### Этап 4: Тестирование

1. ✅ Unit-тесты для каждого check
2. ✅ Integration-тесты с Supabase
3. ✅ E2E тесты полного flow
4. ✅ Тесты детерминированности

### Этап 5: Деплой на Render

1. ✅ Создать Render service
2. ✅ Настроить environment variables
3. ✅ Настроить health check endpoint
4. ✅ Протестировать в production

### Этап 6: Обновление n8n workflow

1. ✅ Обновить workflow для вызова Render API
2. ✅ Добавить обработку ошибок
3. ✅ Добавить retry механизм
4. ✅ Протестировать интеграцию

### Этап 7: Обновление документации

1. ✅ Обновить TECH_DECISIONS.md (v1.3)
2. ✅ Обновить 04_decision_engine_playbook.md
3. ✅ Обновить SERVICE_BOUNDARIES.md
4. ✅ Обновить API_CONTRACTS.md

---

## 🧪 Тестирование

### Unit Tests

```python
# tests/unit/checks/test_schema_validity.py
import pytest
from src.checks.schema_validity import schema_validity

def test_schema_validity_pass_for_valid_idea():
    """Should PASS for valid idea"""
    # ...
    
def test_schema_validity_reject_for_invalid_idea():
    """Should REJECT for invalid idea"""
    # ...
```

### Integration Tests

```python
# tests/integration/test_decision_engine.py
import pytest
from src.services.decision_engine import make_decision

@pytest.mark.asyncio
async def test_decision_engine_persist_to_supabase():
    """Should make decision and persist to Supabase"""
    # ...
```

### E2E Tests

```python
# tests/e2e/test_full_flow.py
import pytest

@pytest.mark.asyncio
async def test_full_decision_flow():
    """Should handle IdeaRegistered event end-to-end"""
    # ...
```

---

## 🔒 Безопасность

1. **API Key Authentication** — Render API защищен API key
2. **Input Validation** — валидация всех входных данных
3. **Error Handling** — безопасная обработка ошибок
4. **Rate Limiting** — защита от перегрузки
5. **Logging** — логирование всех решений

---

## 📈 Мониторинг

1. **Health Check** — `GET /health`
2. **Metrics** — количество решений, время выполнения
3. **Logging** — все решения логируются
4. **Alerts** — алерты на ошибки

---

## 🚀 Деплой на Render

### render.yaml

```yaml
services:
  - type: web
    name: decision-engine-service
    env: python
    rootDir: decision-engine-service
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    region: frankfurt
    plan: free
    envVars:
      - key: PORT
        value: "10000"
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: API_KEY
        generateValue: true
```

### Environment Variables

```bash
PORT=10000
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
API_KEY=generated_key
```

---

## 📝 Чеклист миграции

- [ ] Создать структуру проекта
- [ ] Реализовать Decision Engine logic
- [ ] Реализовать Supabase integration
- [ ] Написать тесты
- [ ] Деплой на Render
- [ ] Обновить n8n workflow
- [ ] Обновить TECH_DECISIONS.md (v1.3)
- [ ] Обновить 04_decision_engine_playbook.md
- [ ] Обновить SERVICE_BOUNDARIES.md
- [ ] Обновить API_CONTRACTS.md
- [ ] Протестировать полный flow
- [ ] Документировать API

---

## ⚠️ Риски и митигация

### Риск 1: Нарушение детерминированности
**Митигация:** Строгие тесты детерминированности, версионирование правил

### Риск 2: Проблемы с производительностью
**Митигация:** Мониторинг, оптимизация запросов к Supabase

### Риск 3: Проблемы с интеграцией n8n
**Митигация:** Retry механизм, обработка ошибок

### Риск 4: Потеря данных
**Митигация:** Транзакции, идемпотентность

---

## 🎯 Definition of Done

Миграция считается завершенной, если:

- ✅ Decision Engine работает на Render
- ✅ n8n workflow вызывает Render API
- ✅ Все тесты проходят
- ✅ Документация обновлена
- ✅ Полный flow протестирован
- ✅ Мониторинг настроен
- ✅ Старый n8n workflow отключен

---

## 📚 Связанные документы

- `TECH_DECISIONS.md` — технологические решения
- `04_decision_engine_playbook.md` — playbook реализации
- `DECISION_ENGINE.md` — спецификация Decision Engine
- `SERVICE_BOUNDARIES.md` — границы сервисов
- `API_CONTRACTS.md` — API контракты

