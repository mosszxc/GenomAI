# n8n Setup Guide

**Версия:** v1.0  
**Статус:** ACTIVE  
**Задача:** Настройка n8n instance для GenomAI

## 📋 Обзор

Этот документ содержит инструкции по настройке n8n для работы с GenomAI системой.

## ✅ Текущий статус

- **n8n Instance:** `https://kazamaqwe.app.n8n.cloud`
- **n8n Version:** 1.123.5
- **API Status:** ✅ Connected
- **Management Tools:** ✅ Enabled
- **Project:** Unighaz (все новые workflow создаются здесь)
- **Legacy Workflows:** Все старые workflow помечены префиксом "Legacy -"
- **Test Workflow Created:** ✅ `Test Supabase Connection` (ID: `cpaFx4dhT5gQBB4C`)

## ✅ Экспонирование схемы genomai

**Статус:** ✅ Выполнено

- ✅ Права доступа выданы (миграция `expose_genomai_schema`)
- ✅ Схема `genomai` добавлена в "Exposed schemas" в Dashboard
- ✅ Схема `genomai` доступна через Supabase API

Подробнее: см. [SUPABASE_SCHEMA_EXPOSURE.md](./SUPABASE_SCHEMA_EXPOSURE.md)

## 🔑 Шаг 1: Настройка Supabase Credentials в n8n

### Supabase API Connection (рекомендуется)

1. В n8n Dashboard → **Credentials** → **Add Credential**
2. Выберите **Supabase**
3. Заполните форму:

```
Name: GenomAI Supabase API
Host: https://ftrerelppsnbdcmtcwya.supabase.co
Service Role Secret: [ваш service_role key]
```

**⚠️ ВАЖНО:** 
- Используйте `service_role` key для полного доступа (чтение и запись)
- Для production рекомендуется использовать отдельные credentials с ограниченными правами

## 📊 Шаг 2: Проверка подключения

### Тест Supabase подключения:

1. Используйте готовый workflow `Test Supabase Connection` (ID: `cpaFx4dhT5gQBB4C`)
2. Или создайте новый workflow:
   - Добавьте **Supabase** node
   - Выберите credential "GenomAI Supabase API"
   - Настройте:
     - Operation: Get Many
     - Use Custom Schema: enabled
     - Schema: `genomai`
     - Table: `event_log`
3. Запустите workflow
4. Ожидаемый результат: успешное чтение данных из `genomai.event_log`

## 🔧 Шаг 3: Настройка базовых workflow templates

### 3.1 Webhook для Ingestion (STEP 01)

**Название workflow:** `Creative Ingestion Webhook` (новый, актуальный)

**Endpoint:** `/ingest/creative`

**Метод:** POST

**Payload:**
```json
{
  "video_url": "https://...",
  "tracker_id": "KT-123456",
  "source_type": "user"
}
```

**Workflow структура:**
1. Webhook Trigger → `/ingest/creative`
2. Validate Payload (IF node)
3. Insert into `genomai.event_log` (emit CreativeReferenceReceived)
4. Insert into `genomai.creatives` (если таблица будет создана)
5. Return response

### 3.2 Daily Scan Workflow (STEP 07)

**Название workflow:** `Daily Metrics Scan` (новый, актуальный)

**Триггер:** Cron (1 раз в день, например, 00:01 UTC)

**Workflow структура:**
1. Cron Trigger
2. Pull metrics from Keitaro
3. Insert into `genomai.raw_metrics_current`
4. Create `genomai.daily_metrics_snapshot`
5. Emit `DailyMetricsSnapshotCreated` event

## 📝 Шаг 4: Environment Variables в n8n

Настройте следующие переменные окружения в n8n (если поддерживается):

```bash
# Supabase
SUPABASE_URL=https://ftrerelppsnbdcmtcwya.supabase.co
SUPABASE_ANON_KEY=[anon key]
SUPABASE_SERVICE_ROLE_KEY=[service_role key]

# Database
DATABASE_HOST=db.ftrerelppsnbdcmtcwya.supabase.co
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=postgres
DATABASE_PASSWORD=[password]

# Schema
GENOMAI_SCHEMA=genomai
```

## 🔗 Шаг 5: Webhook URLs

После создания workflows, n8n автоматически сгенерирует webhook URLs:

**Формат:** `https://kazamaqwe.app.n8n.cloud/webhook/[workflow-id]/[webhook-path]`

