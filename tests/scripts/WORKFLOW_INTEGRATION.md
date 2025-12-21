# Интеграция автоматизации тестирования в процесс работы

**Версия:** v1.0  
**Назначение:** Как использовать автоматизацию тестирования в вашем workflow работы с Issues

## 🎯 Ваш процесс работы

### Типичный Issue для тестирования (например, #22)

```markdown
# 4️⃣ Testing & Validation: ручные проверки

**Epic:** #3  
**Порядок:** 4/4 (финальный шаг)  
**Статус:** 🟡 PENDING  
**Блокируется:** #19 ✅, #20 ✅, #21 ✅

## Задача

Выполнить все обязательные ручные проверки из playbook.

## Обязательные проверки

### Check 1 — Determinism
- [ ] Два одинаковых decomposed_creative
- [ ] canonical_hash совпадает
- [ ] idea одна

### Check 2 — New structure
- [ ] Изменить 1 enum в decomposed_creative
- [ ] Новый canonical_hash
- [ ] Новая Idea

### Check 3 — Idempotency
- [ ] Повтор event `CreativeDecomposed`
- [ ] Новая Idea не создаётся
- [ ] Reuse существующей Idea
```

## ✅ Как использовать автоматизацию

### Шаг 1: Добавьте Workflow ID в Issue

**Обновите Issue, добавив Workflow ID:**

```markdown
# 4️⃣ Testing & Validation: ручные проверки

**Epic:** #3  
**Workflow ID:** `cGSyJPROrkqLVHZP`  ← ДОБАВЬТЕ ЭТО
**Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP

## Задача
...
```

**Или добавьте в секцию "Обязательные проверки":**

```markdown
## Обязательные проверки

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow cGSyJPROrkqLVHZP`

### Check 1 — Determinism
...
```

### Шаг 2: Запустите тестирование

**Вариант A: Через комментарий (рекомендуется)**

Добавьте комментарий в Issue:

```
/test-workflow cGSyJPROrkqLVHZP
```

**Что произойдёт:**
1. GitHub Action запустится автоматически
2. Скрипт начнёт ждать ручного запуска workflow в n8n UI
3. Вы запускаете workflow в n8n UI (один раз)
4. Результаты автоматически появятся в комментарии

**Вариант B: Ручной запуск через Actions UI**

1. Перейдите в **Actions** → **Test n8n Workflow**
2. Нажмите **Run workflow**
3. Укажите:
   - **Workflow ID:** `cGSyJPROrkqLVHZP`
   - **Issue Number:** `22` (опционально)

### Шаг 3: Запустите workflow в n8n UI

1. Откройте workflow: https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP
2. Нажмите на **Manual Trigger** node
3. Нажмите **Execute Node** или **Test workflow**
4. **Всё!** Скрипт автоматически обнаружит execution и покажет результаты

### Шаг 4: Результаты автоматически появятся в Issue

В Issue появится комментарий с результатами:

```markdown
## ✅ Результаты тестирования n8n Workflow

🟢 **Статус:** успешно
🔧 **Workflow ID:** `cGSyJPROrkqLVHZP`
🔗 **Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/cGSyJPROrkqLVHZP

[Детали выполнения...]
```

## 🔄 Полный процесс работы

### До автоматизации:

1. ✅ Создал workflow в n8n
2. ✅ Создал Issue для тестирования
3. ❌ **Вручную:** Открыл n8n UI
4. ❌ **Вручную:** Нажал на Manual Trigger
5. ❌ **Вручную:** Проверил execution в n8n UI
6. ❌ **Вручную:** Скопировал результаты
7. ❌ **Вручную:** Вставил результаты в Issue
8. ❌ **Вручную:** Повторил для каждого Check

**Проблема:** Много ручных действий, легко забыть проверить последний execution

### После автоматизации:

1. ✅ Создал workflow в n8n
2. ✅ Создал Issue для тестирования
3. ✅ Добавил Workflow ID в Issue
4. ✅ Добавил комментарий: `/test-workflow workflow-id`
5. ✅ Запустил workflow в n8n UI (один раз)
6. ✅ **Автоматически:** Результаты появились в Issue

**Преимущество:** Один раз запустил workflow, всё остальное автоматически

## 📋 Примеры для разных шагов

### STEP 02 — Decomposition

**Issue:** Testing & Validation  
**Workflow ID:** `mv6diVtqnuwr7qev`

```markdown
## 6️⃣ Testing & Validation: ручные проверки

