# Создание Issues для STEP 07

## Быстрый способ

1. Установите GitHub CLI (если еще не установлен):
   ```bash
   brew install gh
   gh auth login
   ```

2. Запустите скрипт:
   ```bash
   export GITHUB_TOKEN=$(gh auth token)
   node .github/create_step07_issues.js
   ```

## Альтернативный способ (через GitHub CLI напрямую)

Используйте команды из файла `.github/create_step07_issues_gh.sh`

## Ручной способ

Создайте issues вручную на основе файла `.github/ISSUES_STEP07.md`:

1. Epic #7: STEP 07 — Outcome Ingestion (MVP)
2. Issue 1: Тестирование workflow Outcome Ingestion Keitaro
3. Issue 2: Проверка данных в БД после выполнения workflow
4. Issue 3: Валидация соответствия playbook и проверка ручных тестов
5. Issue 4: Проверка конфигурации Keitaro

