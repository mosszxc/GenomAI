# Тестовые скрипты

**Версия:** v1.0  
**Назначение:** Автоматизированное тестирование системы GenomAI

## 📋 Доступные скрипты

### 1. `test_ingestion.sh` — Bash скрипт для тестирования Ingestion

**Назначение:** Автоматизированное тестирование STEP 01 — Ingestion

**Использование:**
```bash
# Установите WEBHOOK_URL
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"

# Запустите скрипт
./tests/scripts/test_ingestion.sh

# С verbose выводом
VERBOSE=true ./tests/scripts/test_ingestion.sh
```

**Требования:**
- `curl` должен быть установлен
- `bash` версии 4.0+

**Тесты:**
- ✅ Happy Path
- 🔄 Idempotency
- ⚠️ Edge Cases (один video_url, разные tracker_id и наоборот)
- ❌ Invalid Inputs (missing fields, empty fields, wrong source_type)
- ❌ Garbage Input

### 2. `test_ingestion.js` — Node.js скрипт для тестирования Ingestion

**Назначение:** Альтернатива bash скрипту, работает на Node.js

**Использование:**
```bash
# Установите WEBHOOK_URL
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"

# Запустите скрипт
node tests/scripts/test_ingestion.js

# С verbose выводом
VERBOSE=true node tests/scripts/test_ingestion.js
```

**Требования:**
- Node.js версии 12.0+
- Не требует дополнительных зависимостей (использует встроенные модули)

**Тесты:** Те же, что и в bash скрипте

### 3. `test_n8n_workflow.js` — Node.js скрипт для автоматизации тестирования n8n workflows

**Назначение:** Автоматизация тестирования workflows с Manual Trigger

**Проблема:** При отладке workflows с Manual Trigger приходится постоянно нажимать на триггер и проверять последний execution вручную.

**Решение:** Скрипт автоматически ждёт новый execution после ручного запуска и показывает результаты.

**Использование:**
```bash
# Установите N8N_API_KEY и WORKFLOW_ID
export N8N_API_KEY="your-api-key"
export WORKFLOW_ID="your-workflow-id"

# Запустите скрипт
node tests/scripts/test_n8n_workflow.js

# Или передать workflow ID как аргумент
node tests/scripts/test_n8n_workflow.js "your-workflow-id"

# С verbose выводом
VERBOSE=true node tests/scripts/test_n8n_workflow.js "your-workflow-id"
```

**Требования:**
- Node.js версии 12.0+
- n8n API ключ
- Workflow должен быть активен (скрипт попытается активировать автоматически)

**Возможности:**
- ✅ Автоматическое ожидание нового execution после ручного запуска
- ✅ Проверка статуса execution (success/error/running)
- ✅ Детальная информация о выполнении (ноды, длительность, ошибки)
- ✅ Поддержка webhook triggers (автоматический запуск)
- ✅ Подробный вывод с цветами

**Подробнее:** см. [README_N8N_TESTING.md](./README_N8N_TESTING.md)

### 4. `test_n8n_workflow.sh` — Bash скрипт для автоматизации тестирования n8n workflows

**Назначение:** Альтернатива Node.js скрипту, работает на bash

**Использование:**
```bash
# Установите N8N_API_KEY и WORKFLOW_ID
export N8N_API_KEY="your-api-key"
export WORKFLOW_ID="your-workflow-id"

# Запустите скрипт
./tests/scripts/test_n8n_workflow.sh

# Или передать workflow ID как аргумент
./tests/scripts/test_n8n_workflow.sh "your-workflow-id"
```

**Требования:**
- `curl` (обязательно)
- `jq` (рекомендуется для полной функциональности)
- `bash` версии 4.0+

**Подробнее:** см. [README_N8N_TESTING.md](./README_N8N_TESTING.md)

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
# Скопируйте .env.example
cp tests/config/.env.example .env

# Отредактируйте .env и укажите ваши credentials
nano .env

