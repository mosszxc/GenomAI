# CLAUDE.md

Short, dense. Lists > prose.

## Project
**GenomAI** — Autonomous Creative Decision System. Market = ground truth. LLM: transcripts only.

## Stack
DB: Supabase `genomai` schema, project `ftrerelppsnbdcmtcwya`
Backend: FastAPI `decision-engine-service/`, genomai.onrender.com:10000
Orchestration: Temporal | Tracking: Keitaro | UI: Telegram

## Flow
Video → Temporal → LLM → Idea Registry → DE (4 checks) → APPROVE/REJECT/DEFER → Hypothesis → Keitaro → Learning → Telegram

## Decision Engine Checks
schema_validity.py → REJECT | death_memory.py → REJECT | fatigue_constraint.py → REJECT | risk_budget.py → DEFER
All pass = APPROVE

## Commands
```bash
# FastAPI service
cd decision-engine-service && uvicorn main:app --reload --port 10000

# Temporal workers
cd decision-engine-service && python -m temporal.worker

# Temporal schedules
cd decision-engine-service && python -m temporal.schedules list
cd decision-engine-service && python -m temporal.schedules create
cd decision-engine-service && python -m temporal.schedules trigger <schedule-id>
```

## Dirs
`decision-engine-service/` `infrastructure/migrations/` `infrastructure/schemas/` `docs/`

## Schema
Таблицы: `ideas` (не idea_registry), `decisions` (не decision_log), `decomposed_creatives` (не atoms)
Полный референс: `docs/SCHEMA_REFERENCE.md`

## Rules
1. Market = truth 2. Deterministic+trace 3. ML signals only 4. LLM: transcripts 5. Schema-first

## Reference by Task Type
| Задача | Прочитай сначала |
|--------|------------------|
| Temporal workflows | `docs/TEMPORAL_WORKFLOWS.md`, `docs/TEMPORAL_RUNBOOK.md` |
| DB schema changes | `docs/SCHEMA_REFERENCE.md` (check generated columns!) |
| API endpoints | `docs/API_REFERENCE.md` |
| New process | `docs/layer-3-implementation-design/SERVICE_BOUNDARIES.md` |
| Decision Engine | `docs/layer-1-logic/DECISION_ENGINE.md` |

## /idea Workflow (Recommended)
Быстрый старт задачи с изоляцией:
```
/idea описание задачи
```
Автоматически: issue → worktree → Cursor

### Полный цикл
```
1. /idea "описание"           # создаёт issue + worktree + открывает Cursor
2. [работа в изолированном worktree]
3. TEST (обязательно!)
4. qa-notes/issue-XXX-*.md
5. git commit + push (в worktree)
6. ./scripts/task-done.sh XXX --process {process}
   ↓
   ╔═══════════════════════════════════════╗
   ║      VERIFICATION CHECKPOINT          ║
   ║  1. /rw {process} ...                 ║
   ║  2. /valid {process}                  ║
   ║  ✓ qa-notes found                     ║
   ╚═══════════════════════════════════════╝
   ↓
7. [y] → PR → merge → cleanup
```

### task-done.sh флаги
| Флаг | Назначение |
|------|------------|
| `--process <name>` | Подставить процесс в /rw и /valid |
| `--skip-verify` | Пропустить checkpoint (после паузы) |
| `--no-pr` | Только push, без PR |

**Процессы:** decision-engine, learning-loop, hypothesis-factory, video-ingestion, keitaro-poller

### Альтернатива (без /idea)
```bash
gh issue create -t "title" -l enhancement
./scripts/task-start.sh <issue-number>
# ... работа ...
./scripts/task-done.sh <issue-number>
```

## Issue Workflow (7 Phases)

**Правило: ВСЕГДА создавать worktree. Даже для мелких фиксов.**

### Phase 1: STARTUP
```
User: "Работай над issue #123"

1. mcp__github__get_issue(123)     # понять задачу
2. ./scripts/task-start.sh 123     # создать worktree (ОБЯЗАТЕЛЬНО)
3. TodoWrite                        # инициализировать tracking
```

