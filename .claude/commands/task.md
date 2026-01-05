# Task Worktree Manager

Управление изолированными worktrees для параллельной работы над issues.

## Команды

```
/task start <issue-number>  — Phase 1: создать worktree для issue
/task plan <issue-number>   — Phase 3: показать план и чеклист
/task test <issue-number>   — Phase 5: запустить тест-чеклист
/task done <issue-number>   — Phase 7: завершить, создать PR, cleanup
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

| Команда | Действие |
|---------|----------|
| start N | `./scripts/task-start.sh N` |
| plan N | Показать planning template (см. ниже) |
| test N | Показать test checklist (см. ниже) |
| done N | `./scripts/task-done.sh N` |
| list | `git worktree list` |
| open N | `cursor .worktrees/issue-N-*` |

### /task plan N — Planning Template

При вызове показать:

```markdown
## Plan for Issue #N

### Pre-conditions
- [ ] Schema checked (execute_sql)
- [ ] Related files identified (Grep/Glob)
- [ ] KNOWN_ISSUES.md reviewed

### Implementation Steps (TodoWrite)
1. [ ] Step 1...
2. [ ] Step 2...
3. [ ] Step 3...

### Test Strategy
| Step | Test Method | Success Criteria |
|------|-------------|------------------|
| 1 | ... | ... |
| 2 | ... | ... |

### Rollback Plan
If X fails: do Y
```

### /task test N — Test Checklist

При вызове показать и выполнить:

```markdown
## Test Checklist for Issue #N

### Pre-test
- [ ] All code committed
- [ ] Branch pushed to origin

### Test by Change Type
| Type | Command | Expected |
|------|---------|----------|
| Workflow | `WebFetch POST {webhook_url}` | HTTP 200 |
| API | `curl -X POST endpoint` | HTTP 200 + body |
| Migration | `execute_sql SELECT...` | Data exists |
| Python | `curl /health` | No errors |

### Post-test Verification
```sql
SELECT * FROM genomai.{table}
WHERE created_at > '{before_test_time}'
LIMIT 5;
```

### Self-Check (BLOCKING)
- [ ] ⛔ Я ЗАПУСТИЛ тест (не validate)?
- [ ] ⛔ Я ВИДЕЛ результат в БД/response?
- [ ] qa-notes/issue-N-*.md создан?

**Если хоть один ❌ — СТОП, нельзя переходить к /task done**
```

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
