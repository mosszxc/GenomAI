# Issue #223: Отсутствуют ключевые события в event_log

## Статус: ✅ RESOLVED (2026-01-04)

## Диагностика

### Статус событий за последние 7 дней

| Event Type | В issue указано | Реально в БД | Статус |
|------------|-----------------|--------------|--------|
| `CreativeRegistered` | Нет | `SpyCreativeRegistered` (7), `CreativeDecomposed` (4) | ✅ OK — другое имя |
| `TranscriptCreated` | Нет | Есть (3), last: 2025-12-30 | ✅ OK — нет новых видео |
| `HypothesisDelivered` | Нет | `HypothesisDeliveryFailed` (3) → **FIXED** | ✅ RESOLVED |

### Root Cause: HypothesisDeliveryFailed

Все 3 failed гипотезы имели причину `"No buyer_id assigned"`:

| hypothesis_id | buyer_id в БД | Статус после fix |
|---------------|---------------|------------------|
| `4d813753...` | d75efea6... ✅ | ✅ HypothesisDelivered (2026-01-04 20:43:49) |
| `1556b288...` | d75efea6... ✅ | ✅ HypothesisDelivered (2026-01-04 20:45:03) |
| `ef95307d...` | NULL | ⏭️ Skipped (spy creative без buyer) |

**Причина проблемы:** Hypothesis имели `status=failed`, но workflow искал `status=ready_for_launch`.

## Найденные проблемы и решения

### 1. Workflow `Telegram Hypothesis Delivery` — РАБОТАЕТ ✅
- Workflow ID: `5q3mshC9HRPpL6C0`
- Webhook URL: `https://kazamaqwe.app.n8n.cloud/webhook/telegram-hypothesis-delivery-trigger`
- Статус: **active: true**
- Логика buyer_id проверки корректна (`$json.buyer_id` из Format Message)

### 2. Первоначальная причина failed — status mismatch
- Workflow фильтрует по `status=ready_for_launch`
- После первого failed статус менялся на `failed`
- При retry статус не сбрасывался → workflow не находил hypotheses

### 3. Hypothesis Factory не всегда устанавливает buyer_id
- 1 из 3 гипотез (`ef95307d`) не имеет buyer_id
- Причина: spy creative без buyer_id в source
- Связанный issue: #226

## Выполненный fix

```sql
-- 1. Сброс статуса для retry
UPDATE genomai.hypotheses SET status = 'ready_for_launch'
WHERE id IN ('4d813753-61cd-44e2-af5a-98b086739a61', '1556b288-5b50-4a07-818b-9f57ba5f6441')
AND buyer_id IS NOT NULL;

-- 2. Вызов webhook
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/telegram-hypothesis-delivery-trigger" \
  -H "Content-Type: application/json" -d '{"idea_id": "<idea_id>"}'
```

**Результат:** 2 HypothesisDelivered события созданы в event_log.

## Связанные issues
- #222 — застрявшая hypothesis (та же проблема)
- #226 — fix buyer_id propagation в Hypothesis Factory

## Верификация

```sql
-- HypothesisDelivered события появились
SELECT event_type, entity_id, occurred_at FROM genomai.event_log
WHERE event_type = 'HypothesisDelivered' ORDER BY occurred_at DESC LIMIT 5;

-- Результат:
-- HypothesisDelivered | 80aeb676-ed02-4d4a-a1f6-3970b1d9472a | 2026-01-04 20:45:03
-- HypothesisDelivered | 86ce27f1-8f81-4e2c-95fd-916cae445928 | 2026-01-04 20:43:49
```

## Выводы

Issue #223 изначально некорректен, но привёл к полезной диагностике:

| Событие | Статус | Причина |
|---------|--------|---------|
| `CreativeRegistered` | ✅ OK | Используется `SpyCreativeRegistered` |
| `TranscriptCreated` | ✅ OK | Есть, просто нет новых видео |
| `HypothesisDelivered` | ✅ FIXED | Retry 2 из 3 гипотез успешен |

**Lesson learned:** При HypothesisDeliveryFailed нужно:
1. Проверить hypothesis.buyer_id (не idea.buyer_id)
2. Сбросить status на `ready_for_launch`
3. Вызвать webhook с `idea_id` (не hypothesis_id)
