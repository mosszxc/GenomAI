# GenomAI — Telegram Bot Setup Guide

**Версия:** v1.0  
**Статус:** ACTIVE  
**Назначение:** Пошаговая инструкция по настройке Telegram бота для GenomAI

## 📋 Обзор

Telegram бот используется в GenomAI для:
- **Входные данные (STEP 01):** Приём `video_url` + `tracker_id` от пользователя
- **Выходные данные (STEP 06):** Доставка гипотез пользователю

**Важно:** Telegram — транспортный канал, а не логический компонент системы.

## 🎯 Два направления использования

### 1. Telegram → n8n (Ingestion)

**Назначение:** Пользователь отправляет данные в Telegram, бот передаёт их в n8n webhook.

**Workflow:** `Creative Ingestion Webhook` (STEP 01)

**Требуется:**
- Telegram Bot Token
- n8n Telegram Trigger node
- Webhook endpoint в n8n

### 2. n8n → Telegram (Output)

**Назначение:** Система отправляет гипотезы пользователю через Telegram.

**Workflow:** `telegram_hypothesis_delivery` (STEP 06)

**Требуется:**
- Telegram Bot Token
- Telegram Chat ID (получателя)
- n8n Telegram Send Message node

## 🔧 Шаг 1: Создание Telegram бота

### 1.1 Создание бота через @BotFather

1. Откройте Telegram и найдите **@BotFather**
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: `GenomAI Bot`)
   - Введите username бота (должен заканчиваться на `bot`, например: `genomai_bot`)
4. **Сохраните Bot Token** — он понадобится для настройки

**Пример ответа:**
```
Done! Congratulations on your new bot. You will find it at t.me/genomai_bot. Use this token to access the HTTP API:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 1.2 Настройка бота (опционально)

Можно настроить описание и команды:

```
/setdescription - установить описание бота
/setcommands - установить команды бота
```

**Рекомендуемые команды:**
```
start - Начать работу с GenomAI
help - Помощь
```

## 🔧 Шаг 2: Получение Chat ID

### 2.1 Для личного чата

1. Напишите боту любое сообщение
2. Откройте в браузере:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. Найдите `chat.id` в ответе:
   ```json
   {
     "ok": true,
     "result": [{
       "message": {
         "chat": {
           "id": 123456789
         }
       }
     }]
   }
   ```

### 2.2 Для группы/канала

1. Добавьте бота в группу/канал
2. Сделайте бота администратором (для каналов)
3. Используйте тот же метод `getUpdates` для получения `chat.id`

**Примечание:** Для каналов `chat.id` будет отрицательным числом.

## 🔧 Шаг 3: Настройка Telegram в n8n

### 3.1 Создание Telegram Credential

1. Откройте n8n Dashboard
2. Перейдите в **Credentials** → **Add Credential**
3. Найдите **Telegram** в списке
4. Заполните:
   - **Access Token:** Ваш Bot Token из @BotFather
5. Нажмите **Save**

**Название credential:** `GenomAI Telegram Bot`

### 3.2 Настройка готовых workflow

✅ **Workflow уже созданы!** Осталось только вставить credentials.

#### Workflow 1: "Telegram Creative Ingestion" (ID: `wweHxi45m4U1vzJI`)

**Назначение:** Приём сообщений от пользователя и передача в ingestion webhook

**Что нужно сделать:**
1. Откройте workflow "Telegram Creative Ingestion" в n8n
2. В node **"Telegram Trigger"**:
   - Выберите credential "GenomAI Telegram Bot" (или создайте новый)
3. В node **"Send Success Response"**:
   - Выберите credential "GenomAI Telegram Bot"
4. В node **"Send Error Response"**:
   - Выберите credential "GenomAI Telegram Bot"
5. В node **"Call Ingestion Webhook"**:
   - Укажите URL вашего n8n webhook: `http://your-n8n-instance/webhook/ingest/creative`
   - Или используйте переменную окружения: `{{ $env.N8N_WEBHOOK_URL }}`

