# Decision Engine Service

**Версия:** v1.0 (Python)  
**Статус:** IN DEVELOPMENT  
**Платформа:** Render  
**Runtime:** Python 3.11+ / FastAPI

## 📋 Описание

REST API сервис для Decision Engine — детерминированного фильтра допустимости идей в системе GenomAI.

**Архитектура:**
- Stateless сервис (не хранит состояние между вызовами)
- Детерминированный (одинаковый input → одинаковый output)
- Все состояние загружается из Supabase при каждом вызове
- Реализован на Python/FastAPI

## 🚀 Быстрый старт

### Установка

```bash
pip install -r requirements.txt
```

### Настройка environment variables

Создайте `.env` файл:

```bash
PORT=10000
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
API_KEY=your_api_key_here
```

### Запуск

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 10000

# Production
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 📁 Структура проекта

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
│   │   └── risk_budget.py
│   └── utils/
│       ├── validators.py
│       └── errors.py
├── requirements.txt
├── render.yaml
└── README.md
```

## 🔌 API Endpoints

### POST /api/decision

Принимает решение о допустимости идеи.

**Headers:**
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

**Request Body:**
```json
{
  "idea_id": "uuid",
  "idea": {...},
  "system_state": {...},
  "fatigue_state": {...},
  "death_memory": {...}
}
```

**Response:**
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "idea_id": "uuid",
    "decision_type": "APPROVE|REJECT|DEFER",
    "decision_reason": "...",
    "passed_checks": [...],
    "failed_checks": [...],
    "timestamp": "2025-01-01T00:00:00Z"
  },
  "decision_trace": {...}
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## 🧪 Тестирование

```bash
# Run with pytest (when tests are added)
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 🚀 Деплой на Render

Сервис автоматически деплоится через `render.yaml`:

```yaml
services:
  - type: web
    name: decision-engine-service
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    region: frankfurt
    plan: free
```

**Настройте environment variables в Render Dashboard:**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `API_KEY`

## 📚 Документация

- `DECISION_ENGINE_RENDER_MIGRATION.md` — полный план миграции
- `TECH_DECISIONS.md` (v1.3) — технологические решения
- `04_decision_engine_playbook.md` — playbook реализации
- `DECISION_ENGINE.md` — спецификация Decision Engine
- `API_CONTRACTS.md` — API контракты

## 🔒 Безопасность

- API Key authentication (Bearer token)
- Input validation (Pydantic models)
- Error handling
- CORS middleware

## 📈 Мониторинг

- Health check endpoint (`/health`)
- Logging всех решений
- FastAPI automatic API documentation (`/docs`)

## 🔄 Миграция с Node.js

Сервис переписан с Node.js на Python:
- Express → FastAPI
- JavaScript → Python
- Все checks и логика сохранены
- API контракт остался прежним
