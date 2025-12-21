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

## 🔒 Безопасность

- ⚠️ Никогда не коммитьте реальные credentials
- ⚠️ Используйте `service_role` key только в n8n credentials (не в коде)
- ⚠️ Регулярно ротируйте keys в Supabase Dashboard
- ⚠️ Для production рекомендуется использовать отдельные credentials с ограниченными правами

## 📝 Заметки

- Все таблицы находятся в схеме `genomai`
- Обязательно включайте опцию "Use Custom Schema" в Supabase node
- Указывайте схему: `genomai`
- Supabase node автоматически работает с указанной схемой через Supabase API