# Загрузите переменные окружения
source .env  # или export $(cat .env | xargs)
```

### 2. Запуск тестов

```bash
# Тестирование Ingestion (webhook)
./tests/scripts/test_ingestion.sh
# или
node tests/scripts/test_ingestion.js

# Тестирование n8n Workflows (Manual Trigger)
export N8N_API_KEY="your-api-key"
node tests/scripts/test_n8n_workflow.js "workflow-id"
# или
./tests/scripts/test_n8n_workflow.sh "workflow-id"
```

## 📊 Формат вывода

### Успешный тест
```
[PASS] Happy Path — HTTP 200 (expected 200)
```

### Неудачный тест
```
[FAIL] Invalid: Missing video_url — HTTP 400 (expected 400)
```

### Итоги
```
==========================================
Test Results
==========================================
Total:  10
Passed: 10
Failed: 0

All tests passed! ✅
```

## 🔧 Настройка

### Переменные окружения

- `WEBHOOK_URL` — URL webhook для тестирования (обязательно)
- `VERBOSE` — Показывать детальный вывод (опционально, по умолчанию `false`)

### Примеры

```bash
# Локальная разработка
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"
./tests/scripts/test_ingestion.sh

# Production тестирование
export WEBHOOK_URL="https://your-n8n-instance.com/webhook/ingest/creative"
./tests/scripts/test_ingestion.sh

# С verbose выводом
export WEBHOOK_URL="http://localhost:5678/webhook/ingest/creative"
export VERBOSE=true
./tests/scripts/test_ingestion.sh
```

## 📝 Примечания

- Все тесты должны быть идемпотентными
- Тесты не должны изменять production данные
- Используйте тестовые credentials для n8n
- Проверяйте event_log после каждого теста

## 🤖 Автоматизация через GitHub Actions

**Новое!** Автоматический запуск тестирования workflows при упоминании в Issues:

```markdown
# В Issue добавьте комментарий:
/test-workflow workflow-id

# Пример:
/test-workflow mv6diVtqnuwr7qev
```

**Что произойдёт:**
1. GitHub Action автоматически запустится
2. Скрипт начнёт ждать ручного запуска workflow в n8n UI
3. После запуска workflow, результаты автоматически появятся в комментарии к Issue

**Подробнее:** см. [README_GITHUB_ACTIONS.md](./README_GITHUB_ACTIONS.md)

## 🔗 Связанные документы

### Основные документы:
- [README_TASK_BLOCK.md](./README_TASK_BLOCK.md) — **НОВОЕ!** Выполнение блока задач (Epic/Issues) с тестированием и исправлением до конца
- [README_AUTO_FIX.md](./README_AUTO_FIX.md) — Автоматическое исправление и тестирование (цикл до успеха)
- [README_CURSOR.md](./README_CURSOR.md) — **Начните отсюда для Cursor!** Использование в Cursor
- [HOW_TO_USE.md](./HOW_TO_USE.md) — Как использовать в вашем workflow работы
- [CURSOR_INTEGRATION.md](./CURSOR_INTEGRATION.md) — Полная интеграция с Cursor
- [WORKFLOW_INTEGRATION.md](./WORKFLOW_INTEGRATION.md) — Интеграция в процесс работы
- [WORKFLOW_VISUAL.md](./WORKFLOW_VISUAL.md) — Визуализация процесса (до/после)

### Техническая документация:
- [QUICK_START.md](./QUICK_START.md) — Быстрый старт за 3 шага
- [README_GITHUB_ACTIONS.md](./README_GITHUB_ACTIONS.md) — Полная документация GitHub Actions
- [README_N8N_TESTING.md](./README_N8N_TESTING.md) — Ручное тестирование workflows

### Другие документы:
- [Payload Scenarios](../payloads/README.md) — Описание всех тестовых сценариев
- [API Contracts](../docs/API_CONTRACTS.md) — Детальная документация API
- [Webhook Guide](../docs/WEBHOOK_GUIDE.md) — Руководство по работе с webhook'ами
- [n8n Workflow Testing](./README_N8N_TESTING.md) — Автоматизация тестирования n8n workflows