**Примеры:**
- Ingestion: `https://kazamaqwe.app.n8n.cloud/webhook/abc123/ingest/creative`
- (другие webhooks будут добавлены по мере создания workflows)

## 🧪 Шаг 6: Тестовый Workflow

Создан тестовый workflow для проверки подключения:

- **Name:** `Test Supabase Connection` (новый, актуальный)
- **ID:** `cpaFx4dhT5gQBB4C`
- **Status:** Неактивен (требует настройки credential)

**Для использования:**
1. Откройте workflow в n8n Dashboard (проект Unighaz)
2. Настройте Supabase credential в node "Test GenomAI Schema"
3. Выберите credential "GenomAI Supabase API" (создайте его по инструкции выше)
4. Сохраните workflow
5. Запустите вручную через Manual Trigger
6. Проверьте результат - должно вернуться успешное чтение данных из `genomai.event_log`

## 📚 Шаг 7: Полезные n8n Nodes для GenomAI

### Основные nodes:

1. **Supabase** - для работы с Supabase (чтение/запись данных) ⭐ **РЕКОМЕНДУЕТСЯ**
2. **Webhook** - для приема входящих запросов
3. **Cron** - для scheduled workflows (daily scan)
4. **IF** - для валидации и условий
5. **Set** - для формирования payload'ов
6. **Code** - для кастомной логики (если нужно)
7. **Function** - для трансформаций данных

### Специализированные nodes:

- **OpenAI** / **Anthropic** - для LLM вызовов (decomposition, hypothesis generation)
- **Telegram** - для отправки сообщений (STEP 06)
- **Keitaro** - если есть готовый node, или HTTP Request

## ✅ Шаг 8: Чеклист готовности

- [ ] Supabase credential создан и протестирован
- [ ] Тестовый workflow `Test Supabase Connection` выполнен успешно
- [ ] Подключение к схеме `genomai` работает через Supabase node
- [ ] Webhook endpoint для ingestion настроен
- [ ] Environment variables настроены (если поддерживается)
- [ ] Базовые workflow templates созданы (в проекте Unighaz)
- [ ] Доступ к n8n API проверен
- [ ] Все новые workflow создаются в проекте Unighaz (без префикса, просто актуальные)

## 🐛 Troubleshooting

### Ошибка: "401 Unauthorized" или "permission denied"
- Проверьте правильность Service Role Secret
- Убедитесь, что используете правильный credential
- Проверьте, что API key имеет доступ к схеме `genomai`

### Ошибка: "relation does not exist" или "table not found"
- Убедитесь, что миграции применены
- Проверьте, что включена опция "Use Custom Schema"
- Убедитесь, что указана правильная схема: `genomai`
- Проверьте правильность имени таблицы
- ⚠️ **ВАЖНО:** Убедитесь, что схема `genomai` добавлена в "Exposed schemas" в Supabase Dashboard (Settings → API → Data API Settings → Exposed schemas)
- Проверьте, что права доступа выданы (миграция `expose_genomai_schema` применена)

### Webhook не работает
- Проверьте, что workflow активирован
- Убедитесь, что webhook node правильно настроен
- Проверьте URL webhook в n8n dashboard

## 📚 Дополнительные ресурсы

- [n8n Documentation](https://docs.n8n.io/)
- [Supabase REST API](https://supabase.com/docs/reference/javascript/introduction)
- [PostgreSQL Node in n8n](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.postgres/)

## 📋 Важные замечания

### Использование схемы `genomai` в Supabase Node

При работе с Supabase node в n8n:

**Правильно:**
1. Включите опцию **"Use Custom Schema"**
2. Укажите схему: `genomai`
3. Выберите таблицу из списка или введите имя

**Пример настройки:**
- Use Custom Schema: ✅ enabled
- Schema: `genomai`
- Table: `event_log`

**Неправильно:**
- Использование схемы `public` (таблицы GenomAI находятся в `genomai`)
- Отключенная опция "Use Custom Schema" (не найдет таблицы в `genomai`)

## 🎯 Следующие шаги

После настройки n8n:
1. Агент 1 может начать создавать workflows для STEP 01
2. Webhook endpoints будут готовы для интеграции с Telegram Bot
3. Scheduled workflows можно настроить для daily scan

## 📝 Примечания

- Все таблицы GenomAI находятся в схеме `genomai`
- Используйте полные имена таблиц: `genomai.event_log`, `genomai.ideas`, etc.
- Для событий используйте функцию `genomai.emit_event()`
- Старые таблицы находятся в `public` с префиксом `legacy_`