### Phase 2: UNDERSTANDING (READ-ONLY)
```
1. Read issue body + comments
2. Grep/Glob связанные файлы
3. execute_sql - проверить схему БД (Schema-First!)
4. Read docs/KNOWN_ISSUES.md - прошлые уроки
5. Read qa-notes/* - похожие задачи

Output: Requirements, Affected Files, DB Tables, Risks
```

### Phase 3: PLANNING
```
1. Разбить на 3-7 шагов (TodoWrite)
2. Определить test strategy для каждого шага
3. EnterPlanMode если сложная задача (много файлов/подходов)

Критерий выхода: TodoWrite initialized + test plan defined
```

### Phase 4: IMPLEMENTATION
```
For each TodoWrite item:
  1. Mark in_progress
  2. Write failing test (if applicable)
  3. Implement change
  4. Verify locally
  5. Mark completed
  6. git commit + push СРАЗУ (short-lived branches!)
```

### Phase 5: TESTING (BLOCKING!)
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

### Phase 6: DOCUMENTATION
```
1. qa-notes/issue-{N}-*.md - edge cases, gotchas, test commands
2. knowledge/*.md - если новые архитектурные знания
3. KNOWN_ISSUES.md - если lesson learned
```

### Phase 7: COMPLETION
```
1. ./scripts/task-done.sh {N} --process {process}
2. /rw {process} - verification loop
3. /valid {process} - process validation
4. Create PR → Merge → Cleanup
```

### Quick Reference
```
/task start 123    → Phase 1
/task plan 123     → Phase 3 template
/task test 123     → Phase 5 checklist
/task done 123     → Phase 7
```

## Git
Always push after commit. No exceptions.

## ⛔ TEST-AFTER-CHANGE (BLOCKING)
**СТОП. Читай это ПЕРЕД закрытием issue или todo.**

### Правило
```
НЕТ ТЕСТА = НЕТ ЗАКРЫТИЯ
```
Validation (структура) ≠ Test (реальный запуск). Validate — это НЕ тест.

### Обязательные тесты по типу изменения
| Изменение | Тест | Критерий успеха |
|-----------|------|-----------------|
| Workflow | WebFetch webhook + `execute_sql` SELECT | ✅ HTTP 200 + данные в БД |
| API | `curl` endpoint | ✅ HTTP 200 + правильный body |
| Migration | `execute_sql` SELECT | ✅ Данные есть + constraints |
| Python | Запустить endpoint | ✅ Нет ошибок + output |

**Примечание:** Для Temporal workflows используй `python -m temporal.schedules trigger`.

### Before Closing Issue — MANDATORY
1. **RUN THE TEST** (см. таблицу выше)
2. **VERIFY RESULT** (execution success? данные в БД?)
3. **SCREENSHOT/LOG** в qa-notes если нужно
4. Только потом → close issue

### Self-Check
Перед словом "готово" спроси себя:
- [ ] Я ЗАПУСТИЛ тест (не validate, а test)?
- [ ] Я ВИДЕЛ результат (execution log, данные в БД)?
- [ ] Если workflow — был WebFetch на webhook + проверка данных в БД?

**Если хоть один ответ "нет" — СТОП, сначала тест.**

## Post-Task Loop
Always run Post-Task Knowledge Loop after completing any task. No exceptions.
1. `/qa-notes/{task}.md` — edge-cases, gotchas, constraints
2. `/knowledge/{topic}.md` — create or update relevant notes
3. Summary в конце ответа

## Post-Task Checklist (MANDATORY)
**STOP before saying "done". Check ALL:**
- [ ] ⛔ **TEST EXECUTED** (WebFetch webhook / curl / execute_sql) — ПЕРВЫЙ ПУНКТ
- [ ] ⛔ **TEST PASSED** (execution success + данные в БД)
- [ ] `qa-notes/{task}.md` created
- [ ] `knowledge/{topic}.md` created/updated
- [ ] `dependency_manifest.json` checked (if workflow/API changed)
- [ ] `/valid {process}` run (if workflow changed)
- [ ] Git commit + push
- [ ] **Lesson learned** recorded (if issue closed, see below)

**Первые два пункта — БЛОКИРУЮЩИЕ. Без них остальное не имеет смысла.**

