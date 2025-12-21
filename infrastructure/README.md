# GenomAI Infrastructure

**Версия:** v1.0  
**Статус:** ACTIVE  
**Ответственный:** Агент 2 — Infrastructure

## 📋 Обзор

Этот каталог содержит всю инфраструктурную конфигурацию для GenomAI:
- SQL миграции для Supabase PostgreSQL
- Документация по настройке окружения
- Конфигурационные файлы (если требуются)

## 📁 Структура

```
infrastructure/
├── README.md                    # Этот файл
├── SUPABASE_SETUP.md            # Инструкции по настройке Supabase
├── migrations/                   # SQL миграции
│   ├── 001_event_log.sql        # Таблица event_log (задача #6)
│   ├── 002_core_tables.sql      # creatives, ideas (STEP 01, 03)
│   ├── 003_transcription.sql    # transcripts, decomposed_creatives (STEP 01, 02)
│   ├── 004_metrics.sql          # raw_metrics_current, daily_metrics_snapshot (STEP 07)
│   ├── 005_outcomes.sql         # outcome_aggregates (STEP 07)
│   ├── 006_learning.sql         # idea_confidence_versions, fatigue_state_versions (STEP 08)
│   └── 007_hypotheses.sql       # hypotheses, deliveries (STEP 05, 06)
└── functions/                   # PostgreSQL функции (если требуются)
    └── emit_event.sql           # Функция для эмиссии событий
```

## 🎯 Задачи Infrastructure Agent

### ✅ Задача #6: Создание таблицы `event_log`
- Файл: `migrations/001_event_log.sql`
- Статус: Готово

### ✅ Задача #7: Создание всех таблиц для STEP 02-08
- Файлы: `migrations/002-007_*.sql`
- Статус: Готово

### ✅ Задача #8: Настройка Supabase проекта
- Файл: `SUPABASE_SETUP.md`
- Статус: Готово

## 🚀 Быстрый старт

1. **Настройка Supabase:**
   ```bash
   # Следуйте инструкциям в SUPABASE_SETUP.md
   ```

2. **Применение миграций:**
   ```bash
   # Примените миграции в порядке:
   # 001 → 002 → 003 → 004 → 005 → 006 → 007
   ```

3. **Проверка:**
   ```sql
   -- Проверьте, что все таблицы созданы
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name IN (
     'event_log', 'creatives', 'ideas', 'transcripts',
     'decomposed_creatives', 'raw_metrics_current',
     'daily_metrics_snapshot', 'outcome_aggregates',
     'idea_confidence_versions', 'fatigue_state_versions',
     'hypotheses', 'deliveries'
   );
   ```

## 📚 Документация

- [Supabase Setup Guide](./SUPABASE_SETUP.md) — Подробная инструкция по настройке
- [DATA_SCHEMAS.md](../docs/layer-4-implementation-planning/DATA_SCHEMAS.md) — Спецификация схем данных
- [TECH_DECISIONS.md](../docs/layer-4-implementation-planning/TECH_DECISIONS.md) — Технические решения

## ⚠️ Важные правила

1. **Append-only по умолчанию** — большинство таблиц immutable
2. **Версионирование** — состояние хранится как версии
3. **Soft relations** — FK логические, без каскадных delete
4. **Idempotency** — все операции должны быть идемпотентными

## 🔒 Безопасность

- Никогда не коммитьте credentials в репозиторий
- Используйте Supabase Secrets для хранения чувствительных данных
- Проверяйте RLS policies (если используются)

## 📝 Примечания

- Все миграции протестированы на Supabase PostgreSQL
- Миграции можно применять в любом порядке (независимы), но рекомендуется последовательно
- После применения миграций проверьте constraints и индексы

