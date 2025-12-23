# Decision Engine Service

**Версия:** v1.0  
**Статус:** IN DEVELOPMENT  
**Платформа:** Render

## 📋 Описание

REST API сервис для Decision Engine — детерминированного фильтра допустимости идей в системе GenomAI.

**Архитектура:**
- Stateless сервис (не хранит состояние между вызовами)
- Детерминированный (одинаковый input → одинаковый output)
- Все состояние загружается из Supabase при каждом вызове

## 🚀 Быстрый старт

### Установка

```bash
npm install
```

### Настройка environment variables

Создайте `.env` файл:

```bash
NODE_ENV=development
PORT=3000
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
API_KEY=your_api_key_here
```

### Запуск

```bash
# Development
npm run dev

# Production
npm start
```

## 📁 Структура проекта

```
decision-engine-service/
├── src/
│   ├── index.js              # Express server entry point
│   ├── routes/
│   │   └── decision.js       # POST /api/decision route
│   ├── services/
│   │   ├── decisionEngine.js # Core decision logic
│   │   └── supabase.js       # Supabase client
│   ├── checks/
│   │   ├── schemaValidity.js
│   │   ├── deathMemory.js
│   │   ├── fatigueConstraint.js
│   │   ├── pseudoNovelty.js
│   │   ├── contextValidity.js
│   │   ├── riskBudget.js
│   │   ├── horizonCompatibility.js
│   │   ├── diversityControl.js
│   │   └── epistemicShock.js
│   ├── models/
│   │   ├── Idea.js
│   │   ├── Decision.js
│   │   └── DecisionTrace.js
│   └── utils/
│       ├── validators.js
│       └── errors.js
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── package.json
├── Dockerfile
├── render.yaml
├── .env.example
└── README.md
```

## 🔌 API Endpoints

### POST /api/decision

Принимает решение о допустимости идеи.

**Request:** См. `API_CONTRACTS.md`

**Response:** См. `API_CONTRACTS.md`

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
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# All tests
npm test
```

## 🚀 Деплой на Render

1. Создайте новый Web Service на Render
2. Подключите GitHub репозиторий
3. Настройте environment variables
4. Render автоматически задеплоит сервис

**См. `render.yaml` для конфигурации.**

## 📚 Документация

- `DECISION_ENGINE_RENDER_MIGRATION.md` — полный план миграции
- `TECH_DECISIONS.md` (v1.3) — технологические решения
- `04_decision_engine_playbook.md` — playbook реализации
- `DECISION_ENGINE.md` — спецификация Decision Engine
- `API_CONTRACTS.md` — API контракты

## 🔒 Безопасность

- API Key authentication
- Input validation
- Error handling
- Rate limiting (опционально)

## 📈 Мониторинг

- Health check endpoint
- Logging всех решений
- Metrics (опционально)

