# Issue #222: 1 hypothesis застрял в delivery

## Проблема
Hypothesis `4d813753-61cd-44e2-af5a-98b086739a61` не доставлен, status = ready_for_launch.

## Диагностика
1. Event log показал: `HypothesisDeliveryFailed` с `reason: "No buyer_id assigned"`
2. Проверка hypothesis: `buyer_id = NULL`
3. Проверка creative chain: `buyer_id = d75efea6-597f-46a1-820c-e82ec5fe2449` (есть!)

## Root Cause
Workflow `hypothesis_factory_generate` не копирует buyer_id из creative → hypothesis.

## Решение для данного hypothesis
1. Обновлён buyer_id в hypothesis (для теста)
2. Webhook delivery не активен (404)
3. Статус обновлён на `failed`

## Системное решение
Создан Issue #226: добавить lookup buyer_id в Hypothesis Factory.

## Gotchas
- Telegram Hypothesis Delivery webhook требует активации в n8n UI
- buyer_id должен копироваться через цепочку: creative → decomposed_creative → idea → hypothesis
