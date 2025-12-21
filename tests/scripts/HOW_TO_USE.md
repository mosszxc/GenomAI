# Как использовать в вашем workflow работы

## 🎯 Простой пример для Issue #22

### Что у вас сейчас:

Issue #22: "Testing & Validation" для STEP 03  
Workflow: `idea_registry_create` (ID: `cGSyJPROrkqLVHZP`)

### Что нужно сделать:

**1. Обновите Issue #22, добавив Workflow ID:**

Добавьте в начало Issue body:
```markdown
**Workflow ID:** `cGSyJPROrkqLVHZP`
**Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow cGSyJPROrkqLVHZP`
```

**2. Добавьте комментарий в Issue #22:**

```
/test-workflow cGSyJPROrkqLVHZP
```

**3. Запустите workflow в n8n UI:**

- Откройте: https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP
- Нажмите на **Manual Trigger** node
- Нажмите **Execute Node**

**4. Готово!** 

GitHub Action автоматически:
- Обнаружит новый execution
- Проверит статус
- Добавит комментарий с результатами в Issue #22

## 🔄 Ваш процесс работы (пошагово)

### При создании Issue для тестирования:

```
1. Создал Issue "Testing & Validation"
   ↓
2. Добавил Workflow ID в Issue body
   ↓
3. Готово! Issue готов к тестированию
```

### При тестировании:

```
1. Добавил комментарий: /test-workflow workflow-id
   ↓
2. GitHub Action запустился автоматически
   ↓
3. Запустил workflow в n8n UI (один раз)
   ↓
4. Результаты автоматически появились в Issue
   ↓
5. Обновил чеклист в Issue на основе результатов
```

### При повторном тестировании:

```
1. Добавил комментарий: /test-workflow workflow-id (снова)
   ↓
2. Запустил workflow в n8n UI (снова)
   ↓
3. Новые результаты автоматически появились в Issue
```

## 📋 Шаблон для Issue

Скопируйте и используйте этот шаблон для Issues с тестированием:

```markdown
## 4️⃣ Testing & Validation: ручные проверки

**Epic:** #X  
**Workflow ID:** `workflow-id-here`  
**Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/workflow-id-here

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow workflow-id-here`

## Обязательные проверки

### Check 1 — [название]
- [ ] Проверка 1
- [ ] Проверка 2

### Check 2 — [название]
- [ ] Проверка 1
- [ ] Проверка 2

### Check 3 — [название]
- [ ] Проверка 1
- [ ] Проверка 2
```

## 💡 Преимущества

### Экономия времени:

**До:**
- Открыть n8n → запустить → проверить → скопировать → вставить = **~70 секунд**

**После:**
- Добавить комментарий → запустить workflow = **~10 секунд**

**Экономия: 60 секунд на каждую проверку!**

### Меньше ошибок:

**До:**
- Легко забыть проверить последний execution
- Нужно помнить, какой execution последний

**После:**
- Скрипт всегда проверяет последний execution автоматически
- Не нужно помнить ничего

### Удобство:

**До:**
- Переключаться между n8n UI и GitHub
- Копировать результаты вручную

**После:**
- Всё в одном месте (GitHub Issue)
- Результаты автоматически появляются

## 🎯 Конкретный пример для Issue #22

### Текущее состояние:

Issue #22 открыт, нужно протестировать workflow `idea_registry_create`

### Что сделать:

1. **Обновите Issue #22:**
   - Добавьте `**Workflow ID:** \`cGSyJPROrkqLVHZP\``
   - Добавьте инструкцию для автоматического тестирования

2. **Добавьте комментарий:**
   ```
   /test-workflow cGSyJPROrkqLVHZP
   ```

3. **Запустите workflow в n8n UI:**
   - https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP
   - Manual Trigger → Execute Node

4. **Готово!** Результаты появятся в Issue автоматически

### После получения результатов:

Обновите чеклист в Issue на основе результатов из комментария:

```markdown
### Check 1 — Determinism
- [x] Два одинаковых decomposed_creative ✅ (результаты в комментарии)
- [x] canonical_hash совпадает ✅
- [x] idea одна ✅
```

## ❓ FAQ

### Нужно ли каждый раз добавлять комментарий?

**Да**, но это занимает 5 секунд. Каждый комментарий запускает новый тест.

### Можно ли протестировать несколько раз подряд?

**Да**, просто добавляйте комментарий `/test-workflow workflow-id` каждый раз.

### Что если workflow не запустился?

Скрипт будет ждать до timeout (3 минуты). Если workflow не запущен, покажет timeout ошибку.

### Нужно ли настраивать что-то каждый раз?

**Нет**, настройка нужна только один раз (добавить `N8N_API_KEY` в GitHub Secrets).

## 📚 Дополнительная информация

- [WORKFLOW_INTEGRATION.md](./WORKFLOW_INTEGRATION.md) — Подробная интеграция в процесс
- [WORKFLOW_VISUAL.md](./WORKFLOW_VISUAL.md) — Визуализация процесса
- [QUICK_START.md](./QUICK_START.md) — Быстрый старт
- [README_GITHUB_ACTIONS.md](./README_GITHUB_ACTIONS.md) — Полная документация

