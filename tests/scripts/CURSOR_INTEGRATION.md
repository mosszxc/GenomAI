# Интеграция с Cursor

**Версия:** v1.0  
**Назначение:** Как использовать автоматизацию тестирования n8n workflows прямо из Cursor

## 🎯 Преимущества интеграции с Cursor

- ✅ **Автоматическое предложение** запустить тестирование при работе с Issue
- ✅ **Не нужно искать Workflow ID** — извлекается автоматически из Issue
- ✅ **Все результаты в Issue** — автоматически добавляются комментарием
- ✅ **Интеграция в процесс работы** — всё в одном месте (Cursor)

## 🚀 Как использовать в Cursor

### Вариант 1: Автоматический (рекомендуется)

**Когда работаешь с Issue для тестирования, просто скажи мне:**

```
"Протестируй workflow из Issue #22"
```

**Или:**

```
"Запусти тестирование для Issue #22"
```

**Я автоматически:**
1. Прочитаю Issue через GitHub API
2. Извлеку Workflow ID из Issue body
3. Запущу скрипт тестирования
4. Добавлю результаты в Issue

### Вариант 2: Вручную через команду

**В Cursor можно запустить команду:**

```bash
node tests/scripts/test_workflow_from_issue.js 22
```

**Скрипт автоматически:**
- Прочитает Issue #22
- Извлечёт Workflow ID
- Запустит тестирование
- Добавит результаты в Issue

### Вариант 3: С явным Workflow ID

**Если Workflow ID не найден в Issue:**

```bash
node tests/scripts/test_workflow_from_issue.js 22 cGSyJPROrkqLVHZP
```

## 📋 Настройка для Cursor

### 1. Установите переменные окружения

**В Cursor можно установить через `.env` файл или через терминал:**

```bash
# Создайте .env файл в корне проекта
export GITHUB_TOKEN="your-github-token"
export N8N_API_KEY="your-n8n-api-key"
```

**Или добавьте в `tests/config/.env`:**
```bash
GITHUB_TOKEN=your-github-token
N8N_API_KEY=your-n8n-api-key
```

### 2. Правило для Cursor создано

**Файл:** `.cursor/rules/n8n-workflow-testing.mdc`

**Что делает:**
- Автоматически предлагает запустить тестирование при работе с Issue для тестирования
- Извлекает Workflow ID из Issue
- Запускает скрипт тестирования

## 🎯 Примеры использования в Cursor

### Пример 1: Автоматический запуск

**Вы говорите:**
```
"Протестируй workflow из Issue #22"
```

**Я делаю:**
1. Читаю Issue #22 через GitHub API
2. Нахожу Workflow ID: `cGSyJPROrkqLVHZP`
3. Запускаю: `node tests/scripts/test_workflow_from_issue.js 22`
4. Показываю результаты
5. Результаты автоматически добавляются в Issue

### Пример 2: При работе с Issue

**Вы говорите:**
```
"Работаю над Issue #22, нужно протестировать workflow"
```

**Я предлагаю:**
```
"Я вижу, что Issue #22 связан с тестированием workflow.
Workflow ID найден: cGSyJPROrkqLVHZP

Хотите запустить автоматическое тестирование?
Я могу:
1. Запустить тестирование через скрипт (результаты в Issue)
2. Добавить комментарий для GitHub Action

Что предпочитаете?"
```

### Пример 3: При создании Issue

**Вы говорите:**
```
"Создай Issue для тестирования workflow idea_registry_create"
```

**Я создаю Issue и автоматически:**
1. Добавляю Workflow ID в Issue body
2. Добавляю инструкцию для автоматического тестирования
3. Предлагаю сразу запустить тестирование

## 🔄 Полный процесс работы в Cursor

### При работе с Issue для тестирования:

```
1. Вы: "Работаю над Issue #22"
   ↓
2. Я: Читаю Issue, вижу "Testing & Validation" и Workflow ID
   ↓
3. Я: "Нашёл Workflow ID: cGSyJPROrkqLVHZP. Запустить тестирование?"
   ↓
4. Вы: "Да"
   ↓
5. Я: Запускаю скрипт test_workflow_from_issue.js 22
   ↓
6. Скрипт: Ждёт ручного запуска workflow в n8n UI
   ↓
7. Вы: Запускаете workflow в n8n UI
   ↓
8. Скрипт: Автоматически обнаруживает execution
   ↓
9. Скрипт: Добавляет результаты в Issue #22
   ↓
10. Я: Показываю результаты
```

## 💡 Команды для Cursor

### Автоматический запуск (рекомендуется):

**Просто скажи:**
```
"Протестируй workflow из Issue #22"
```

### Ручной запуск:

```bash
# В терминале Cursor
node tests/scripts/test_workflow_from_issue.js 22
```

### С явным Workflow ID:

```bash
node tests/scripts/test_workflow_from_issue.js 22 cGSyJPROrkqLVHZP
```

## 📋 Что нужно настроить

### 1. Переменные окружения

**Создайте `.env` файл или экспортируйте:**

```bash
export GITHUB_TOKEN="ghp_your-token-here"
export N8N_API_KEY="n8n_api_your-key-here"
```

**Как получить токены:**
- **GITHUB_TOKEN:** GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- **N8N_API_KEY:** n8n Dashboard → Settings → API → Create API Key

### 2. Правило для Cursor (уже создано)

**Файл:** `.cursor/rules/n8n-workflow-testing.mdc`

**Что делает:**
- Автоматически предлагает запустить тестирование
- Извлекает Workflow ID из Issue
- Интегрируется в процесс работы

## 🎯 Примеры для разных ситуаций

### Ситуация 1: Работаешь над Issue #22

**Вы:**
```
"Работаю над Issue #22, нужно протестировать workflow"
```

**Я:**
```
"Прочитал Issue #22. Нашёл Workflow ID: cGSyJPROrkqLVHZP

Запустить автоматическое тестирование?
Результаты автоматически появятся в Issue."
```

**Вы:**
```
"Да, запусти"
```

**Я:**
```
Запускаю тестирование...
[показываю процесс]
Результаты добавлены в Issue #22!
```

### Ситуация 2: Создаёшь новый Issue для тестирования

**Вы:**
```
"Создай Issue для тестирования workflow idea_registry_create"
```

**Я:**
```
Создаю Issue...
Добавляю Workflow ID: cGSyJPROrkqLVHZP
Добавляю инструкцию для автоматического тестирования

Хотите сразу запустить тестирование?
```

### Ситуация 3: Обновляешь Issue с тестированием

**Вы:**
```
"Обнови Issue #22, добавь Workflow ID"
```

**Я:**
```
Обновляю Issue #22...
Добавляю Workflow ID: cGSyJPROrkqLVHZP
Добавляю инструкцию для автоматического тестирования

Готово! Теперь можно запустить тестирование командой:
node tests/scripts/test_workflow_from_issue.js 22
```

## 🔧 Troubleshooting

### Ошибка: "GITHUB_TOKEN не установлен"

**Решение:**
```bash
export GITHUB_TOKEN="your-token"
```

### Ошибка: "N8N_API_KEY не установлен"

**Решение:**
```bash
export N8N_API_KEY="your-api-key"
```

### Ошибка: "Workflow ID не найден"

**Решение:**
- Добавьте Workflow ID в Issue body: `**Workflow ID:** \`workflow-id\``
- Или укажите как аргумент: `node test_workflow_from_issue.js 22 workflow-id`

## 📚 Связанные документы

- [HOW_TO_USE.md](./HOW_TO_USE.md) — Как использовать в workflow
- [WORKFLOW_INTEGRATION.md](./WORKFLOW_INTEGRATION.md) — Интеграция в процесс
- [.cursor/rules/n8n-workflow-testing.mdc](../../.cursor/rules/n8n-workflow-testing.mdc) — Правило для Cursor

