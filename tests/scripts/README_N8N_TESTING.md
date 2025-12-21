# Автоматизация тестирования n8n Workflows

**Версия:** v1.0  
**Проблема:** При отладке workflows с Manual Trigger приходится постоянно нажимать на триггер и проверять последний execution вручную.

**Решение:** Скрипты для автоматического ожидания и проверки executions.

## 📋 Доступные скрипты

### 1. `test_n8n_workflow.js` — Node.js скрипт

**Назначение:** Автоматизированное тестирование n8n workflows с Manual Trigger

**Возможности:**
- ✅ Автоматическое ожидание нового execution после ручного запуска
- ✅ Проверка статуса execution (success/error/running)
- ✅ Детальная информация о выполнении (ноды, длительность, ошибки)
- ✅ Поддержка webhook triggers (автоматический запуск)
- ✅ Подробный вывод с цветами

**Использование:**

```bash
# Базовое использование
export N8N_API_KEY="your-api-key"
export WORKFLOW_ID="your-workflow-id"
node tests/scripts/test_n8n_workflow.js

# Или передать workflow ID как аргумент
node tests/scripts/test_n8n_workflow.js "your-workflow-id"

# С подробным выводом
VERBOSE=true node tests/scripts/test_n8n_workflow.js "your-workflow-id"

# Настроить timeout и интервал проверки
TIMEOUT=60000 POLL_INTERVAL=500 node tests/scripts/test_n8n_workflow.js "your-workflow-id"
```

**Переменные окружения:**

- `N8N_API_URL` — URL n8n API (по умолчанию: `https://kazamaqwe.app.n8n.cloud/api/v1`)
- `N8N_API_KEY` — API ключ n8n (обязательно)
- `WORKFLOW_ID` — ID workflow для тестирования (обязательно)
- `TIMEOUT` — Timeout ожидания в миллисекундах (по умолчанию: 120000 = 2 минуты)
- `POLL_INTERVAL` — Интервал проверки нового execution в миллисекундах (по умолчанию: 1000 = 1 секунда)
- `VERBOSE` — Подробный вывод (`true`/`false`, по умолчанию: `false`)
- `WAIT_FOR_MANUAL` — Ждать ручного запуска если webhook не найден (`true`/`false`, по умолчанию: `true`)
- `TRIGGER_WEBHOOK` — Пытаться запустить через webhook (`true`/`false`, по умолчанию: `true`)
- `WEBHOOK_DATA` — JSON данные для webhook (если нужны)

### 2. `test_n8n_workflow.sh` — Bash скрипт

**Назначение:** Альтернатива Node.js скрипту, работает на bash

**Требования:**
- `curl` (обязательно)
- `jq` (рекомендуется для полной функциональности)

**Использование:**

```bash
# Базовое использование
export N8N_API_KEY="your-api-key"
export WORKFLOW_ID="your-workflow-id"
./tests/scripts/test_n8n_workflow.sh

# Или передать workflow ID как аргумент
./tests/scripts/test_n8n_workflow.sh "your-workflow-id"

# С подробным выводом
VERBOSE=true ./tests/scripts/test_n8n_workflow.sh "your-workflow-id"
```

**Переменные окружения:** Те же, что и для Node.js скрипта

## 🚀 Быстрый старт

### 1. Получить API ключ n8n

1. Откройте n8n Dashboard
2. Перейдите в **Settings** → **API**
3. Создайте новый API ключ
4. Скопируйте ключ

### 2. Настроить окружение

```bash
# Создать .env файл или экспортировать переменные
export N8N_API_KEY="your-api-key-here"
export N8N_API_URL="https://kazamaqwe.app.n8n.cloud/api/v1"
```

### 3. Запустить тест

```bash
# Node.js (рекомендуется)
node tests/scripts/test_n8n_workflow.js "your-workflow-id"

# Или Bash
./tests/scripts/test_n8n_workflow.sh "your-workflow-id"
```

### 4. Запустить workflow вручную

1. Откройте workflow в n8n UI
2. Нажмите на Manual Trigger node
3. Нажмите "Execute Node" или "Test workflow"
4. Скрипт автоматически обнаружит новый execution и покажет результаты

