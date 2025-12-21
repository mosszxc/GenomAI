# Supabase Setup Guide

**Версия:** v1.0  
**Статус:** ACTIVE  
**Задача:** #8 - Настройка Supabase проекта и окружения

## 📋 Обзор

Этот документ содержит пошаговые инструкции по настройке Supabase для проекта GenomAI.

## 🎯 Требования

- Аккаунт Supabase (https://supabase.com)
- Доступ к созданию проектов
- Базовое понимание PostgreSQL

## 🚀 Шаг 1: Создание проекта

1. Войдите в [Supabase Dashboard](https://app.supabase.com)
2. Нажмите **"New Project"**
3. Заполните форму:
   - **Name:** `genomai` (или другое имя)
   - **Database Password:** Сгенерируйте надежный пароль (сохраните его!)
   - **Region:** Выберите ближайший регион
   - **Pricing Plan:** Free tier для MVP достаточно
4. Нажмите **"Create new project"**
5. Дождитесь создания проекта (обычно 1-2 минуты)

## 🔑 Шаг 2: Получение credentials

После создания проекта:

1. Перейдите в **Settings** → **API**
2. Найдите следующие значения:
   - **Project URL:** `https://xxxxx.supabase.co`
   - **anon/public key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (⚠️ секретный!)

3. Перейдите в **Settings** → **Database**
4. Найдите:
   - **Connection string:** `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres`
   - **Host:** `db.xxxxx.supabase.co`
   - **Database name:** `postgres`
   - **Port:** `5432`
   - **User:** `postgres`
   - **Password:** (тот, что вы создали при создании проекта)

## 📝 Шаг 3: Сохранение credentials

**⚠️ ВАЖНО:** Никогда не коммитьте credentials в репозиторий!

Создайте файл `.env.local` в корне проекта (он уже в `.gitignore`):

```bash
# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database Connection (для прямых подключений)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
DATABASE_HOST=db.xxxxx.supabase.co
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password_here
```

## 🗄️ Шаг 4: Применение миграций

### Вариант 1: Через Supabase SQL Editor (рекомендуется)

1. Перейдите в **SQL Editor** в Supabase Dashboard
2. Откройте файл миграции (начните с `001_event_log.sql`)
3. Скопируйте содержимое файла
4. Вставьте в SQL Editor
5. Нажмите **"Run"** или `Cmd/Ctrl + Enter`
6. Повторите для всех миграций в порядке:
   - `001_event_log.sql`
   - `002_core_tables.sql`
   - `003_transcription.sql`
   - `004_metrics.sql`
   - `005_outcomes.sql`
   - `006_learning.sql`
   - `007_hypotheses.sql`

### Вариант 2: Через psql (командная строка)

```bash
# Установите psql (если еще не установлен)
# macOS: brew install postgresql
# Linux: apt-get install postgresql-client

# Примените миграции
psql "postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres" \
  -f infrastructure/migrations/001_event_log.sql

psql "postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres" \
  -f infrastructure/migrations/002_core_tables.sql

# ... и так далее для всех миграций
```

### Вариант 3: Через Supabase CLI (если установлен)

```bash
# Установите Supabase CLI
# npm install -g supabase

# Логин
supabase login

# Свяжите проект
supabase link --project-ref your-project-ref

# Примените миграции
supabase db push
```

## ✅ Шаг 5: Проверка установки

Выполните следующий SQL запрос в Supabase SQL Editor:

```sql
-- Проверка всех таблиц
SELECT 
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns 
   WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_name IN (
    'event_log',
    'creatives',
    'ideas',
    'transcripts',
    'decomposed_creatives',
    'raw_metrics_current',
    'daily_metrics_snapshot',
    'outcome_aggregates',
    'idea_confidence_versions',
    'fatigue_state_versions',
    'hypotheses',
    'deliveries'
  )
ORDER BY table_name;
```

Ожидаемый результат: 12 таблиц.

## 🔍 Шаг 6: Проверка constraints и triggers

```sql
-- Проверка CHECK constraints
SELECT 
  tc.table_name,
  tc.constraint_name,
  tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.constraint_type = 'CHECK'
ORDER BY tc.table_name;

-- Проверка triggers (append-only protection)
SELECT 
  trigger_name,
  event_object_table,
  action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name LIKE '%prevent%'
ORDER BY event_object_table;
```

## 🛠️ Шаг 7: Настройка n8n (если готово)

После применения миграций, настройте n8n для работы с Supabase:

1. В n8n создайте **Supabase** credentials:
   - **Host:** `db.xxxxx.supabase.co`
   - **Database:** `postgres`
   - **User:** `postgres`
   - **Password:** ваш пароль
   - **Port:** `5432`
   - **SSL:** Enabled

2. Или используйте **Supabase API** node:
   - **Project URL:** `https://xxxxx.supabase.co`
   - **Service Role Key:** ваш service_role key

## 🔒 Шаг 8: Безопасность (опционально, для production)

Для production рекомендуется:

1. **Row Level Security (RLS):**
   - Включите RLS для таблиц, если требуется
   - Создайте policies для доступа

2. **API Keys:**
   - Используйте `anon` key для клиентских приложений
   - Используйте `service_role` key только на сервере/n8n

3. **Connection Pooling:**
   - Используйте Supabase Connection Pooler для production
   - Port: `6543` вместо `5432`

## 📊 Шаг 9: Мониторинг

После настройки:

1. Проверьте **Database** → **Tables** в Supabase Dashboard
2. Убедитесь, что все таблицы видны
3. Проверьте **Database** → **Indexes** для индексов
4. Мониторьте **Logs** для ошибок

## 🐛 Troubleshooting

### Ошибка: "relation already exists"
- Таблица уже создана. Это нормально, миграции идемпотентны.
- Можно пропустить эту миграцию или удалить таблицу (⚠️ только для dev!)

### Ошибка: "permission denied"
- Убедитесь, что используете правильные credentials
- Проверьте, что используете `postgres` user или `service_role` key

### Ошибка: "connection refused"
- Проверьте, что проект активен в Supabase Dashboard
- Проверьте правильность host и port
- Убедитесь, что IP не заблокирован

### Миграция не применяется
- Проверьте синтаксис SQL
- Убедитесь, что нет ошибок в SQL Editor
- Проверьте логи в Supabase Dashboard

## 📚 Дополнительные ресурсы

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [DATA_SCHEMAS.md](../docs/layer-4-implementation-planning/DATA_SCHEMAS.md)
- [TECH_DECISIONS.md](../docs/layer-4-implementation-planning/TECH_DECISIONS.md)

## ✅ Чеклист готовности

- [ ] Проект Supabase создан
- [ ] Credentials сохранены в `.env.local`
- [ ] Все миграции применены
- [ ] Все таблицы созданы (проверка через SQL)
- [ ] Constraints и triggers работают
- [ ] n8n настроен для работы с Supabase (если готово)

## 🎉 Готово!

После выполнения всех шагов, инфраструктура Supabase готова к использованию.

**Следующие шаги:**
- Агент 1 может начать работу с таблицей `creatives`
- n8n workflows могут использовать Supabase для записи данных
- Event logging готов к использованию

