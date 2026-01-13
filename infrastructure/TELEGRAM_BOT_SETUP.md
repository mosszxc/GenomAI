# GenomAI — Telegram Bot Setup Guide

**Версия:** v3.0
**Статус:** ACTIVE
**Назначение:** Пошаговая инструкция по настройке Telegram бота для GenomAI

## Обзор

Telegram бот используется в GenomAI для:
- **Buyer Onboarding:** Регистрация новых медиабайеров (`/start`)
- **Video Registration:** Приём video_url от пользователя
- **Statistics:** Статистика и аналитика (`/stats`, `/genome`)
- **Admin Tools:** Мониторинг и управление системой

**Архитектура:** FastAPI webhook + Temporal workflows

## Архитектура

```
Telegram Bot API
      ↓
FastAPI Webhook (/webhook/telegram)
      ↓
Message Router (src/routes/telegram.py)
      ↓
├─ Commands → Direct Response or Temporal Workflow
├─ Video URL → CreativeRegistrationWorkflow
└─ Callbacks → Handle inline button actions
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

**Команды для байеров:**
```
start - Начать работу с GenomAI
stats - Показать статистику
genome - Матрица компонентов
help - Помощь
feedback - Оставить отзыв
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
TELEGRAM_WEBHOOK_SECRET=your-secret-token  # опционально, для безопасности
ADMIN_TELEGRAM_IDS=123456,789012  # ID администраторов
```

### 3.2 Установка Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://genomai.onrender.com/webhook/telegram",
    "secret_token": "<YOUR_SECRET>"
  }'
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
2. Ожидаемый ответ: статистика (wins/losses, ROI, рекомендации)

## Команды

### Для всех пользователей (Buyers)

| Команда | Описание |
|---------|----------|
| `/start` | Онбординг нового байера |
| `/stats` | Статистика: wins, losses, ROI |
| `/genome` | Матрица компонентов (heatmap) |
| `/help` | Справка по командам |
| `/feedback <текст>` | Оставить отзыв |
| Video URL | Регистрация креатива |

### Только для администраторов

| Команда | Описание |
|---------|----------|
| `/genome <type>` | Heatmap по конкретному типу компонента |
| `/genome <value> --by <geo\|avatar\|week>` | Сегментированный анализ |
| `/confidence` | Доверительные интервалы |
| `/correlations` | Синергии компонентов |
| `/trends` | Графики трендов win rate |
| `/drift` | Обнаружение дрифта |
| `/simulate X + Y + Z` | What-If симулятор |
| `/recommend` | Лучшая комбинация дня |
| `/knowledge` | Knowledge extractions на ревью |
| `/buyers` | Список всех баеров |
| `/activity` | Последние действия в системе |
| `/decisions` | Решения Decision Engine |
| `/creatives` | Все креативы |
| `/status` | Статус Temporal workflows |
| `/errors` | Последние ошибки |
| `/pending` | Гипотезы на модерацию |
| `/approve <id>` | Одобрить гипотезу |
| `/reject <id>` | Отклонить гипотезу |
| `.txt/.md file` | Knowledge extraction из документа |

## Temporal Workflows

| Workflow | Task Queue | Триггер |
|----------|-----------|---------|
| BuyerOnboardingWorkflow | telegram | `/start` |
| CreativeRegistrationWorkflow | telegram | Video URL |
| CreativePipelineWorkflow | creative-pipeline | После регистрации |
| DailyRecommendationWorkflow | metrics | Schedule 09:00 UTC |

## Troubleshooting

### Бот не отвечает

1. Проверьте webhook: `getWebhookInfo`
2. Проверьте логи FastAPI на Render
3. Проверьте статус Temporal workers: `/status` (admin)

### Ошибка авторизации

1. Проверьте `TELEGRAM_WEBHOOK_SECRET` совпадает с secret_token в setWebhook
2. Проверьте `TELEGRAM_BOT_TOKEN` в env

### Команда не работает

1. Проверьте права: команда может быть admin-only
2. Проверьте `ADMIN_TELEGRAM_IDS` в env

## Связанные документы

- [TELEGRAM_INTERACTION_MODEL.md](../docs/layer-2-product/TELEGRAM_INTERACTION_MODEL.md) — Модель взаимодействия
- [TEMPORAL_WORKFLOWS.md](../docs/TEMPORAL_WORKFLOWS.md) — Справочник workflows
- [API_REFERENCE.md](../docs/API_REFERENCE.md) — API документация

## Важные правила

1. **Telegram — транспорт, а не мозг**
   - Бот не принимает решения
   - Бот не хранит состояние (кроме Temporal workflow state)
   - Бот только передаёт данные

2. **Stateless Messaging**
   - Состояние хранится в Temporal workflow
   - Каждое сообщение обрабатывается независимо

3. **Безопасность**
   - Bot Token хранится в secrets
   - Webhook защищён secret_token
   - Admin команды доступны только по whitelist
