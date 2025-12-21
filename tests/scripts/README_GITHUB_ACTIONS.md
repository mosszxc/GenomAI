# Автоматическое тестирование n8n Workflows через GitHub Actions

**Версия:** v1.0  
**Назначение:** Автоматический запуск тестирования n8n workflows при упоминании в GitHub Issues

## 🚀 Как использовать

### Способ 1: Комментарий в Issue

Добавьте комментарий в Issue с командой:

```
/test-workflow workflow-id
```

**Пример:**
```
/test-workflow mv6diVtqnuwr7qev
```

**Что произойдёт:**
1. GitHub Action автоматически запустится
2. Скрипт начнёт ждать ручного запуска workflow в n8n UI
3. После запуска workflow вручную, скрипт автоматически обнаружит новый execution
4. Результаты будут добавлены в комментарий к Issue

### Способ 2: Ручной запуск через GitHub Actions UI

1. Перейдите в **Actions** → **Test n8n Workflow**
2. Нажмите **Run workflow**
3. Укажите:
   - **Workflow ID** — ID n8n workflow для тестирования
   - **Issue Number** (опционально) — номер Issue для комментария результатов

## 📋 Требования

### GitHub Secrets

Нужно настроить следующие secrets в GitHub:

1. **N8N_API_KEY** (обязательно)
   - Получить: n8n Dashboard → Settings → API → Create API Key
   - Добавить: Settings → Secrets and variables → Actions → New repository secret

2. **N8N_API_URL** (опционально)
   - По умолчанию: `https://kazamaqwe.app.n8n.cloud/api/v1`
   - Если используется другой instance, добавить как secret

### Настройка Secrets

```bash
# Через GitHub UI:
# 1. Settings → Secrets and variables → Actions
# 2. New repository secret
# 3. Name: N8N_API_KEY
# 4. Value: ваш-api-key
```

## 🎯 Workflow

### 1. Добавьте комментарий в Issue

```
/test-workflow mv6diVtqnuwr7qev
```

### 2. GitHub Action запустится автоматически

Action:
- Извлечёт Workflow ID из комментария
- Запустит скрипт `test_n8n_workflow.js`
- Начнёт ждать ручного запуска workflow

### 3. Запустите workflow вручную в n8n UI

1. Откройте workflow: `https://kazamaqwe.app.n8n.cloud/workflow/{workflow-id}`
2. Нажмите на **Manual Trigger** node
3. Нажмите **Execute Node** или **Test workflow**

### 4. Скрипт автоматически обнаружит execution

- Скрипт проверяет новые executions каждую секунду
- Как только появится новый execution, скрипт покажет результаты
- Результаты автоматически добавятся в комментарий к Issue

## 📊 Пример результата

После выполнения в Issue появится комментарий:

```markdown
## ✅ Результаты тестирования n8n Workflow

🟢 **Статус:** успешно
🔧 **Workflow ID:** `mv6diVtqnuwr7qev`
🔗 **Workflow URL:** https://kazamaqwe.app.n8n.cloud/workflow/mv6diVtqnuwr7qev

<details>
<summary>📊 Детали выполнения</summary>

```
[INFO] Получение информации о workflow: mv6diVtqnuwr7qev
[PASS] Workflow найден: creative_decomposition_llm
[PASS] Новый execution найден: 1400
[PASS] Execution завершился успешно!
```

</details>

---

💡 **Для повторного запуска:** добавьте комментарий `/test-workflow mv6diVtqnuwr7qev`

*Автоматически запущено через GitHub Actions*
```

## ⚙️ Настройки

### Timeout

По умолчанию: 3 минуты (180000ms)

Можно изменить в `.github/workflows/test-n8n-workflow.yml`:
```yaml
TIMEOUT: 300000  # 5 минут
```

### Poll Interval

По умолчанию: 2 секунды (2000ms)

Можно изменить в `.github/workflows/test-n8n-workflow.yml`:
```yaml
POLL_INTERVAL: 1000  # 1 секунда
```

## 🔍 Troubleshooting

### Action не запускается

**Проблема:** Комментарий `/test-workflow` не триггерит Action

**Решение:**
- Убедитесь, что комментарий добавлен в Issue (не в PR)
- Убедитесь, что формат правильный: `/test-workflow workflow-id`
- Проверьте, что Action включён в репозитории (Settings → Actions → General)

### Workflow ID не найден

**Проблема:** Action не может извлечь Workflow ID

**Решение:**
- Убедитесь, что формат правильный: `/test-workflow mv6diVtqnuwr7qev`
- Workflow ID должен быть одним словом (без пробелов)
- Можно использовать ручной запуск через Actions UI

### Timeout

**Проблема:** Скрипт не дождался нового execution

**Решение:**
- Увеличьте `TIMEOUT` в workflow файле
- Убедитесь, что workflow запущен в n8n UI
- Проверьте, что workflow активен

### Ошибка аутентификации

**Проблема:** `N8N_API_KEY не установлен`

**Решение:**
- Убедитесь, что secret `N8N_API_KEY` настроен в GitHub
- Проверьте правильность API ключа
- Убедитесь, что ключ не истёк

## 📚 Связанные документы

- [README_N8N_TESTING.md](./README_N8N_TESTING.md) — Ручное тестирование workflows
- [test_n8n_workflow.js](./test_n8n_workflow.js) — Скрипт для тестирования
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🎯 Примеры использования

### В Issue с тестированием

```markdown
## 4️⃣ Testing & Validation: ручные проверки

**Workflow ID:** `mv6diVtqnuwr7qev`

### Check 1 — Happy path
- [ ] Отправить transcript
- [ ] decomposed_creative появился
- [ ] schema валидна

Для автоматического тестирования добавьте комментарий:
`/test-workflow mv6diVtqnuwr7qev`
```

### В комментарии

```
/test-workflow mv6diVtqnuwr7qev
```

### Ручной запуск через Actions UI

1. Actions → Test n8n Workflow → Run workflow
2. Workflow ID: `mv6diVtqnuwr7qev`
3. Issue Number: `22` (опционально)
4. Run workflow

