# Issue Workflow (7 Phases)

**Правило: ВСЕГДА создавать worktree. Даже для мелких фиксов.**

## Phase 1: STARTUP
```
User: "Работай над issue #123"

1. gh issue view 123               # понять задачу
2. git worktree list               # проверить существующие
3. ./scripts/task-start.sh 123    # создать worktree (если нет)
4. TodoWrite                       # инициализировать tracking
```

## Phase 2: UNDERSTANDING (READ-ONLY)
```
1. Read issue body + comments
2. Grep/Glob связанные файлы
3. execute_sql - проверить схему БД (Schema-First!)
4. grep -i "keyword" LESSONS.md  # Check lessons FIRST!
5. Read docs/KNOWN_ISSUES.md - прошлые уроки
6. Read qa-notes/* - похожие задачи

Output: Requirements, Affected Files, DB Tables, Risks, Relevant Lessons
```

## Phase 3: PLANNING
```
1. Разбить на 3-7 шагов (TodoWrite)
2. Определить test strategy для каждого шага
3. EnterPlanMode если сложная задача (много файлов/подходов)

Критерий выхода: TodoWrite initialized + test plan defined
```

## Phase 4: IMPLEMENTATION
```
For each TodoWrite item:
  1. Mark in_progress
  2. Write failing test (if applicable)
  3. Implement change
  4. Verify locally
  5. Mark completed
  6. git commit + push СРАЗУ (short-lived branches!)
```

## Phase 5: TESTING (BLOCKING!)
```
| Change Type | Test                    | Verify               |
|-------------|-------------------------|----------------------|
| Workflow    | WebFetch webhook        | execute_sql SELECT   |
| API         | curl endpoint           | Response body        |
| Migration   | execute_sql             | Schema + data        |
| Python      | curl /health            | No errors            |

Self-check:
- [ ] Я ЗАПУСТИЛ тест (не validate)?
- [ ] Я ВИДЕЛ результат (данные в БД, HTTP 200)?
- [ ] Если workflow — WebFetch webhook + проверка данных?

⛔ БЕЗ ПРОХОЖДЕНИЯ ЭТОЙ ФАЗЫ — НЕ ПЕРЕХОДИТЬ К PHASE 6
```

## Phase 6: DOCUMENTATION
```
1. qa-notes/issue-{N}-*.md - edge cases, gotchas, test commands
2. knowledge/*.md - если новые архитектурные знания
3. KNOWN_ISSUES.md - если lesson learned
```

## Phase 7: COMPLETION
```
1. ./scripts/task-done.sh {N} --process {process}
2. /rw {process} - verification loop
3. /valid {process} - process validation
4. Create PR → Merge → Cleanup
```

## Quick Reference
```
/task start 123    → Phase 1
/task plan 123     → Phase 3 template
/task test 123     → Phase 5 checklist
/task done 123     → Phase 7
```