**Workflow ID:** `mv6diVtqnuwr7qev`

### Check 1 — Happy path
- [ ] Отправить transcript
- [ ] decomposed_creative появился
- [ ] schema валидна

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow mv6diVtqnuwr7qev`
```

### STEP 03 — Idea Registry

**Issue:** Testing & Validation  
**Workflow ID:** `cGSyJPROrkqLVHZP`

```markdown
## 4️⃣ Testing & Validation: ручные проверки

**Workflow ID:** `cGSyJPROrkqLVHZP`

### Check 1 — Determinism
- [ ] Два одинаковых decomposed_creative
- [ ] canonical_hash совпадает
- [ ] idea одна

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow cGSyJPROrkqLVHZP`
```

## 🎯 Рекомендуемый workflow

### При создании Issue для тестирования:

1. **Создайте Issue** с шаблоном "Testing & Validation"
2. **Добавьте Workflow ID** в Issue body:
   ```markdown
   **Workflow ID:** `workflow-id-here`
   ```
3. **Добавьте инструкцию:**
   ```markdown
   **Для автоматического тестирования:**
   Добавьте комментарий: `/test-workflow workflow-id-here`
   ```

### При тестировании:

1. **Добавьте комментарий:** `/test-workflow workflow-id`
2. **Откройте workflow в n8n UI**
3. **Запустите workflow** (Manual Trigger → Execute Node)
4. **Готово!** Результаты автоматически появятся в Issue

### При повторном тестировании:

1. **Добавьте комментарий:** `/test-workflow workflow-id`
2. **Запустите workflow в n8n UI**
3. **Готово!** Новые результаты автоматически появятся в Issue

## 💡 Преимущества

### Экономия времени:

- **До:** 5-10 минут на каждую проверку (открыть n8n → запустить → проверить → скопировать → вставить)
- **После:** 30 секунд (добавить комментарий → запустить workflow → готово)

### Меньше ошибок:

- **До:** Легко забыть проверить последний execution
- **После:** Скрипт всегда проверяет последний execution автоматически

### История тестирования:

- **До:** Результаты теряются или хранятся в разных местах
- **После:** Все результаты в комментариях к Issue, видна история

### Удобство:

- **До:** Нужно переключаться между n8n UI и GitHub
- **После:** Всё в одном месте (GitHub Issue)

## 📝 Шаблон для Issue

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
```

## 🔧 Настройка (один раз)

1. **GitHub Settings** → **Secrets and variables** → **Actions**
2. **New repository secret:**
   - **Name:** `N8N_API_KEY`
   - **Value:** ваш API ключ из n8n (Settings → API → Create API Key)

**Готово!** Теперь можно использовать автоматизацию.

## ❓ FAQ

### Нужно ли каждый раз добавлять комментарий?

**Да**, но это занимает 5 секунд. Комментарий триггерит GitHub Action.

### Можно ли запустить несколько тестов подряд?

**Да**, просто добавляйте комментарий `/test-workflow workflow-id` каждый раз, когда хотите протестировать.

### Что если workflow не запустился в n8n UI?

Скрипт будет ждать до timeout (по умолчанию 3 минуты). Если workflow не запущен, скрипт покажет timeout ошибку.

### Можно ли использовать для других типов тестов?

**Да**, если тест требует запуска n8n workflow с Manual Trigger, можно использовать этот же подход.

