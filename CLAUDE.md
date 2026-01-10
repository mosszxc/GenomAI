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
| **Любая задача** | `grep -i "keyword" LESSONS.md` (NOT Read — use grep!) |
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
1. /idea "описание"     → issue + worktree + Cursor
2. Работа в worktree
3. TEST (обязательно!)
4. qa-notes/issue-XXX-*.md
5. git commit + push
6. ./scripts/task-done.sh XXX --process {process}
   → /rw {process} → /valid {process} → PR → merge
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

## Issue Workflow
**Детали:** `.claude/docs/issue-workflow.md`

**Правило:** Работа над issue → `./scripts/task-start.sh {N}` → worktree.

## Git
Always push after commit. No exceptions.

## Testing (BLOCKING)
**Детали:** `.claude/docs/testing-rules.md`

```
НЕТ ТЕСТА = НЕТ ЗАКРЫТИЯ
```
| Изменение | Тест | Критерий |
|-----------|------|----------|
| Workflow | `temporal.schedules trigger` | данные в БД |
| API | `curl` endpoint | HTTP 200 |
| Migration | `execute_sql` SELECT | constraints OK |

## Env
`SUPABASE_URL` `SUPABASE_SERVICE_ROLE_KEY` `API_KEY` `PORT=10000`

**Python:** Использовать `python3` (не `python`) — на macOS `python` не в PATH.

## Token Optimization

| Паттерн | Правило |
|---------|---------|
| Documentation | Один Edit на qa-notes + один на KNOWN_ISSUES.md |
| GitHub | `gh` CLI, не `mcp__github__*` |
| Bash network | Сразу `dangerouslyDisableSandbox: true` |
| Render deploy | `sleep 180`, не polling |
| Secrets | Спросить пользователя, не grep |
| Issue close | Post-Task Loop ПЕРЕД закрытием (см. testing-rules.md) |
| /rw | Только для DB writes, не для cosmetic changes |

**Лимиты:** Supabase `LIMIT 10` | Grep `head_limit:10` | Explore `Task subagent_type:"Explore"`

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

## Validation
`/valid {process}` — валидация процесса (learning-loop, hypothesis-factory, decision-engine, video-ingestion)
После изменения workflow/API → автоматически `/valid {affected_process}`

## API
POST `/api/decision/` | POST `/learning/process` | GET `/learning/status` | GET `/health`

## Testing
Результат = данные в БД. Workflow → SELECT → данные есть = работает.
Reviewer agent: workflow ID, таблица, поля, `project_id: ftrerelppsnbdcmtcwya, schema: genomai`

