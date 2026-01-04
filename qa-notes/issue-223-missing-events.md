# Issue #223: Отсутствуют ключевые события в event_log

## Диагностика

### Статус событий за последние 7 дней

| Event Type | В issue указано | Реально в БД | Статус |
|------------|-----------------|--------------|--------|
| `CreativeRegistered` | Нет | `SpyCreativeRegistered` (7), `CreativeDecomposed` (4) | ✅ OK — другое имя |
| `TranscriptCreated` | Нет | Есть (3), last: 2025-12-30 | ✅ OK — нет новых видео |
| `HypothesisDelivered` | Нет | `HypothesisDeliveryFailed` (3) | ❌ BUG |

### Root Cause: HypothesisDeliveryFailed

Все 3 failed гипотезы имеют причину `"No buyer_id assigned"`:

| hypothesis_id | buyer_id в БД | creative_buyer_id | Причина failed |
|---------------|---------------|-------------------|----------------|
| `4d813753...` | d75efea6... ✅ | d75efea6... | Workflow не читает buyer_id |
| `1556b288...` | d75efea6... ✅ | d75efea6... | Workflow не читает buyer_id |
| `ef95307d...` | NULL | NULL | Spy creative без buyer |

**Вывод:** 2 из 3 гипотез имеют buyer_id, но workflow всё равно failed.

## Найденные проблемы

### 1. Workflow `Telegram Hypothesis Delivery` неактивен
- Webhook URL: `https://kazamaqwe.app.n8n.cloud/webhook/hypothesis-delivery-trigger`
- Статус: **404 Not Found**
- Решение: Активировать workflow в n8n UI

### 2. Workflow проверяет buyer_id неправильно
- Вероятно ищет `idea.buyer_id` вместо `hypotheses.buyer_id`
- Таблица `ideas` не имеет колонки `buyer_id`
- Решение: Исправить lookup в workflow на `hypotheses.buyer_id`

### 3. Hypothesis Factory не всегда устанавливает buyer_id
- 1 из 3 гипотез (`ef95307d`) не имеет buyer_id
- Причина: spy creative без buyer_id в source
- Связанный issue: #226

## Действия для исправления

### Шаг 1: Активировать workflow
```
n8n UI → Workflows → "Telegram Hypothesis Delivery" → Activate
```

### Шаг 2: Исправить buyer_id lookup
В workflow изменить node "Check Buyer":
```javascript
// Было (вероятно):
$json.idea.buyer_id

// Должно быть:
$json.hypothesis.buyer_id
```

### Шаг 3: Retry failed hypotheses
После активации workflow:
```sql
-- Сбросить статус для retry
UPDATE genomai.hypotheses
SET status = 'pending_delivery'
WHERE id IN (
  '4d813753-61cd-44e2-af5a-98b086739a61',
  '1556b288-5b50-4a07-818b-9f57ba5f6441'
) AND buyer_id IS NOT NULL;
```

Затем вызвать webhook для каждой:
```bash
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/hypothesis-delivery-trigger" \
  -H "Content-Type: application/json" \
  -d '{"hypothesis_id": "4d813753-61cd-44e2-af5a-98b086739a61"}'
```

## Ограничения

**n8n API недоступен** — переменные `N8N_API_URL` и `N8N_API_KEY` не настроены.
Поэтому исправления workflow нужно делать вручную в n8n UI.

## Детальные инструкции для fix в n8n UI

### 1. Активировать workflow

```
n8n UI → Workflows → Search "Telegram Hypothesis Delivery" (ID: 5q3mshC9HRPpL6C0)
→ Click workflow → Toggle "Active" = ON → Save
```

### 2. Исправить buyer_id lookup

В workflow найти node который проверяет buyer_id (вероятно "Check Buyer" или IF node).

**Проблема:** Workflow ищет `idea.buyer_id`, но таблица `ideas` не имеет этой колонки.

**Решение:** Изменить expression на чтение из `hypotheses.buyer_id`:

```javascript
// В Supabase node "Load Hypothesis":
// Убедиться что select включает buyer_id
SELECT id, idea_id, content, buyer_id, status FROM genomai.hypotheses WHERE id = :hypothesis_id

// В Check Buyer IF node:
// Изменить condition с:
{{ $json.idea.buyer_id }}
// На:
{{ $json.buyer_id }}
```

### 3. Retry failed hypotheses

После активации workflow выполнить SQL для сброса статуса:

```sql
-- Сбросить статус для retry (только те, у которых есть buyer_id)
UPDATE genomai.hypotheses
SET status = 'pending_delivery'
WHERE id IN (
  '4d813753-61cd-44e2-af5a-98b086739a61',
  '1556b288-5b50-4a07-818b-9f57ba5f6441'
) AND buyer_id IS NOT NULL;
```

Затем вызвать webhook:
```bash
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/hypothesis-delivery-trigger" \
  -H "Content-Type: application/json" \
  -d '{"hypothesis_id": "4d813753-61cd-44e2-af5a-98b086739a61"}'

curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/hypothesis-delivery-trigger" \
  -H "Content-Type: application/json" \
  -d '{"hypothesis_id": "1556b288-5b50-4a07-818b-9f57ba5f6441"}'
```

### 4. Верификация

После retry проверить:
```sql
-- Должны появиться HypothesisDelivered события
SELECT event_type, entity_id, occurred_at
FROM genomai.event_log
WHERE event_type = 'HypothesisDelivered'
ORDER BY occurred_at DESC
LIMIT 5;

-- Статус hypotheses должен измениться
SELECT id, status, delivered_at
FROM genomai.hypotheses
WHERE id IN (
  '4d813753-61cd-44e2-af5a-98b086739a61',
  '1556b288-5b50-4a07-818b-9f57ba5f6441'
);
```

## Связанные issues
- #222 — застрявшая hypothesis (та же проблема)
- #226 — fix buyer_id propagation в Hypothesis Factory

## Выводы

Issue #223 частично некорректен:
- `CreativeRegistered` → используется `SpyCreativeRegistered` (expected)
- `TranscriptCreated` → есть, просто нет новых видео
- `HypothesisDelivered` → **реальная проблема**, workflow неактивен + баг с buyer_id lookup
