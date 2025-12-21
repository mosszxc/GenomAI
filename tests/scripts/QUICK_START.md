# Быстрый старт: Автоматизация тестирования n8n Workflows

## 🚀 За 3 шага

### Шаг 1: Настройте GitHub Secrets

1. Перейдите в **Settings** → **Secrets and variables** → **Actions**
2. Нажмите **New repository secret**
3. Добавьте:
   - **Name:** `N8N_API_KEY`
   - **Value:** ваш API ключ из n8n

**Как получить API ключ:**
- Откройте n8n Dashboard: https://kazamaqwe.app.n8n.cloud
- Перейдите в **Settings** → **API**
- Нажмите **Create API Key**
- Скопируйте ключ

### Шаг 2: Добавьте комментарий в Issue

В Issue с тестированием workflow добавьте комментарий:

```
/test-workflow workflow-id
```

**Пример:**
```
/test-workflow mv6diVtqnuwr7qev
```

### Шаг 3: Запустите workflow в n8n UI

1. Откройте workflow: https://kazamaqwe.app.n8n.cloud/workflow/{workflow-id}
2. Нажмите на **Manual Trigger** node
3. Нажмите **Execute Node** или **Test workflow**
4. GitHub Action автоматически обнаружит новый execution и покажет результаты в комментарии!

## ✅ Готово!

Результаты автоматически появятся в комментарии к Issue.

## 📋 Примеры

### В Issue с тестированием

```markdown
## 4️⃣ Testing & Validation: ручные проверки

**Workflow ID:** `mv6diVtqnuwr7qev`

### Check 1 — Happy path
- [ ] Отправить transcript
- [ ] decomposed_creative появился
- [ ] schema валидна

**Для автоматического тестирования:**
Добавьте комментарий: `/test-workflow mv6diVtqnuwr7qev`
```

### Комментарий для запуска

```
/test-workflow mv6diVtqnuwr7qev
```

## 🔧 Troubleshooting

### Action не запускается

- Убедитесь, что комментарий добавлен в **Issue** (не в PR)
- Убедитесь, что формат правильный: `/test-workflow workflow-id`
- Проверьте, что Action включён (Settings → Actions → General)

### Workflow ID не найден

- Убедитесь, что формат правильный: `/test-workflow mv6diVtqnuwr7qev`
- Workflow ID должен быть одним словом (без пробелов)

### Ошибка аутентификации

- Убедитесь, что secret `N8N_API_KEY` настроен в GitHub
- Проверьте правильность API ключа

## 🔄 Интеграция в процесс работы

**Как это вписывается в ваш workflow работы с Issues:**

1. **Создаёте Issue** для тестирования workflow
2. **Добавляете Workflow ID** в Issue body
3. **Добавляете комментарий:** `/test-workflow workflow-id`
4. **Запускаете workflow в n8n UI** (один раз)
5. **Готово!** Результаты автоматически появляются в Issue

**Преимущества:**
- ✅ Не нужно постоянно проверять последний execution вручную
- ✅ Все результаты в одном месте (Issue)
- ✅ История тестирования сохраняется
- ✅ Экономия времени (5-10 минут → 30 секунд)

**Подробнее:** см. [WORKFLOW_INTEGRATION.md](./WORKFLOW_INTEGRATION.md)

## 📚 Подробнее

- [WORKFLOW_INTEGRATION.md](./WORKFLOW_INTEGRATION.md) — Интеграция в процесс работы
- [README_GITHUB_ACTIONS.md](./README_GITHUB_ACTIONS.md) — Полная документация GitHub Actions
- [README_N8N_TESTING.md](./README_N8N_TESTING.md) — Ручное тестирование

