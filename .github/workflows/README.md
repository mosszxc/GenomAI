# GitHub Actions Workflows

## 📋 Доступные Workflows

### 1. Test n8n Workflow

**Файл:** `test-n8n-workflow.yml`

**Назначение:** Автоматическое тестирование n8n workflows при упоминании в GitHub Issues

**Триггеры:**
- Комментарий в Issue: `/test-workflow workflow-id`
- Ручной запуск через Actions UI

**Использование:**

```markdown
# В Issue добавьте комментарий:
/test-workflow mv6diVtqnuwr7qev
```

**Что делает:**
1. Извлекает Workflow ID из комментария
2. Запускает скрипт `test_n8n_workflow.js`
3. Ждёт ручного запуска workflow в n8n UI
4. Автоматически обнаруживает новый execution
5. Добавляет результаты в комментарий к Issue

**Требования:**
- `N8N_API_KEY` — secret в GitHub (обязательно)
- `N8N_API_URL` — secret в GitHub (опционально, по умолчанию используется production URL)

**Настройка Secrets:**

1. Перейдите в **Settings** → **Secrets and variables** → **Actions**
2. Нажмите **New repository secret**
3. Добавьте:
   - **Name:** `N8N_API_KEY`
   - **Value:** ваш API ключ из n8n (Settings → API → Create API Key)
4. (Опционально) Добавьте:
   - **Name:** `N8N_API_URL`
   - **Value:** `https://kazamaqwe.app.n8n.cloud/api/v1`

**Подробнее:** см. [tests/scripts/README_GITHUB_ACTIONS.md](../../tests/scripts/README_GITHUB_ACTIONS.md)