## Lessons Learned (on issue close)
При закрытии issue — **сначала проверить** `docs/KNOWN_ISSUES.md` → "Lessons Learned":
1. Если похожий урок уже есть → **не дублировать**, можно добавить ссылку на новый issue
2. Если урок новый → записать по шаблону:
```markdown
### Short Title (что пошло не так)

**Context:** Что делали, какой issue
**Mistake:** В чём была ошибка
**Reality:** Что оказалось на самом деле
**Correct Approach:** Как надо было делать
**Rule:** Короткое правило на будущее
```
Цель: не повторять одни и те же ошибки. Один урок = одна запись.

## Env
`SUPABASE_URL` `SUPABASE_SERVICE_ROLE_KEY` `API_KEY` `PORT=10000`

## Token Optimization

### Workflow Editing (CRITICAL)
```
❌ Несколько Edit для node positions — каждый Edit = 14k tokens
✅ Один batch Edit для всех positions — 15k tokens total
✅ Используй scripts/workflow_tools.py для batch операций
```
**Правило:** Один Edit = одна логическая операция. Cosmetic fixes (positions) — batch.

### MCP Tools

**claude-mem:**
```
❌ search() → get_observations([all_ids])
✅ search() → timeline(anchor=id) → get_observations([filtered_ids])
```

**vibe-kanban (смешанный режим):**
```
❌ list_tasks() каждый раз
❌ update_task() если статус уже изменён в UI
✅ list_tasks(limit:10) один раз в начале
✅ Не дублировать UI действия через MCP
```

**Общие лимиты:**
Supabase: `LIMIT 10` | Grep: `head_limit:10` | Explore: `Task subagent_type:"Explore"`

### /rw Exclusions
Skip /rw для:
- Node position changes (cosmetic)
- Documentation updates
- Comments/formatting only

Run /rw для:
- DB writes (INSERT/UPDATE)
- Workflow logic changes
- API modifications

## Schema-First Coding
**ПЕРЕД написанием кода, работающего с БД:**
```sql
-- Проверить ВСЕ таблицы которые будут использоваться
SELECT column_name, data_type, is_nullable, is_generated, generation_expression
FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name IN ('table1', 'table2');

-- Проверить constraints
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'genomai.table_name'::regclass;
```
**Частые ошибки:**
- Generated columns (win_rate, avg_roi) — нельзя INSERT/UPDATE
- Отсутствующие колонки (geo в creatives)
- CHECK constraints (origin_type + decision_id)

## Render Deploy
Free tier = **3 минуты** на deploy. После push: один `sleep 180`, не несколько коротких.

## Temporal
Документация: `docs/TEMPORAL_WORKFLOWS.md` | `docs/TEMPORAL_RUNBOOK.md`

### Workflows
| Workflow | Queue | Schedule |
|----------|-------|----------|
| CreativePipelineWorkflow | creative-pipeline | Webhook trigger |
| KeitaroPollerWorkflow | metrics | Every 10 min |
| MetricsProcessingWorkflow | metrics | Every 30 min |
| LearningLoopWorkflow | metrics | Every 1 hour |
| DailyRecommendationWorkflow | metrics | 09:00 UTC |
| MaintenanceWorkflow | metrics | Every 6 hours |

### Common Operations
```bash
# List schedules
python -m temporal.schedules list

# Trigger manually
python -m temporal.schedules trigger daily-recommendations

# Pause/resume
python -m temporal.schedules pause keitaro-poller
python -m temporal.schedules resume keitaro-poller
```

### n8n (ARCHIVED)
n8n workflows migrated to Temporal. Archive: `infrastructure/n8n-archive/`

## Validation
`/valid {process}` — валидация процесса (learning-loop, hypothesis-factory, decision-engine, video-ingestion)
После изменения workflow/API → автоматически `/valid {affected_process}`

## API
POST `/api/decision/` | POST `/learning/process` | GET `/learning/status` | GET `/health`

## Testing
Результат = данные в БД. Workflow → SELECT → данные есть = работает.
Reviewer agent: workflow ID, таблица, поля, `project_id: ftrerelppsnbdcmtcwya, schema: genomai`

