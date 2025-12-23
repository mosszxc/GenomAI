# Render MCP Setup - Настройка авторизации

**Дата создания:** 2025-01-22  
**Статус:** ⚠️ Требуется настройка авторизации

## 🚨 Проблема

При попытке создать сервис через Render MCP получаем ошибку:
```
unauthorized
```

**Workspace выбран:** `tea-d54u5v0gjchc7385epk0` ✅

## 🔧 Решение: Настройка Render API Token

### Шаг 1: Получить Render API Token

1. Откройте [Render Dashboard](https://dashboard.render.com)
2. Перейдите в **Account Settings** → **API Keys**
3. Нажмите **Create API Key**
4. Дайте имя ключу (например, "GenomAI MCP")
5. Скопируйте созданный токен

### Шаг 2: Настроить Render MCP в Cursor

Render MCP требует настройки через переменные окружения или конфигурацию MCP сервера.

**Вариант A: Через переменные окружения**

Добавьте в настройки Cursor MCP:

```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-render"
      ],
      "env": {
        "RENDER_API_KEY": "your-render-api-token-here"
      }
    }
  }
}
```

**Вариант B: Через конфигурацию MCP сервера**

Если используете отдельный MCP сервер, настройте его с Render API Token.

### Шаг 3: Проверка

После настройки проверьте доступ:

```typescript
// Должно работать без ошибки "unauthorized"
const services = await mcp_render_list_services();
```

## 📋 Текущий статус

- ✅ Workspace выбран: `tea-d54u5v0gjchc7385epk0`
- ⚠️ Требуется Render API Token для создания сервисов
- ⚠️ Требуется настройка Render MCP в Cursor

## 🚀 После настройки

После настройки Render API Token, выполните:

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

## 📚 Дополнительная информация

- [Render API Documentation](https://render.com/docs/api)
- [Render MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/render)

---

**Следующий шаг:** Настройте Render API Token в Cursor MCP конфигурации.