**Готово!** Workflow готов к использованию.

#### Workflow 2: "Telegram Hypothesis Delivery" (ID: `kNOQ2dBE0B6OihS5`)

**Назначение:** Отправка гипотез пользователю (STEP 06)

**Что нужно сделать:**
1. Откройте workflow "Telegram Hypothesis Delivery" в n8n
2. В node **"Send Telegram Message"**:
   - Выберите credential "GenomAI Telegram Bot"
   - Укажите Chat ID: `{{ $env.TELEGRAM_CHAT_ID }}` (или вставьте напрямую)
3. В node **"Load Hypotheses"**:
   - Выберите Supabase credential "GenomAI Supabase API"
   - Настройте фильтры для загрузки гипотез (по умолчанию загружает последние 10)
4. В node **"Persist Delivery"**:
   - Выберите Supabase credential "GenomAI Supabase API"
5. В node **"Emit HypothesisDelivered"**:
   - Выберите Supabase credential "GenomAI Supabase API"

**Примечание:** Этот workflow использует Manual Trigger для тестирования.  
Для production можно заменить на Cron Trigger для polling event_log на предмет новых `HypothesisGenerated` событий.

### 3.3 Проверка подключения

1. Откройте workflow "Telegram Creative Ingestion"
2. Активируйте workflow (Enable)
3. Отправьте тестовое сообщение боту в Telegram:
   ```
   video_url: https://example.com/video/12345 tracker_id: KT-123456
   ```
4. Проверьте, что workflow выполнился и ответ пришёл в Telegram

## 🔧 Шаг 4: Настройка Telegram Trigger (Ingestion)

### 4.1 Workflow уже создан!

✅ **Workflow "Telegram Creative Ingestion" создан** (ID: `wweHxi45m4U1vzJI`)

**Структура workflow:**
1. ✅ **Telegram Trigger** — приём сообщений от пользователя
2. ✅ **Parse Message** — парсинг `video_url` и `tracker_id` из сообщения
3. ✅ **Validate Payload** — проверка наличия обязательных полей
4. ✅ **Call Ingestion Webhook** — вызов webhook `/ingest/creative`
5. ✅ **Send Success Response** — отправка успешного ответа в Telegram
6. ✅ **Send Error Response** — отправка ошибки в Telegram

**Что осталось сделать:**
- Вставить Telegram Bot Token в credential
- Указать URL webhook ingestion (или использовать переменную окружения)

### 4.2 Формат сообщения от пользователя

**Рекомендуемый формат:**
```
video_url: https://example.com/video/12345 tracker_id: KT-123456
```

Или в одну строку:
```
https://example.com/video/12345 KT-123456
```

**Workflow автоматически распарсит оба формата.**

## 🔧 Шаг 5: Настройка Telegram Output (STEP 06)

### 5.1 Workflow уже создан!

✅ **Workflow "Telegram Hypothesis Delivery" создан** (ID: `kNOQ2dBE0B6OihS5`)

**Структура workflow:**
1. ✅ **Manual Trigger** — для тестирования (можно заменить на Cron для polling)
2. ✅ **Load Hypotheses** — загрузка гипотез из `genomai.hypotheses`
3. ✅ **Format Message** — форматирование гипотез в текст для Telegram
4. ✅ **Send Telegram Message** — отправка сообщения в Telegram
5. ✅ **Persist Delivery** — сохранение delivery в `genomai.deliveries`
6. ✅ **Emit HypothesisDelivered** — запись события в `genomai.event_log`

**Что осталось сделать:**
- Вставить Telegram Bot Token в credential
- Указать Chat ID (через переменную окружения `TELEGRAM_CHAT_ID` или напрямую)
- Настроить Supabase credentials для всех Supabase nodes

**Примечание:** Для production рекомендуется заменить Manual Trigger на:
- **Cron Trigger** для периодического polling `event_log` на предмет новых `HypothesisGenerated` событий
- Или использовать **Supabase Realtime** для подписки на события (если поддерживается)

