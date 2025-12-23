# Команды для создания Issues STEP 07

## Вариант 1: Через GitHub CLI (рекомендуется)

```bash
# Установите GitHub CLI (если еще не установлен)
brew install gh

# Авторизуйтесь
gh auth login

# Запустите скрипт
bash .github/create_step07_issues_gh.sh
```

## Вариант 2: Через curl с токеном

```bash
# Установите токен
export GITHUB_TOKEN=your_token_here

# Запустите скрипт
node .github/create_step07_issues.js
```

## Вариант 3: Ручное создание

Создайте issues вручную на основе файла `.github/ISSUES_STEP07.md`

## Что будет создано:

1. **Epic #7**: STEP 07 — Outcome Ingestion (MVP)
2. **Issue 1**: Тестирование workflow Outcome Ingestion Keitaro
3. **Issue 2**: Проверка данных в БД после выполнения workflow
4. **Issue 3**: Валидация соответствия playbook и проверка ручных тестов
5. **Issue 4**: Проверка конфигурации Keitaro

