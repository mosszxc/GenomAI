# n8n Credentials Template

**Версия:** v1.0  
**Статус:** REFERENCE  
**⚠️ НЕ КОММИТИТЬ В РЕПОЗИТОРИЙ!**

Этот файл содержит шаблоны для настройки credentials в n8n.

## 🔑 Supabase Credential (рекомендуется)

**Type:** Supabase

**Name:** `GenomAI Supabase API`

**Configuration:**
```
Host: https://ftrerelppsnbdcmtcwya.supabase.co
Service Role Secret: [SERVICE_ROLE_KEY]
```

**Важно:**
- Используйте `service_role` key для полного доступа (чтение и запись)
- Этот key имеет полные права доступа к базе данных
- Храните его в безопасности, не коммитьте в репозиторий

## 📋 Примеры использования в n8n

### Supabase Node Examples:

**Чтение данных (Get Many):**
- Operation: Get Many
- Use Custom Schema: ✅ enabled
- Schema: `genomai`
- Table: `event_log`
- Return All: true (или указать Limit)

**Создание записи (Create):**
- Operation: Create
- Use Custom Schema: ✅ enabled
- Schema: `genomai`
- Table: `event_log`
- Data:
```json
{
  "event_type": "TestEvent",
  "entity_type": "test",
  "payload": {"test": true},
  "idempotency_key": "test-key-123"
}
```

**Обновление записи (Update):**
- Operation: Update
- Use Custom Schema: ✅ enabled
- Schema: `genomai`
- Table: `event_log`
- Row ID: [uuid записи]
- Data: {обновляемые поля}

## 📱 Telegram Bot Credential

**Type:** Telegram

**Name:** `GenomAI Telegram Bot`

**Configuration:**
```
Access Token: [BOT_TOKEN from @BotFather]
```

**Как получить Bot Token:**
1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный Bot Token

**Важно:**
- Bot Token должен храниться в secrets, не в коде
- Не коммитьте Bot Token в репозиторий
- Для production используйте отдельного бота

**Использование:**
- **Telegram Trigger:** для приёма сообщений от пользователей (STEP 01)
- **Telegram Send Message:** для отправки гипотез пользователям (STEP 06)

**Подробнее:** см. [TELEGRAM_BOT_SETUP.md](./TELEGRAM_BOT_SETUP.md)

## 🔒 Безопасность

- ⚠️ Никогда не коммитьте реальные credentials
- ⚠️ Используйте `service_role` key только в n8n credentials (не в коде)
- ⚠️ Регулярно ротируйте keys в Supabase Dashboard
- ⚠️ Для production рекомендуется использовать отдельные credentials с ограниченными правами
- ⚠️ Храните Bot Token в secrets, не в коде

## 🤖 OpenAI Credential (для STEP 02 - Decomposition)

**Type:** OpenAI

**Name:** `GenomAI OpenAI API`

**Configuration:**
```
API Key: [OPENAI_API_KEY]
```

**Как получить API Key:**
1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Перейдите в раздел API Keys
3. Создайте новый API Key
4. Сохраните ключ в безопасном месте

**Важно:**
- API Key должен храниться в secrets, не в коде
- Не коммитьте API Key в репозиторий
- Для production рекомендуется использовать отдельный API Key с ограниченными правами
- Следите за лимитами использования API

**Использование в workflow `creative_decomposition_llm`:**
- **Node:** LLM Call (Classification)
- **Resource:** Chat
- **Operation:** Complete
- **Model:** gpt-4o-mini (рекомендуется для классификации) или gpt-4o
- **Temperature:** 0.1 (низкая для детерминированности)
- **Max Tokens:** 2000
- **Prompt:** Уже настроен в workflow согласно Canonical Schema

**Рекомендуемые модели:**
- `gpt-4o-mini` - оптимальный баланс цена/качество для классификации
- `gpt-4o` - более точная классификация, но дороже
- `gpt-3.5-turbo` - дешевле, но менее точная

## 📝 Заметки

- Все таблицы находятся в схеме `genomai`
- Обязательно включайте опцию "Use Custom Schema" в Supabase node
- Указывайте схему: `genomai`
- Supabase node автоматически работает с указанной схемой через Supabase API
- Telegram бот используется как транспортный канал, не как логический компонент
- LLM используется только для классификации, не для оценки или принятия решений

