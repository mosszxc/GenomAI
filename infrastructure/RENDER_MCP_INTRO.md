# Render MCP Integration - Интро

**Дата создания:** 2025-01-22  
**Статус:** ✅ Активно используется

## 🎯 Что такое Render MCP?

Render MCP (Model Context Protocol) — это интеграция Render.com с Cursor AI, которая позволяет управлять инфраструктурой Render прямо из Cursor через MCP инструменты.

### Возможности:

- ✅ **Управление сервисами** — создание, обновление, мониторинг web services
- ✅ **Управление базами данных** — создание и управление Postgres инстансами
- ✅ **Управление Key-Value stores** — создание Redis-подобных хранилищ
- ✅ **Static Sites** — деплой статических сайтов
- ✅ **Мониторинг** — метрики, логи, статусы деплоев
- ✅ **Environment Variables** — управление переменными окружения

## 📋 Доступные инструменты

### Управление сервисами

```typescript
// Список всех сервисов
mcp_render_list_services()

// Получить детали сервиса
mcp_render_get_service({ serviceId: "srv-xxx" })

// Создать web service
mcp_render_create_web_service({
  name: "my-service",
  runtime: "node",
  buildCommand: "npm install",
  startCommand: "npm start",
  repo: "https://github.com/user/repo"
})

// Обновить web service
mcp_render_update_web_service({ serviceId: "srv-xxx" })

// Обновить environment variables
mcp_render_update_environment_variables({
  serviceId: "srv-xxx",
  envVars: [
    { key: "API_KEY", value: "secret" }
  ]
})
```

### Управление базами данных

```typescript
// Список всех Postgres инстансов
mcp_render_list_postgres_instances()

// Получить детали БД
mcp_render_get_postgres({ postgresId: "dpg-xxx" })

// Создать Postgres инстанс
mcp_render_create_postgres({
  name: "genomai-db",
  plan: "free",
  region: "oregon",
  version: 16
})

// Выполнить SQL запрос (read-only)
mcp_render_query_render_postgres({
  postgresId: "dpg-xxx",
  sql: "SELECT * FROM genomai.ideas LIMIT 10"
})
```

### Мониторинг и логи

```typescript
// Получить метрики сервиса
mcp_render_get_metrics({
  resourceId: "srv-xxx",
  metricTypes: ["cpu_usage", "memory_usage", "http_request_count"],
  startTime: "2025-01-22T00:00:00Z",
  endTime: "2025-01-22T23:59:59Z"
})

// Получить логи
mcp_render_list_logs({
  resource: ["srv-xxx"],
  level: ["error", "warn"],
  limit: 100
})

// Список деплоев
mcp_render_list_deploys({
  serviceId: "srv-xxx",
  limit: 10
})

// Детали деплоя
mcp_render_get_deploy({
  serviceId: "srv-xxx",
  deployId: "dep-xxx"
})
```

### Управление workspace

```typescript
// Список доступных workspace
mcp_render_list_workspaces()

// Выбрать workspace (требует подтверждения пользователя)
mcp_render_select_workspace({ ownerID: "owner-id" })

// Получить текущий workspace
mcp_render_get_selected_workspace()
```

## 🚀 Текущее состояние проекта GenomAI

### Decision Engine Service

**Файл конфигурации:** `decision-engine-service/render.yaml`

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

**Статус:** Готов к деплою через Render MCP

## 📝 Примеры использования

### 1. Создание Decision Engine Service

```typescript
// Создать web service для Decision Engine
await mcp_render_create_web_service({
  name: "decision-engine-service",
  runtime: "node",
  buildCommand: "npm install",
  startCommand: "npm start",
  repo: "https://github.com/mosszxc/GenomAI",
  branch: "main",
  region: "frankfurt",
  plan: "starter",
  envVars: [
    { key: "NODE_ENV", value: "production" },
    { key: "PORT", value: "10000" },
    { key: "SUPABASE_URL", value: "{{SUPABASE_URL}}" },
    { key: "SUPABASE_SERVICE_ROLE_KEY", value: "{{SUPABASE_KEY}}" },
    { key: "API_KEY", value: "{{API_KEY}}" }
  ],
  autoDeploy: "yes"
});
```

### 2. Мониторинг сервиса

