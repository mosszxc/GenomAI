#!/bin/bash

# Тестовый запрос для webhook telegram_hypothesis_delivery
# Использование: ./test_telegram_delivery_webhook.sh

# Тестовый webhook URL (требует активации через UI n8n)
TEST_WEBHOOK_URL="https://kazamaqwe.app.n8n.cloud/webhook-test/telegram-hypothesis-delivery-trigger"

# Production webhook URL (после активации workflow)
PROD_WEBHOOK_URL="https://kazamaqwe.app.n8n.cloud/webhook/telegram-hypothesis-delivery-trigger"

# Реальные данные из БД (обновлено 2025-12-22)
IDEA_ID="c0c2d259-9f91-49b6-ba1e-0ecb3040d65e"
DECISION_ID="cfb0db86-06d7-4ba9-b71d-443416d9b188"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")
UNIX_TIMESTAMP=$(date +%s)

# Формат Database Trigger (как будет приходить от Supabase)
PAYLOAD=$(cat <<EOF
{
  "type": "INSERT",
  "table": "event_log",
  "record": {
    "id": "test-hypothesis-generated-${UNIX_TIMESTAMP}",
    "event_type": "HypothesisGenerated",
    "entity_type": "idea",
    "entity_id": "${IDEA_ID}",
    "payload": "{\"idea_id\":\"${IDEA_ID}\",\"decision_id\":\"${DECISION_ID}\",\"count\":1}",
    "occurred_at": "${TIMESTAMP}",
    "idempotency_key": "test_hypothesis_generated:${UNIX_TIMESTAMP}"
  }
}
EOF
)

echo "Тестовый запрос для Telegram Hypothesis Delivery webhook"
echo "=================================================="
echo ""
echo "Webhook URL (test): ${TEST_WEBHOOK_URL}"
echo "Webhook URL (prod): ${PROD_WEBHOOK_URL}"
echo ""
echo "Payload:"
echo "$PAYLOAD" | jq .
echo ""
echo "Отправка запроса..."

# Отправка запроса
RESPONSE=$(curl -s -X POST "${TEST_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo ""
echo "Ответ:"
echo "$RESPONSE" | jq .

# Если используется production URL
if [ "$1" == "prod" ]; then
  echo ""
  echo "Используется production URL..."
  RESPONSE=$(curl -s -X POST "${PROD_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
  echo "$RESPONSE" | jq .
fi



