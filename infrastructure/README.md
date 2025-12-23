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
├── README.md                          # Этот файл
│
├── Основная документация:
│   ├── SUPABASE_SETUP.md              # Инструкции по настройке Supabase
│   ├── N8N_SETUP.md                   # Инструкции по настройке n8n
│   ├── N8N_CREDENTIALS_TEMPLATE.md    # Шаблоны credentials для n8n
│   ├── N8N_TEST_WORKFLOW.md           # Тестовый workflow для проверки
│   ├── INFRASTRUCTURE_SUMMARY.md      # Итоговая сводка
│   ├── SUPABASE_SCHEMA_EXPOSURE.md    # Настройка экспорта схемы
│   └── RENDER_MCP_INTRO.md            # Интро по Render MCP интеграции
│
├── Telegram:
│   ├── TELEGRAM_BOT_SETUP.md          # Настройка Telegram бота
│   ├── TELEGRAM_WORKFLOWS_QUICK_START.md  # Быстрый старт
│   └── TELEGRAM_SETUP_SUMMARY.md      # Сводка по настройке
│
├── Workflow проблемы и уроки:
│   ├── WORKFLOW_DIFF_ANALYSIS.md      # Анализ различий workflow
│   ├── WORKFLOW_UPDATE_LESSON.md      # Урок: не менять рабочий workflow
│   ├── WORKFLOW_PARAMETERS_RESET_ISSUE.md  # Проблема "слетающих" параметров
│   └── WORKFLOW_CREATION_ANALYSIS.md  # Анализ создания workflow
│
├── Тестирование:
│   ├── TEST_RESULTS_REPORT.md         # Отчет по тестированию
│   ├── STEP02_FINAL_STATUS.md         # Финальный статус STEP 02
│   └── STEP02_TEST_INSTRUCTIONS.md    # Инструкции по тестированию
│
├── migrations/                        # SQL миграции
│   ├── 001_event_log.sql              # Таблица event_log
│   ├── 002_core_tables.sql            # creatives, ideas
│   ├── 003_transcription.sql          # transcripts, decomposed_creatives
│   ├── 004_metrics.sql                # raw_metrics_current, daily_metrics_snapshot
│   ├── 005_outcomes.sql               # outcome_aggregates
│   ├── 006_learning.sql               # idea_confidence_versions, fatigue_state_versions
│   └── 007_hypotheses.sql             # hypotheses, deliveries
│
└── functions/                         # PostgreSQL функции
    └── emit_event.sql                 # Функция для эмиссии событий
```

## 🎯 Задачи Infrastructure Agent

### ✅ Задача #6: Создание таблицы `event_log`
- Файл: `migrations/001_event_log.sql`
- Статус: ✅ Готово (схема `genomai`)

### ✅ Задача #7: Создание всех таблиц для STEP 02-08
- Файлы: `migrations/002-007_*.sql`
- Статус: ✅ Готово (схема `genomai`)

### ✅ Задача #8: Настройка Supabase проекта
- Файл: `SUPABASE_SETUP.md`
- Статус: ✅ Готово

### ✅ Настройка n8n instance
- Файл: `N8N_SETUP.md`
- Тестовый workflow: `GenomAI - Test Supabase Connection` (ID: `cpaFx4dhT5gQBB4C`)
- Статус: ✅ Документация готова, workflow создан (требует настройки credential)

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
   -- Проверьте, что все таблицы созданы в схеме genomai
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'genomai' 
   AND table_type = 'BASE TABLE'
   ORDER BY table_name;
   ```

4. **Настройка n8n:**
   - Следуйте инструкциям в `N8N_SETUP.md`
   - Создайте Postgres credential в n8n
   - Протестируйте подключение через workflow `GenomAI - Test Supabase Connection`

## 📚 Документация

### Основная настройка:
- [Supabase Setup Guide](./SUPABASE_SETUP.md) — Подробная инструкция по настройке Supabase
- [Supabase Schema Exposure](./SUPABASE_SCHEMA_EXPOSURE.md) — Настройка экспорта схемы genomai
- [n8n Setup Guide](./N8N_SETUP.md) — Инструкции по настройке n8n instance
- [n8n Credentials Template](./N8N_CREDENTIALS_TEMPLATE.md) — Шаблоны для credentials
- [n8n Test Workflow](./N8N_TEST_WORKFLOW.md) — Тестовый workflow для проверки
- [Infrastructure Summary](./INFRASTRUCTURE_SUMMARY.md) — Итоговая сводка по инфраструктуре
- [Render MCP Intro](./RENDER_MCP_INTRO.md) — Интро по Render MCP интеграции и использованию

### Telegram:
- [Telegram Bot Setup Guide](./TELEGRAM_BOT_SETUP.md) — Инструкции по настройке Telegram бота
- [Telegram Workflows Quick Start](./TELEGRAM_WORKFLOWS_QUICK_START.md) — Быстрый старт для готовых workflows
- [Telegram Setup Summary](./TELEGRAM_SETUP_SUMMARY.md) — Сводка по настройке

### Workflow проблемы и уроки:
- [Workflow Diff Analysis](./WORKFLOW_DIFF_ANALYSIS.md) — Анализ различий между актуальным и валидированным workflow
- [Workflow Update Lesson](./WORKFLOW_UPDATE_LESSON.md) — Урок: как не менять рабочий workflow
- [Workflow Parameters Reset Issue](./WORKFLOW_PARAMETERS_RESET_ISSUE.md) — Объяснение проблемы "слетающих" параметров
- [Workflow Creation Analysis](./WORKFLOW_CREATION_ANALYSIS.md) — Анализ причин проблем при создании workflow

### Тестирование:
- [Test Results Report](./TEST_RESULTS_REPORT.md) — Отчет по тестированию STEP 01 и STEP 02
- [STEP 02 Final Status](./STEP02_FINAL_STATUS.md) — Финальный статус STEP 02
- [STEP 02 Test Instructions](./STEP02_TEST_INSTRUCTIONS.md) — Инструкции по тестированию

### Спецификации:
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

