# GenomAI — Telegram Bot Setup Guide

**Версия:** v2.0
**Статус:** ACTIVE
**Назначение:** Пошаговая инструкция по настройке Telegram бота для GenomAI

## Обзор

Telegram бот используется в GenomAI для:
- **Buyer Onboarding:** Регистрация новых медиабайеров (`/start`)
- **Video Registration:** Приём video_url от пользователя
- **Hypothesis Delivery:** Доставка гипотез пользователю
- **Daily Recommendations:** Ежедневные рекомендации (09:00 UTC)

**Архитектура:** FastAPI webhook + Temporal workflows (n8n не используется)

## Архитектура

```
Telegram Bot API
      ↓
FastAPI Webhook (/webhook/telegram)
      ↓
Temporal Workflows:
  - BuyerOnboardingWorkflow
  - CreativeRegistrationWorkflow
  - CreativePipelineWorkflow (включает Hypothesis Delivery)
  - DailyRecommendationWorkflow
```

## Шаг 1: Создание Telegram бота

### 1.1 Создание бота через @BotFather

1. Откройте Telegram и найдите **@BotFather**
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: `GenomAI Bot`)
   - Введите username бота (должен заканчиваться на `bot`, например: `genomai_bot`)
4. **Сохраните Bot Token** — он понадобится для настройки

### 1.2 Настройка команд бота

```
/setcommands
```

**Рекомендуемые команды:**
```
start - Начать работу с GenomAI
stats - Показать статистику
genome - Тепловая карта компонентов
knowledge - Просмотр knowledge extractions (admin)
help - Помощь
```

## Шаг 2: Получение Chat ID

### 2.1 Для личного чата

1. Напишите боту любое сообщение
2. Откройте в браузере:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. Найдите `chat.id` в ответе

### 2.2 Для группы/канала

1. Добавьте бота в группу/канал
2. Сделайте бота администратором (для каналов)
3. Используйте тот же метод `getUpdates`

## Шаг 3: Настройка Webhook

### 3.1 Environment Variables

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-default-chat-id  # опционально
```

### 3.2 Установка Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://genomai.onrender.com/webhook/telegram"}'
```

### 3.3 Проверка Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## Шаг 4: Проверка работы

### 4.1 Тест /start

1. Отправьте боту `/start`
2. Ожидаемый ответ: приветствие и запрос имени (на русском)
3. Workflow: `BuyerOnboardingWorkflow`

### 4.2 Тест Video URL

1. Отправьте боту ссылку на видео:
   ```
   https://www.youtube.com/watch?v=example
   ```
2. Ожидаемый ответ: подтверждение регистрации креатива
3. Workflow: `CreativeRegistrationWorkflow`

### 4.3 Тест /stats

1. Отправьте боту `/stats`
2. Ожидаемый ответ: статистика (ROI, wins/losses)

## Temporal Workflows

| Workflow | Task Queue | Триггер |
|----------|-----------|---------|
| BuyerOnboardingWorkflow | telegram | `/start` |
| CreativeRegistrationWorkflow | telegram | Video URL |
| CreativePipelineWorkflow | creative-pipeline | После регистрации |
| DailyRecommendationWorkflow | metrics | Schedule 09:00 UTC |

## Поддерживаемые команды

| Команда | Описание | Доступ | Статус |
|---------|----------|--------|--------|
| `/start` | Онбординг нового байера | Все | ✅ |
| `/stats` | Статистика пользователя | Все | ✅ |
| `/help` | Справка | Все | ✅ |
| `/genome` | Heatmap компонентов | Все | ✅ |
| `/trends` | Win rate trends (график) | Admin | ✅ |
| `/knowledge` | Pending knowledge extractions | Admin | ✅ |
| Video URL | Регистрация креатива | Все | ✅ |
| `.txt/.md` file | Knowledge extraction | Admin | ✅ |

## Troubleshooting

### Бот не отвечает

1. Проверьте webhook: `getWebhookInfo`
2. Проверьте логи FastAPI на Render
3. Проверьте статус Temporal workers

### Ошибка "Session timed out"

- Issue #280 исправлен
- Таймаут сессии: 60 минут

### Сообщения не приходят

1. Проверьте `TELEGRAM_BOT_TOKEN` в env
2. Проверьте что webhook установлен правильно
3. Проверьте Render logs

## Связанные документы

- [TELEGRAM_INTERACTION_MODEL.md](../docs/layer-2-product/TELEGRAM_INTERACTION_MODEL.md) — Модель взаимодействия
- [TEMPORAL_WORKFLOWS.md](../docs/TEMPORAL_WORKFLOWS.md) — Справочник workflows
- [API_REFERENCE.md](../docs/API_REFERENCE.md) — API документация

## Важные правила

1. **Telegram — транспорт, а не мозг**
   - Бот не принимает решения
   - Бот не хранит состояние
   - Бот только передаёт данные

2. **Push-Only Model**
   - Пользователь отправляет факты
   - Система обрабатывает и отвечает
   - Интерактивные диалоги запрещены

3. **Stateless Messaging**
   - Состояние хранится в Temporal workflow
   - Каждое сообщение обрабатывается независимо
