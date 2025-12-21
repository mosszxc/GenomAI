# Экспонирование схемы genomai в Supabase API

**Версия:** v1.0  
**Статус:** ACTIVE  
**Проблема:** Схема `genomai` не доступна через Supabase API по умолчанию

## 🔍 Проблема

По умолчанию Supabase API экспонирует только схему `public`. Для доступа к кастомным схемам (например, `genomai`) нужно:

1. Выдать права доступа ролям (`anon`, `authenticated`, `service_role`)
2. Добавить схему в список "Exposed schemas" в настройках API

## ✅ Решение

### Шаг 1: Выдача прав доступа (выполнено через миграцию)

Миграция `expose_genomai_schema` уже применена и выдала все необходимые права.

### Шаг 2: Добавление схемы в Exposed Schemas

**⚠️ ВАЖНО:** Это нужно сделать вручную в Supabase Dashboard!

1. Перейдите в **Settings** → **API** в Supabase Dashboard
2. Найдите раздел **Data API Settings**
3. Найдите поле **Exposed schemas**
4. Добавьте `genomai` в список (через запятую, например: `public, genomai`)
5. Нажмите **Save**

**Текущее значение:** `public`  
**Нужно изменить на:** `public, genomai`

## 📋 Проверка

После настройки проверьте:

1. **Через Supabase node в n8n:**
   - Operation: Get Many
   - Use Custom Schema: ✅ enabled
   - Schema: `genomai`
   - Table: `event_log`
   - Должно вернуть данные без ошибок

2. **Через REST API (curl):**
```bash
curl 'https://ftrerelppsnbdcmtcwya.supabase.co/rest/v1/event_log?select=*&limit=1' \
  -H "apikey: [YOUR_ANON_KEY]" \
  -H "Authorization: Bearer [YOUR_ANON_KEY]" \
  -H "Accept-Profile: genomai"
```

## 🔒 Безопасность

После экспонирования схемы `genomai`:

- ✅ Все таблицы имеют RLS отключен (для внутреннего использования)
- ✅ Доступ только через `service_role` key (в n8n)
- ⚠️ Рекомендуется настроить RLS policies для production

## 📚 Ссылки

- [Supabase: Using Custom Schemas](https://supabase.com/docs/guides/api/using-custom-schemas)
- [Supabase: Hardening the Data API](https://supabase.com/docs/guides/database/hardening-data-api)

## ✅ Статус

- ✅ Права доступа выданы (миграция `expose_genomai_schema` применена)
- ✅ Схема `genomai` добавлена в "Exposed schemas" в Dashboard
- ✅ Схема `genomai` теперь доступна через Supabase API

## ⚠️ Важно

**Без добавления схемы в "Exposed schemas" в Dashboard, даже с выданными правами, Supabase API не будет видеть таблицы в схеме `genomai`!**

Это настройка на уровне PostgREST (API сервера Supabase), а не на уровне базы данных.

**✅ Выполнено:** Схема добавлена в Dashboard, все должно работать!

