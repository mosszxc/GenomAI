# QA Notes: Issue #630 - Удалить неиспользуемые системы

## Что изменено

### 1. Agent auto-fix система (удалена)
Лейблы: `agent-ready`, `agent-failed`, `human-only`

Удалённые файлы:
- `scripts/agent-auto.sh` - автономный агент для исправления багов
- `scripts/agent-next.sh` - получение следующей задачи
- `scripts/agent-register.sh` - регистрация агента
- `scripts/agent-add-task.sh` - добавление задачи в очередь
- `scripts/label-for-agent.sh` - разметка issues лейблами
- `.github/workflows/label-issues.yml` - GitHub Action для автолейблинга
- `.claude/commands/agent.md` - Claude skill
- `.claude/commands/next.md` - Claude skill

### 2. n8n workflows (удалена)
Лейбл: `n8n`

Удалённые файлы:
- `infrastructure/n8n-archive/` - вся директория (8 файлов документации)
- `tests/scripts/fix_and_test_workflow.js` - n8n auto-fix тестирование
- `tests/scripts/test_tableid_auto_fix.js` - n8n tableId тестирование
- `tests/scripts/test_workflow_from_issue.js` - n8n workflow тестирование
- `tests/scripts/execute_task_block.js` - n8n task block execution
- `.cursor/rules/workflow-testing-agent.mdc` - n8n auto-fix agent rules
- `.cursor/rules/workflow-error-learning.mdc` - n8n error learning rules

### 3. Multi-agent qa-notes (удалена)
- `qa-notes/issue-350-multi-agent-phase2.md` - устаревшие qa-notes
- `qa-notes/issue-359-agent-identity.md` - устаревшие qa-notes

### 4. Queue/Priority система
Лейблы: `queue-1` до `queue-10`
- Не найдено в кодовой базе

### 5. Parallel groups
Лейблы: `parallel-A`, `parallel-B`, `parallel-C`
- Не найдено в кодовой базе

### 6. Changelog генерация
Лейбл: `changelog`
- Встроена в deploy.sh - NOT удаляется (это часть релизного процесса)

## Итого удалено
- 24 файла
- 2 директории (n8n-archive, + её содержимое)

## Test

```bash
# Проверка что agent-auto скрипт удалён
test ! -f scripts/agent-auto.sh && echo "OK: agent-auto.sh removed"
```