```typescript
// Проверить статус сервиса
const service = await mcp_render_get_service({
  serviceId: "srv-xxx"
});

// Получить метрики за последний час
const metrics = await mcp_render_get_metrics({
  resourceId: "srv-xxx",
  metricTypes: ["cpu_usage", "memory_usage", "http_request_count", "http_latency"],
  resolution: 300 // 5 минут
});

// Проверить последние ошибки
const errorLogs = await mcp_render_list_logs({
  resource: ["srv-xxx"],
  level: ["error"],
  limit: 50
});
```

### 3. Обновление environment variables

```typescript
// Обновить API ключ
await mcp_render_update_environment_variables({
  serviceId: "srv-xxx",
  envVars: [
    { key: "API_KEY", value: "new-secret-key" }
  ],
  replace: false // merge с существующими
});
```

### 4. Создание Postgres для тестирования

```typescript
// Создать тестовую БД
await mcp_render_create_postgres({
  name: "genomai-test-db",
  plan: "free",
  region: "frankfurt",
  version: 16
});

// Выполнить миграции (через Supabase MCP или напрямую)
// Затем проверить данные
const result = await mcp_render_query_render_postgres({
  postgresId: "dpg-xxx",
  sql: "SELECT COUNT(*) FROM genomai.ideas"
});
```

## ⚠️ Важные замечания

### Workspace Selection

**КРИТИЧЕСКИ ВАЖНО:** Перед работой с Render MCP нужно выбрать workspace:

```typescript
// 1. Получить список workspace
const workspaces = await mcp_render_list_workspaces();

// 2. Попросить пользователя выбрать workspace
// 3. Выбрать workspace (только после подтверждения пользователя)
await mcp_render_select_workspace({ ownerID: "owner-id" });
```

**Правило:** НИКОГДА не выбирать workspace автоматически — это может быть деструктивно!

### Environment Variables

- **`sync: false`** в `render.yaml` означает, что переменная не синхронизируется автоматически
- Используйте `mcp_render_update_environment_variables` для обновления
- **`generateValue: true`** означает, что Render сгенерирует значение автоматически

### Регионы

Доступные регионы:
- `frankfurt` (по умолчанию для GenomAI)
- `oregon`
- `singapore`
- `ohio`
- `virginia`

**Правило:** Всегда использовать `frankfurt` для деплоя GenomAI сервисов.

### Планы сервисов

- **Web Services:** `starter`, `standard`, `pro`, `pro_max`, `pro_plus`, `pro_ultra`
- **Postgres:** `free`, `basic_256mb`, `basic_1gb`, `basic_4gb`, `pro_*`, `accelerated_*`
- **Key-Value:** `free`, `starter`, `standard`, `pro`, `pro_plus`

## 🔄 Workflow использования

### Типичный workflow:

1. **Выбрать workspace** (если не выбран)
2. **Проверить существующие сервисы** через `list_services`
3. **Создать/обновить сервис** через `create_web_service` / `update_web_service`
4. **Настроить environment variables** через `update_environment_variables`
5. **Мониторить деплой** через `list_deploys` и `get_deploy`
6. **Проверить логи** через `list_logs` при ошибках
7. **Мониторить метрики** через `get_metrics` для производительности

## 📚 Связанная документация

- `decision-engine-service/README.md` — документация Decision Engine Service
- `decision-engine-service/render.yaml` — конфигурация Render
- `docs/layer-4-implementation-planning/DECISION_ENGINE_RENDER_MIGRATION.md` — план миграции

## 🎯 Следующие шаги

1. ✅ **Выбрать workspace** в Render
2. ✅ **Создать Decision Engine Service** через MCP
3. ✅ **Настроить environment variables**
4. ✅ **Проверить деплой и логи**
5. ✅ **Настроить мониторинг метрик**

## 💡 Полезные команды

```bash
# В Cursor можно использовать:
"Создай Decision Engine Service на Render"
"Покажи метрики сервиса за последний час"
"Обнови API_KEY в environment variables"
"Проверь последние ошибки в логах"
"Создай тестовую Postgres БД"
```

---

**Примечание:** Render MCP автоматически интегрирован в Cursor и готов к использованию. Все операции выполняются через MCP инструменты, что обеспечивает безопасность и контроль.

