# External API Configuration

## Keitaro API

**Config Table:** `genomai.keitaro_config`

| Field | Type | Description |
|-------|------|-------------|
| domain | TEXT | Base URL (e.g., `https://uniaffzhb.com`) |
| api_key | TEXT | API key для заголовка `Api-Key` |
| is_active | BOOL | Активна ли конфигурация |

### Проверка работоспособности

```bash
curl -s -w "\nHTTP:%{http_code}" \
  "https://DOMAIN/admin_api/v1/campaigns?limit=1" \
  -H "Api-Key: API_KEY"
```

### Частые проблемы

| Код | Причина | Решение |
|-----|---------|---------|
| 401 | Неверный API key или домен | Проверить актуальный домен/ключ |
| 404 | Неверный endpoint | Проверить версию API |
| 5xx | Сервер недоступен | Подождать / связаться с поддержкой |

### История изменений доменов

| Дата | Старый домен | Новый домен |
|------|--------------|-------------|
| 2026-01-03 | uniaffburan.com | uniaffzhb.com |

## Decision Engine API

**Base URL:** `https://genomai.onrender.com`
**Endpoints:**
- `GET /health` - Health check
- `POST /api/decision/` - Make decision
- `POST /learning/process` - Process learning

**Cold Start:** ~85 сек на Render Free Tier

## Best Practices

1. **Хранить конфиги в БД** - не в env vars (n8n Cloud блокирует $env)
2. **Health checks** - добавить в Pipeline Health Monitor
3. **Retry logic** - для cold start сервисов
4. **Документировать изменения** - записывать смену доменов/ключей
