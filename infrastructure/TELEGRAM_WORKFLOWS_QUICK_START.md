# Telegram Workflows — Quick Start Guide

**Версия:** v1.0  
**Статус:** ACTIVE  
**Назначение:** Быстрый старт для готовых Telegram workflows

## ✅ Workflows созданы!

Два workflow уже созданы в n8n. Осталось только вставить credentials.

### Workflow 1: Telegram Creative Ingestion

**ID:** `wweHxi45m4U1vzJI`  
**Название:** `Telegram Creative Ingestion`  
**Назначение:** Приём сообщений от пользователя и передача в ingestion webhook

### Workflow 2: Telegram Hypothesis Delivery

**ID:** `kNOQ2dBE0B6OihS5`  
**Название:** `Telegram Hypothesis Delivery`  
**Назначение:** Отправка гипотез пользователю (STEP 06)

## ⚠️ КРИТИЧНО: Перемещение в проект Unighaz

**Workflows созданы, но находятся в личном проекте!** Их **ОБЯЗАТЕЛЬНО** нужно переместить в проект **"Unighaz"**.

### Быстрое перемещение:

1. Откройте n8n Dashboard
2. Найдите workflow в списке
3. Нажмите на **три точки** (⋮) → **"Move to Project"** → **"Unighaz"**

**Или:**
1. Откройте workflow в редакторе
2. Нажмите на **название проекта** (вверху, рядом с названием workflow)
3. Выберите **"Unighaz"**

**Подробная инструкция:** см. [TELEGRAM_WORKFLOWS_MOVE_TO_UNIGHAZ.md](./TELEGRAM_WORKFLOWS_MOVE_TO_UNIGHAZ.md)

**Workflows для перемещения:**
- `Telegram Creative Ingestion` (ID: `O8SPLlixny3MHvxO`)
- `Telegram Hypothesis Delivery` (ID: `5q3mshC9HRPpL6C0`)

## 🚀 Быстрая настройка (5 минут)

### Шаг 1: Создайте Telegram бота (если ещё не создан)

1. Откройте Telegram → найдите **@BotFather**
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. **Сохраните Bot Token**

### Шаг 2: Получите Chat ID

1. Напишите боту любое сообщение
2. Откройте: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Найдите `chat.id` в ответе

### Шаг 3: Создайте Telegram Credential в n8n

1. n8n Dashboard → **Credentials** → **Add Credential**
2. Найдите **Telegram**
3. **Access Token:** вставьте ваш Bot Token
4. **Name:** `GenomAI Telegram Bot`
5. **Save**

### Шаг 4: Настройте Workflow 1 (Telegram Creative Ingestion)

1. Откройте workflow `Telegram Creative Ingestion` (ID: `wweHxi45m4U1vzJI`)
2. В node **"Telegram Trigger"**:
   - Выберите credential "GenomAI Telegram Bot"
3. В node **"Send Success Response"**:
   - Выберите credential "GenomAI Telegram Bot"
4. В node **"Send Error Response"**:
   - Выберите credential "GenomAI Telegram Bot"
5. В node **"Call Ingestion Webhook"**:
   - Укажите URL: `http://your-n8n-instance/webhook/ingest/creative`
   - Или используйте: `{{ $env.N8N_WEBHOOK_URL }}`
6. **Активируйте workflow** (Enable)

### Шаг 5: Настройте Workflow 2 (Telegram Hypothesis Delivery)

1. Откройте workflow `Telegram Hypothesis Delivery` (ID: `kNOQ2dBE0B6OihS5`)
2. В node **"Send Telegram Message"**:
   - Выберите credential "GenomAI Telegram Bot"
   - Chat ID: `{{ $env.TELEGRAM_CHAT_ID }}` (или вставьте напрямую)
3. В node **"Load Hypotheses"**:
   - Выберите Supabase credential "GenomAI Supabase API"
4. В node **"Persist Delivery"**:
   - Выберите Supabase credential "GenomAI Supabase API"
5. В node **"Emit HypothesisDelivered"**:
   - Выберите Supabase credential "GenomAI Supabase API"

### Шаг 6: Настройте Environment Variables (опционально)

В n8n добавьте переменные окружения:

```bash
TELEGRAM_CHAT_ID=your-chat-id-here
N8N_WEBHOOK_URL=http://your-n8n-instance/webhook/ingest/creative
```

## 🧪 Тестирование

### Тест Workflow 1 (Ingestion)

1. Активируйте workflow "Telegram Creative Ingestion"
2. Отправьте боту сообщение:
   ```
   video_url: https://example.com/video/12345 tracker_id: KT-123456
   ```
3. Проверьте:
   - ✅ Workflow выполнился
   - ✅ Ответ пришёл в Telegram
   - ✅ Creative создан в БД (если webhook настроен)

### Тест Workflow 2 (Output)

1. Убедитесь, что в `genomai.hypotheses` есть данные
2. Запустите workflow "Telegram Hypothesis Delivery" вручную
3. Проверьте:
   - ✅ Сообщение пришло в Telegram
   - ✅ Delivery сохранён в `genomai.deliveries`
   - ✅ Событие записано в `genomai.event_log`

## 📝 Что осталось сделать вручную

- ✅ Workflows созданы
- ✅ Структура настроена
- ⚠️ **Вставить Bot Token** в Telegram credential
- ⚠️ **Указать Chat ID** (через env или напрямую)
- ⚠️ **Настроить Supabase credentials** (если ещё не настроены)
- ⚠️ **Указать URL webhook** для ingestion (если используется внешний)

## 🔗 Связанные документы

- [TELEGRAM_BOT_SETUP.md](./TELEGRAM_BOT_SETUP.md) — Полная инструкция по настройке
- [N8N_CREDENTIALS_TEMPLATE.md](./N8N_CREDENTIALS_TEMPLATE.md) — Шаблоны credentials

## ⚠️ Важно

- Bot Token должен храниться в secrets, не в коде
- Chat ID можно получить динамически из сообщения (для Workflow 1)
- Для production используйте отдельного бота
- Тестируйте на отдельном тестовом боте

