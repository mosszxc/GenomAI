# Использование в Cursor

## 🚀 Быстрый старт

### Просто скажи мне:

```
"Исправь и протестируй workflow из Issue #22"
```

**Или:**

```
"Запусти автоматическое исправление для Issue #22"
```

**Я автоматически:**
1. Прочитаю Issue через GitHub API
2. Извлеку Workflow ID из Issue body
3. Запущу цикл исправления и тестирования (до успеха)
4. Добавлю результаты в Issue

### Только тестирование (без исправления):

```
"Протестируй workflow из Issue #22"
```

**Я запущу только тестирование без исправления.**

## 📋 Что нужно настроить (один раз)

### 1. Переменные окружения

**Создайте `.env` файл в корне проекта или экспортируйте:**

```bash
export GITHUB_TOKEN="ghp_your-token-here"
export N8N_API_KEY="n8n_api_your-key-here"
```

**Как получить:**
- **GITHUB_TOKEN:** GitHub → Settings → Developer settings → Personal access tokens
- **N8N_API_KEY:** n8n Dashboard → Settings → API → Create API Key

### 2. Правило для Cursor (уже создано)

**Файл:** `.cursor/rules/n8n-workflow-testing.mdc`

**Что делает:**
- Автоматически предлагает запустить тестирование при работе с Issue
- Извлекает Workflow ID из Issue
- Интегрируется в процесс работы

## 🎯 Примеры использования

### Пример 1: Автоматический запуск

**Вы:**
```
"Протестируй workflow из Issue #22"
```

**Я:**
```
Читаю Issue #22...
Нашёл Workflow ID: cGSyJPROrkqLVHZP
Запускаю тестирование...

⚠️ ВНИМАНИЕ: Запустите workflow в n8n UI:
1. Откройте: https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP
2. Нажмите Manual Trigger → Execute Node

Скрипт ждёт запуска workflow...
```

**После запуска workflow:**
```
✅ Execution найден!
✅ Execution завершился успешно!
Результаты добавлены в Issue #22
```

### Пример 2: При работе с Issue

**Вы:**
```
"Работаю над Issue #22, нужно протестировать workflow"
```

**Я:**
```
Прочитал Issue #22.
Нашёл Workflow ID: cGSyJPROrkqLVHZP

Запустить автоматическое тестирование?
Результаты автоматически появятся в Issue.
```

### Пример 3: Ручной запуск через команду

**В терминале Cursor:**

```bash
node tests/scripts/test_workflow_from_issue.js 22
```

**Скрипт автоматически:**
- Прочитает Issue #22
- Извлечёт Workflow ID
- Запустит тестирование
- Добавит результаты в Issue

## 🔄 Полный процесс

```
1. Вы: "Протестируй workflow из Issue #22"
   ↓
2. Я: Читаю Issue, извлекаю Workflow ID
   ↓
3. Я: Запускаю скрипт test_workflow_from_issue.js 22
   ↓
4. Скрипт: Ждёт ручного запуска workflow в n8n UI
   ↓
5. Вы: Запускаете workflow в n8n UI
   ↓
6. Скрипт: Автоматически обнаруживает execution
   ↓
7. Скрипт: Добавляет результаты в Issue #22
   ↓
8. Я: Показываю результаты
```

## 💡 Преимущества

- ✅ **Не нужно искать Workflow ID** — извлекается автоматически
- ✅ **Все результаты в Issue** — автоматически добавляются комментарием
- ✅ **Интеграция в Cursor** — всё в одном месте
- ✅ **Экономия времени** — один запрос вместо множества действий

## 📚 Подробнее

- [README_AUTO_FIX.md](./README_AUTO_FIX.md) — **НОВОЕ!** Автоматическое исправление и тестирование
- [CURSOR_INTEGRATION.md](./CURSOR_INTEGRATION.md) — Полная документация
- [HOW_TO_USE.md](./HOW_TO_USE.md) — Как использовать в workflow
- [.cursor/rules/n8n-workflow-testing.mdc](../../.cursor/rules/n8n-workflow-testing.mdc) — Правило для Cursor

