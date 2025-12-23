# GenomAI Deployment Guide - Render

**Дата создания:** 2025-01-22  
**Статус:** 🚧 Требуется выбор workspace

## 🎯 Цель

Деплой Decision Engine Service на Render через Render MCP.

## 📋 Текущее состояние

### ✅ Готово:
- ✅ Конфигурация `decision-engine-service/render.yaml`
- ✅ Код сервиса готов
- ✅ Dockerfile настроен
- ✅ Health check endpoint (`/health`)
- ✅ Environment variables определены

### ⚠️ Требуется:
- ⚠️ **Выбрать workspace в Render** (через Render Dashboard или MCP)
- ⚠️ Настроить environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, API_KEY)

## 🚀 Пошаговая инструкция

### Шаг 1: Выбор Workspace

**Вариант A: Через Render Dashboard**
1. Откройте [Render Dashboard](https://dashboard.render.com)
2. Выберите нужный workspace/team
3. Скопируйте `ownerID` из URL или настроек

**Вариант B: Через MCP (после авторизации)**
```typescript
// Получить список workspace
const workspaces = await mcp_render_list_workspaces();

// Выбрать workspace (только после подтверждения пользователя)
await mcp_render_select_workspace({ ownerID: "owner-id" });
```

### Шаг 2: Создание Web Service

После выбора workspace, выполните:

```typescript
await mcp_render_create_web_service({
  name: "decision-engine-service",
  runtime: "node",
  buildCommand: "cd decision-engine-service && npm install",
  startCommand: "cd decision-engine-service && npm start",
  repo: "https://github.com/mosszxc/GenomAI",
  branch: "main",
  region: "frankfurt",
  plan: "starter",
  autoDeploy: "yes",
  envVars: [
    { key: "NODE_ENV", value: "production" },
    { key: "PORT", value: "10000" }
  ]
});
```

### Шаг 3: Настройка Environment Variables

После создания сервиса, настройте секретные переменные:

```typescript
await mcp_render_update_environment_variables({
  serviceId: "srv-xxx", // ID созданного сервиса
  envVars: [
    { key: "SUPABASE_URL", value: "https://xxxxx.supabase.co" },
    { key: "SUPABASE_SERVICE_ROLE_KEY", value: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." },
    { key: "API_KEY", value: "your-generated-api-key" }
  ],
  replace: false // merge с существующими
});
```

### Шаг 4: Проверка деплоя

```typescript
// Проверить статус сервиса
const service = await mcp_render_get_service({
  serviceId: "srv-xxx"
});

// Проверить последние деплои
const deploys = await mcp_render_list_deploys({
  serviceId: "srv-xxx",
  limit: 5
});

// Проверить логи
const logs = await mcp_render_list_logs({
  resource: ["srv-xxx"],
  level: ["error", "warn"],
  limit: 50
});
```

## 📝 Конфигурация сервиса

### Из `render.yaml`:

```yaml
services:
  - type: web
    name: decision-engine-service
    env: node
    buildCommand: npm install
    startCommand: npm start
    healthCheckPath: /health
    envVars:
      - key: NODE_ENV
        value: production
      - key: PORT
        value: 10000
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: API_KEY
        generateValue: true
```

### Параметры деплоя:

- **Runtime:** Node.js 18+
- **Build Command:** `cd decision-engine-service && npm install`
- **Start Command:** `cd decision-engine-service && npm start`
- **Port:** 10000
- **Health Check:** `/health`
- **Region:** Frankfurt (по умолчанию)
- **Plan:** Starter (можно изменить на Standard/Pro)

## 🔐 Environment Variables

### Обязательные переменные:

1. **NODE_ENV** = `production`
2. **PORT** = `10000`
3. **SUPABASE_URL** = URL вашего Supabase проекта
4. **SUPABASE_SERVICE_ROLE_KEY** = Service Role Key из Supabase
5. **API_KEY** = Секретный ключ для аутентификации API (можно сгенерировать)

### Где взять Supabase credentials:

1. Откройте [Supabase Dashboard](https://app.supabase.com)
2. Выберите проект GenomAI
3. Settings → API
4. Скопируйте:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`

## 🧪 Тестирование после деплоя

### 1. Health Check

```bash
curl https://decision-engine-service.onrender.com/health
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-22T12:00:00.000Z"
}
```

### 2. API Endpoint

```bash
curl -X POST https://decision-engine-service.onrender.com/api/decision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "idea": {
      "id": "test-idea-1",
      "schema_version": "1.0",
      "content": {...}
    },
    "context": {...}
  }'
```

## 📊 Мониторинг

### Метрики

```typescript
const metrics = await mcp_render_get_metrics({
  resourceId: "srv-xxx",
  metricTypes: [
    "cpu_usage",
    "memory_usage",
    "http_request_count",
    "http_latency"
  ],
  resolution: 300, // 5 минут
  startTime: "2025-01-22T00:00:00Z",
  endTime: "2025-01-22T23:59:59Z"
});
```

### Логи

```typescript
const logs = await mcp_render_list_logs({
  resource: ["srv-xxx"],
  level: ["error"],
  limit: 100
});
```

## 🔄 Обновление сервиса

### Автоматический деплой

Если `autoDeploy: "yes"`, Render автоматически задеплоит изменения при push в `main` branch.

### Ручной деплой

1. Сделайте изменения в коде
2. Commit и push в GitHub
3. Render автоматически начнет новый деплой
4. Проверьте статус через `list_deploys`

## ⚠️ Troubleshooting

### Проблема: "no workspace set"

**Решение:** Выберите workspace через Render Dashboard или MCP:
```typescript
await mcp_render_select_workspace({ ownerID: "your-owner-id" });
```

### Проблема: "unauthorized"

**Решение:** Проверьте настройки Render MCP credentials в Cursor.

### Проблема: Сервис не запускается

**Проверьте:**
1. Логи через `list_logs`
2. Environment variables через `get_service`
3. Build logs в Render Dashboard

### Проблема: Health check не проходит

**Проверьте:**
1. Правильность `healthCheckPath: /health`
2. Что сервер слушает на правильном порту
3. Логи ошибок

## 📚 Связанная документация

- [Render MCP Intro](./RENDER_MCP_INTRO.md) — Обзор Render MCP
- [Decision Engine Service README](../decision-engine-service/README.md) — Документация сервиса
- [Decision Engine Migration](../docs/layer-4-implementation-planning/DECISION_ENGINE_RENDER_MIGRATION.md) — План миграции

## ✅ Чеклист деплоя

- [ ] Выбран workspace в Render
- [ ] Создан web service через MCP
- [ ] Настроены environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, API_KEY)
- [ ] Проверен health check endpoint
- [ ] Протестирован API endpoint
- [ ] Настроен мониторинг метрик
- [ ] Проверены логи на ошибки

---

**Следующий шаг:** Выберите workspace в Render и выполните команду создания сервиса через MCP.