## 📝 Шаг 6: Environment Variables

Добавьте в n8n environment variables (если поддерживается):

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

Или используйте в workflow через `{{ $env.TELEGRAM_BOT_TOKEN }}` и `{{ $env.TELEGRAM_CHAT_ID }}`.

## ✅ Чеклист готовности

### Для Ingestion (STEP 01):
- [x] Telegram бот создан через @BotFather (требует ручного действия)
- [x] Bot Token получен и сохранён (требует ручного действия)
- [ ] Telegram credential создан в n8n (вставить Bot Token)
- [x] Telegram Trigger workflow создан ✅ (ID: `wweHxi45m4U1vzJI`)
- [ ] Webhook endpoint `/ingest/creative` настроен (указать URL)
- [ ] Тестовое сообщение успешно обработано

### Для Output (STEP 06):
- [x] Chat ID получен и сохранён (требует ручного действия)
- [x] Telegram Send Message node настроен ✅ (в workflow)
- [x] Workflow `Telegram Hypothesis Delivery` создан ✅ (ID: `kNOQ2dBE0B6OihS5`)
- [ ] Telegram credential настроен (вставить Bot Token)
- [ ] Chat ID указан (через `TELEGRAM_CHAT_ID` или напрямую)
- [ ] Тестовое сообщение успешно отправлено

## 🐛 Troubleshooting

### Бот не отвечает

**Причины:**
1. Workflow не активирован
2. Неверный Bot Token
3. Бот не запущен

**Решение:**
- Проверьте, что workflow enabled в n8n
- Проверьте правильность Bot Token
- Убедитесь, что Telegram Trigger node правильно настроен

### Ошибка "Chat not found"

**Причины:**
1. Неверный Chat ID
2. Бот не добавлен в чат/группу
3. Бот не является администратором (для каналов)

**Решение:**
- Проверьте Chat ID через `getUpdates`
- Убедитесь, что бот добавлен в чат
- Для каналов: сделайте бота администратором

### Сообщения не приходят

**Причины:**
1. Webhook не настроен
2. Workflow не обрабатывает события
3. Ошибка в логике workflow

**Решение:**
- Проверьте логи n8n execution
- Убедитесь, что Telegram Trigger node правильно настроен
- Проверьте, что workflow активирован

## 📚 Связанные документы

- [TELEGRAM_INTERACTION_MODEL.md](../docs/layer-2-product/TELEGRAM_INTERACTION_MODEL.md) — Модель взаимодействия через Telegram
- [01_ingestion_playbook.md](../docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/01_ingestion_playbook.md) — Playbook для STEP 01
- [06_telegram_output_playbook.md](../docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/06_telegram_output_playbook.md) — Playbook для STEP 06
- [API_CONTRACTS.md](../docs/layer-4-implementation-planning/API_CONTRACTS.md) — Контракты API
- [N8N_CREDENTIALS_TEMPLATE.md](./N8N_CREDENTIALS_TEMPLATE.md) — Шаблоны credentials

## ⚠️ Важные правила

1. **Telegram — транспорт, а не мозг**
   - Бот не принимает решения
   - Бот не хранит состояние
   - Бот только передаёт данные

2. **Push-Only Model**
   - Пользователь отправляет факты
   - Система обрабатывает и отвечает
   - Запросно-ответная модель запрещена

3. **Stateless Messaging**
   - Каждое сообщение изолировано
   - Нет контекста диалога
   - Состояние только в системе

## 🎯 Следующие шаги

После настройки Telegram бота:

1. **Для STEP 01:** Начните работу с workflow `Creative Ingestion Webhook`
2. **Для STEP 06:** Настройте workflow `telegram_hypothesis_delivery` (после реализации STEP 05)

## 📝 Примечания

- Bot Token должен храниться в secrets, не в коде
- Chat ID можно получить динамически из сообщения
- Для production используйте отдельного бота
- Тестируйте на отдельном тестовом боте

