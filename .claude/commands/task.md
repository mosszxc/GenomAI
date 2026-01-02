# Task Worktree Manager

Управление изолированными worktrees для параллельной работы над issues.

## Команды

```
/task start <issue-number>  — создать worktree для issue
/task done <issue-number>   — завершить, создать PR, cleanup
/task list                  — показать активные worktrees
/task open <issue-number>   — открыть worktree в Cursor
```

## Workflow

1. **Начать задачу:**
   ```bash
   ./scripts/task-start.sh 123
   ```
   - Создаёт branch `issue-123-название-задачи`
   - Создаёт worktree в `.worktrees/`
   - Выводит команды для работы

2. **Работать в worktree:**
   ```bash
   cd .worktrees/issue-123-...
   # или
   cursor .worktrees/issue-123-...
   ```

3. **Завершить задачу:**
   ```bash
   ./scripts/task-done.sh 123
   ```
   - Коммитит изменения (если есть)
   - Пушит branch
   - Создаёт PR с "Closes #123"
   - Предлагает merge
   - Удаляет worktree и branch

## Действие

При вызове `/task`:

1. Парсить аргументы: `$ARGUMENTS`

2. Выполнить соответствующий скрипт:

| Команда | Скрипт |
|---------|--------|
| start N | `./scripts/task-start.sh N` |
| done N | `./scripts/task-done.sh N` |
| list | `git worktree list` |
| open N | `cursor .worktrees/issue-N-*` |

3. Если без аргументов — показать список открытых issues:
   ```bash
   gh issue list --state open --limit 10
   ```

## Параллельная работа

Можно работать над несколькими issues одновременно:

```bash
./scripts/task-start.sh 123  # В терминале 1
./scripts/task-start.sh 124  # В терминале 2

# Worktrees изолированы — изменения не конфликтуют
```

## Интеграция с Claude Code

При запуске агента для issue:
1. `/task start <issue>` — создаёт изолированное пространство
2. Агент работает в worktree
3. `/task done <issue>` — мержит изменения

## Cleanup

Автоматический cleanup merged worktrees:
- GitHub Actions: `.github/workflows/cleanup-branches.yml`
- Локально: `./scripts/cleanup-worktrees.sh`
