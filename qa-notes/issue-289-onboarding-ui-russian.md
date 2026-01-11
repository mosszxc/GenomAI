# Issue #289: Улучшить UI сообщения онбоардинга + campaign-based video collection

## Изменения

### 1. Перевод сообщений на русский
Все сообщения BuyerOnboardingWorkflow переведены на русский язык с дружелюбным тоном (обращение на "ты").

### 2. Новое состояние AWAITING_VIDEOS
После загрузки истории из Keitaro — бот показывает каждую кампанию по очереди и запрашивает URL видео.

**Flow:**
```
LOADING_HISTORY:
  1. create_buyer()
  2. HistoricalImportWorkflow → campaigns saved to historical_import_queue (status=pending_video)
  3. get_pending_video_campaigns(buyer_id) → list of campaigns

AWAITING_VIDEOS:
  FOR EACH campaign:
    1. Show "📹 Кампания: {name}\n🆔 ID: {campaign_id}\n📊 Клики: X | Конверсии: Y"
    2. Wait for URL
    3. update_import_with_video(import_id, video_url)
    4. Start CreativeRegistrationWorkflow
  → COMPLETED
```

### 3. Обновлённые вертикали
```python
VALID_VERTICALS = [
    "потенция", "простатит", "цистит", "грибок",
    "давление", "диабет", "зрение", "суставы",
    "похудение", "варикоз", "паразиты", "слух",
]
```

### 4. Терминология
- `keitaro_source` → `sub10` в UI сообщениях

## Файлы

| Файл | Изменения |
|------|-----------|
| `temporal/models/buyer.py` | AWAITING_VIDEOS state, VALID_VERTICALS |
| `temporal/activities/buyer.py` | `get_pending_video_campaigns()` activity |
| `temporal/workflows/buyer_onboarding.py` | MESSAGES dict, campaign-loop logic |

## Пример UI

**После загрузки истории:**
```
📹 Загружено 3 кампаний без видео

Сейчас покажу каждую — скинь ссылку на креатив.
```

**Запрос видео:**
```
1️⃣ Кампания: Potency IT Male 35+
🆔 ID: 10136
📊 Клики: 1190 | Конверсии: 6

Скинь URL видео:
```

**Подтверждение:**
```
✅ Видео получено, запускаю анализ...
```

## Тестирование

- [x] Симуляция диалога (ручная проверка сообщений)
- [ ] E2E тест с реальным buyer (требуется deploy)

## Deploy

После merge в main — автоматический deploy на Render.
