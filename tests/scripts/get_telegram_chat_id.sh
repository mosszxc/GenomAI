#!/bin/bash

# Скрипт для получения Telegram Chat ID
# Использование: ./get_telegram_chat_id.sh <BOT_TOKEN>

if [ -z "$1" ]; then
  echo "Использование: $0 <BOT_TOKEN>"
  echo ""
  echo "Пример:"
  echo "  $0 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  echo ""
  echo "Как получить Bot Token:"
  echo "  1. Откройте Telegram и найдите @BotFather"
  echo "  2. Отправьте команду /newbot"
  echo "  3. Следуйте инструкциям"
  echo "  4. Сохраните Bot Token"
  exit 1
fi

BOT_TOKEN="$1"
API_URL="https://api.telegram.org/bot${BOT_TOKEN}/getUpdates"

echo "Получение Chat ID через Telegram Bot API..."
echo "=========================================="
echo ""
echo "Убедитесь, что вы уже отправили боту сообщение!"
echo "Нажмите Enter, чтобы продолжить..."
read

echo ""
echo "Запрос к API: ${API_URL}"
echo ""

RESPONSE=$(curl -s "${API_URL}")

# Проверка ответа
if echo "$RESPONSE" | jq -e '.ok == true' > /dev/null 2>&1; then
  echo "✅ Успешный ответ от API:"
  echo ""
  echo "$RESPONSE" | jq .
  echo ""
  
  # Извлечение Chat ID
  CHAT_ID=$(echo "$RESPONSE" | jq -r '.result[0].message.chat.id // empty')
  
  if [ -n "$CHAT_ID" ] && [ "$CHAT_ID" != "null" ]; then
    echo "=========================================="
    echo "✅ Chat ID найден:"
    echo ""
    echo "   CHAT_ID=${CHAT_ID}"
    echo ""
    echo "Используйте этот Chat ID в n8n workflow:"
    echo "   - В node 'Send Telegram Message'"
    echo "   - Или в переменной окружения: TELEGRAM_CHAT_ID=${CHAT_ID}"
    echo ""
  else
    echo "⚠️  Chat ID не найден в ответе."
    echo ""
    echo "Возможные причины:"
    echo "  1. Вы еще не отправили боту сообщение"
    echo "  2. Бот не получил сообщение"
    echo ""
    echo "Решение:"
    echo "  1. Откройте Telegram"
    echo "  2. Найдите вашего бота"
    echo "  3. Отправьте ему любое сообщение (например, 'Привет')"
    echo "  4. Запустите этот скрипт снова"
    echo ""
  fi
else
  echo "❌ Ошибка при запросе к API:"
  echo ""
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
  echo ""
  echo "Возможные причины:"
  echo "  1. Неверный Bot Token"
  echo "  2. Проблемы с сетью"
  echo ""
fi


