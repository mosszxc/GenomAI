# Автоматическое исправление и тестирование n8n Workflows

**Версия:** v1.0  
**Назначение:** Автоматическое исправление ошибок и тестирование workflow до успешного результата

## 🎯 Что делает

Скрипт `fix_and_test_workflow.js` автоматически:
1. ✅ Тестирует workflow
2. ✅ Анализирует ошибки
3. ✅ Исправляет ошибки автоматически
4. ✅ Тестирует заново
5. ✅ Повторяет цикл до успеха (максимум 10 итераций)

## 🚀 Использование в Cursor

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
3. Запущу цикл исправления и тестирования
4. Добавлю результаты в Issue

## 📋 Ручной запуск

```bash
# Автоматическое исправление и тестирование
node tests/scripts/fix_and_test_workflow.js 22

# С явным Workflow ID
node tests/scripts/fix_and_test_workflow.js 22 cGSyJPROrkqLVHZP
```

## 🔄 Процесс работы

```
1. Тестирование workflow
   ↓
2. Анализ ошибок
   ↓
3. Автоматическое исправление
   ↓
4. Повторное тестирование
   ↓
5. Если успешно → готово ✅
   Если ошибки → повтор с шага 2
   ↓
6. Максимум 10 итераций
```

## 🛠️ Типы исправляемых ошибок

### ✅ Автоматически исправляются:

1. **Schema Validation**
   - Добавление `useCustomSchema: true`
   - Добавление `schema: "genomai"` для Supabase nodes

2. **Missing Parameters**
   - Автоматическое определение `tableId` из имени node
   - Добавление обязательных параметров

3. **Database Errors**
   - Исправление проблем с schema
   - Добавление `useCustomSchema` для Supabase nodes

### ⚠️ Требуют ручного исправления:

1. **Connection Errors**
   - Проблемы с credentials
   - Проблемы с подключением к базе данных

2. **Expression Errors**
   - Синтаксические ошибки в выражениях
   - Неправильные ссылки на переменные

3. **Unknown Errors**
   - Неизвестные типы ошибок
   - Сложные логические ошибки

## 📊 Пример работы

### Итерация 1:
```
❌ Ошибка: Schema validation failed
🔧 Исправление: Добавлен useCustomSchema и schema для Supabase node
🔄 Повторное тестирование...
```

### Итерация 2:
```
❌ Ошибка: Missing tableId
🔧 Исправление: Добавлен tableId для Supabase node
🔄 Повторное тестирование...
```

### Итерация 3:
```
✅ Workflow работает успешно!
🎉 Готово после 3 итераций
```

## ⚙️ Настройка

### Переменные окружения:

```bash
# Обязательные
export GITHUB_TOKEN="your-github-token"
export N8N_API_KEY="your-n8n-api-key"

# Опциональные
export MAX_ITERATIONS=10  # Максимум итераций (по умолчанию: 10)
export AUTO_FIX=false      # Отключить автоматическое исправление
```

### Параметры:

- `MAX_ITERATIONS` — Максимум итераций исправления (по умолчанию: 10)
- `AUTO_FIX` — Включить/отключить автоматическое исправление (по умолчанию: true)

## 💡 Преимущества

- ✅ **Автоматическое исправление** — не нужно исправлять вручную
- ✅ **Цикл до успеха** — автоматически повторяет до готовности
- ✅ **Анализ ошибок** — определяет тип ошибки и исправляет
- ✅ **Интеграция с Cursor** — всё в одном месте
- ✅ **Результаты в Issue** — автоматически добавляются комментарием

## 📋 Примеры использования

### Пример 1: Автоматический запуск из Cursor

**Вы:**
```
"Исправь и протестируй workflow из Issue #22"
```

**Я:**
```
Читаю Issue #22...
Нашёл Workflow ID: cGSyJPROrkqLVHZP
Запускаю цикл исправления и тестирования...

Итерация 1/10:
⚠️ Запустите workflow в n8n UI...
[анализ ошибок]
🔧 Исправление: добавлен useCustomSchema
🔄 Повторное тестирование...

Итерация 2/10:
⚠️ Запустите workflow в n8n UI...
✅ Workflow работает успешно!
🎉 Готово после 2 итераций
```

### Пример 2: Ручной запуск

```bash
node tests/scripts/fix_and_test_workflow.js 22
```

**Вывод:**
```
[HEADER] ============================================================
[HEADER] GenomAI — Auto-fix and Test Workflow Loop
[HEADER] ============================================================
[INFO] Issue: #22
[INFO] Workflow ID: cGSyJPROrkqLVHZP
[INFO] Max iterations: 10
[INFO] Auto-fix: enabled

[HEADER] Итерация 1/10
[INFO] Запуск тестирования...
[WARN] ⚠️ ВНИМАНИЕ: Запустите workflow в n8n UI
...
[FAIL] Найдено 2 ошибок:
[FAIL]   - Supabase Node: schema_validation - Schema validation failed
[FAIL]   - Supabase Node: missing_parameter - Missing tableId
[INFO] Попытка автоматического исправления...
[INFO] Добавлен useCustomSchema и schema для Supabase Node
[INFO] Добавлен tableId для Supabase Node
[PASS] Исправления применены. Повторное тестирование...

[HEADER] Итерация 2/10
...
[PASS] ✅ Workflow работает успешно после 2 итерации(й)!
```

## 🔧 Troubleshooting

### Ошибка: "Не удалось автоматически исправить"

**Причины:**
- Ошибка требует ручного исправления (connection, expression, unknown)
- Достигнут максимум итераций (10)

**Решение:**
- Проверьте ошибки в последней итерации
- Исправьте вручную в n8n UI
- Запустите тестирование заново

### Ошибка: "Workflow ID не найден"

**Решение:**
- Добавьте Workflow ID в Issue body: `**Workflow ID:** \`workflow-id\``
- Или укажите как аргумент: `node fix_and_test_workflow.js 22 workflow-id`

### Ошибка: "GITHUB_TOKEN не установлен"

**Решение:**
```bash
export GITHUB_TOKEN="your-token"
```

## 📚 Связанные документы

- [README_CURSOR.md](./README_CURSOR.md) — Использование в Cursor
- [HOW_TO_USE.md](./HOW_TO_USE.md) — Как использовать в workflow
- [.cursor/rules/n8n-workflow-testing.mdc](../../.cursor/rules/n8n-workflow-testing.mdc) — Правило для Cursor

