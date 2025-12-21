# Автоматизация тестирования n8n Workflows через GitHub Issues

**Версия:** v1.0  
**Проблема:** При работе с Issue, связанным с тестированием workflow, нужно вручную запускать скрипт и проверять результаты.

**Решение:** Автоматический запуск тестирования при создании/обновлении Issue или добавлении комментария.

## 🚀 Способы автоматизации

### 1. GitHub Actions (автоматический)

**Файл:** `.github/workflows/test-workflow-on-issue.yml`

**Триггеры:**
- ✅ При создании Issue с текстом "Testing & Validation" или "test-workflow"
- ✅ При редактировании Issue с текстом "Testing & Validation" или "test-workflow"
- ✅ При добавлении комментария `/test-workflow workflow-id`

**Как использовать:**

1. **В Issue body укажите Workflow ID:**
   ```markdown
   Workflow ID: `mv6diVtqnuwr7qev`
   ```

2. **Или добавьте комментарий:**
   ```
   /test-workflow mv6diVtqnuwr7qev
   ```

3. **GitHub Action автоматически:**
   - Извлечёт Workflow ID из Issue
   - Запустит тестирование
   - Добавит комментарий с результатами

**Настройка Secrets:**

В GitHub Settings → Secrets and variables → Actions добавьте:
- `N8N_API_KEY` — API ключ n8n
- `N8N_API_URL` (опционально) — URL n8n API (по умолчанию: `https://kazamaqwe.app.n8n.cloud/api/v1`)

### 2. Локальный скрипт (ручной запуск)

**Файл:** `tests/scripts/test_workflow_from_issue.js`

**Использование:**

```bash
# Установите переменные окружения
export GITHUB_TOKEN="your-github-token"
export N8N_API_KEY="your-n8n-api-key"

# Запустите скрипт с номером Issue
node tests/scripts/test_workflow_from_issue.js 123

# Или укажите Workflow ID явно
node tests/scripts/test_workflow_from_issue.js 123 "workflow-id"
```

**Что делает скрипт:**

1. Получает Issue через GitHub API
2. Извлекает Workflow ID из Issue body (или использует переданный)
3. Запускает тестирование workflow
4. Добавляет комментарий с результатами в Issue

## 📋 Форматы Workflow ID в Issue

Скрипт ищет Workflow ID в следующих форматах:

```markdown
Workflow ID: `mv6diVtqnuwr7qev`
```

```markdown
workflow-id: `mv6diVtqnuwr7qev`
```

```markdown
Workflow: `mv6diVtqnuwr7qev`
```

```markdown
Workflow ID: mv6diVtqnuwr7qev
```

## 🎯 Примеры использования

### Пример 1: Issue с тестированием workflow

**Issue body:**
```markdown
# Testing & Validation

Workflow ID: `mv6diVtqnuwr7qev`

## Проверки:
- [ ] Check 1 — Happy path
- [ ] Check 2 — LLM hallucination
- [ ] Check 3 — Повтор
```

**Результат:** GitHub Action автоматически запустит тестирование при создании Issue.

### Пример 2: Комментарий для повторного запуска

**Комментарий в Issue:**
```
/test-workflow mv6diVtqnuwr7qev
```

**Результат:** GitHub Action запустит тестирование и добавит комментарий с результатами.

### Пример 3: Локальный запуск

```bash
export GITHUB_TOKEN="ghp_..."
export N8N_API_KEY="n8n_api_..."
node tests/scripts/test_workflow_from_issue.js 123
```

**Результат:** Скрипт протестирует workflow и добавит комментарий в Issue #123.

## 📊 Формат результатов

Результаты автоматически добавляются в Issue как комментарий:

```markdown
## ✅ Результаты тестирования n8n Workflow

**Workflow ID:** `mv6diVtqnuwr7qev`
**Статус:** успешно

✅ Execution завершился успешно

<details>
<summary>Детали выполнения</summary>

[Детальный вывод скрипта]

</details>

---
*Автоматически запущено через GitHub Actions*
*Для повторного запуска добавьте комментарий: `/test-workflow mv6diVtqnuwr7qev`*
```

## ⚙️ Настройка

### GitHub Actions Secrets

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте:
   - `N8N_API_KEY` — API ключ n8n (обязательно)
   - `N8N_API_URL` — URL n8n API (опционально)

### Локальные переменные окружения

```bash
# GitHub
export GITHUB_TOKEN="your-github-token"

# n8n
export N8N_API_KEY="your-n8n-api-key"
export N8N_API_URL="https://kazamaqwe.app.n8n.cloud/api/v1"

# Опционально
export VERBOSE="true"
export TIMEOUT="120000"
export POLL_INTERVAL="1000"
```

## 🔧 Troubleshooting

### Workflow ID не найден

**Проблема:** GitHub Action не может найти Workflow ID в Issue.

**Решение:**
- Убедитесь, что в Issue body есть: `Workflow ID: \`workflow-id\``
- Или используйте комментарий: `/test-workflow workflow-id`

### Timeout при ожидании execution

**Проблема:** Скрипт ждёт слишком долго новый execution.

**Решение:**
- Увеличьте `TIMEOUT` в GitHub Actions secrets или переменных окружения
- Убедитесь, что workflow запущен вручную в n8n UI

### Ошибка аутентификации

**Проблема:** `401 Unauthorized` при обращении к n8n API.

**Решение:**
- Проверьте правильность `N8N_API_KEY` в GitHub Secrets
- Убедитесь, что API ключ имеет права на чтение workflows и executions

## 📚 Связанные документы

- [README_N8N_TESTING.md](./README_N8N_TESTING.md) — Ручное тестирование workflows
- [test_n8n_workflow.js](./test_n8n_workflow.js) — Основной скрипт тестирования
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