## 📊 Пример вывода

```
============================================================
[HEADER] GenomAI — n8n Workflow Test Script
============================================================
[INFO] Workflow ID: mv6diVtqnuwr7qev
[INFO] API URL: https://kazamaqwe.app.n8n.cloud/api/v1
[INFO] Timeout: 120000ms

[INFO] Получение информации о workflow: mv6diVtqnuwr7qev
[PASS] Workflow найден: creative_decomposition_llm

[INFO] Получение последнего execution до запуска...
[INFO] Последний execution до запуска: 1399 (finished)

[WARN] Ожидание ручного запуска через Manual Trigger...
[INFO] Запустите workflow вручную в n8n UI, скрипт будет ждать новый execution...

[PASS] Новый execution найден: 1400
[INFO] Получение деталей execution...

============================================================
[HEADER] Execution Status
============================================================
[INFO] Execution ID: 1400
[INFO] Status: finished
[INFO] Mode: manual
[INFO] Started: 2025-12-21 15:30:00
[INFO] Stopped: 2025-12-21 15:30:06
[INFO] Duration: 6000ms
[PASS] Execution завершился успешно!
[INFO] Выполнено нод: 11
```

## 🎯 Workflow

### Для workflows с Manual Trigger:

1. **Запустите скрипт:**
   ```bash
   node tests/scripts/test_n8n_workflow.js "workflow-id"
   ```

2. **Скрипт ждёт:**
   - Скрипт показывает последний execution до запуска
   - Скрипт ждёт появления нового execution

3. **Запустите workflow вручную:**
   - Откройте workflow в n8n UI
   - Нажмите на Manual Trigger
   - Нажмите "Execute Node"

4. **Скрипт автоматически:**
   - Обнаруживает новый execution
   - Показывает статус (success/error)
   - Показывает детали выполнения
   - Завершается с правильным exit code

### Для workflows с Webhook Trigger:

1. **Скрипт автоматически:**
   - Обнаруживает webhook trigger
   - Запускает workflow через webhook
   - Ждёт завершения execution
   - Показывает результаты

## 🔧 Интеграция с CI/CD

Скрипты возвращают правильные exit codes:
- `0` — execution завершился успешно
- `1` — execution завершился с ошибкой или timeout
- `2` — execution ещё выполняется (если прерван)

```bash
# В CI/CD pipeline
node tests/scripts/test_n8n_workflow.js "workflow-id" || exit 1
```

## 📝 Примечания

- **API Key:** Обязательно нужен API ключ для доступа к n8n API
- **Workflow должен быть активен:** Скрипт попытается активировать workflow если он неактивен
- **Timeout:** По умолчанию 2 минуты, можно настроить через `TIMEOUT`
- **Poll Interval:** По умолчанию проверка каждую секунду, можно настроить через `POLL_INTERVAL`
- **Webhook:** Если workflow имеет webhook trigger, скрипт попытается запустить его автоматически
- **Manual Trigger:** Если webhook не найден, скрипт ждёт ручного запуска (если `WAIT_FOR_MANUAL=true`)

## 🐛 Troubleshooting

### Ошибка: "N8N_API_KEY не установлен"
```bash
export N8N_API_KEY="your-api-key"
```

### Ошибка: "Workflow не найден"
- Проверьте правильность `WORKFLOW_ID`
- Проверьте доступность n8n API
- Проверьте API ключ

### Timeout: новый execution не появился
- Увеличьте `TIMEOUT` (например, `TIMEOUT=300000` для 5 минут)
- Проверьте, что workflow действительно запущен
- Проверьте, что workflow активен

### Execution не завершается
- Проверьте workflow на наличие бесконечных циклов
- Проверьте логи workflow в n8n UI
- Используйте `VERBOSE=true` для подробного вывода

## 📚 Связанные документы

- [n8n API Documentation](https://docs.n8n.io/api/)
- [n8n MCP Tools](../../../.cursor/rules/n8n-workflow-patterns.mdc)
- [Webhook Testing Guide](../docs/WEBHOOK_GUIDE.md)


