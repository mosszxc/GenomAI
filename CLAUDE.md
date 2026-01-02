# CLAUDE.md

Short, dense. Lists > prose.

## Project
**GenomAI** — Autonomous Creative Decision System. Market = ground truth. LLM: transcripts only.

## Stack
DB: Supabase `genomai` schema, project `ftrerelppsnbdcmtcwya`
Backend: FastAPI `decision-engine-service/`, genomai.onrender.com:10000
Orchestration: n8n | Tracking: Keitaro | UI: Telegram

## Flow
Video → n8n → LLM → Idea Registry → DE (4 checks) → APPROVE/REJECT/DEFER → Hypothesis → Keitaro → Learning → Telegram

## Decision Engine Checks
schema_validity.py → REJECT | death_memory.py → REJECT | fatigue_constraint.py → REJECT | risk_budget.py → DEFER
All pass = APPROVE

## Commands
`cd decision-engine-service && uvicorn main:app --reload --port 10000`

## Dirs
`decision-engine-service/` `infrastructure/migrations/` `infrastructure/schemas/` `docs/`

## Schema
Таблицы: `ideas` (не idea_registry), `decisions` (не decision_log), `decomposed_creatives` (не atoms)
Полный референс: `docs/SCHEMA_REFERENCE.md`

## Rules
1. Market = truth 2. Deterministic+trace 3. ML signals only 4. LLM: transcripts 5. Schema-first

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

## Git
Always push after commit. No exceptions.

## ⛔ TEST-AFTER-CHANGE (BLOCKING)
**СТОП. Читай это ПЕРЕД закрытием issue или todo.**

### Правило
```
НЕТ ТЕСТА = НЕТ ЗАКРЫТИЯ
```
Validation (структура) ≠ Test (реальный запуск). `n8n_validate_workflow` — это НЕ тест.

### Обязательные тесты по типу изменения
| Изменение | Тест | Критерий успеха |
|-----------|------|-----------------|
| Workflow | `n8n_test_workflow` | ✅ Execution SUCCESS + данные в БД |
| API | `curl` endpoint | ✅ HTTP 200 + правильный body |
| Migration | `execute_sql` SELECT | ✅ Данные есть + constraints |
| Python | Запустить endpoint | ✅ Нет ошибок + output |

### Before Closing Issue — MANDATORY
1. **RUN THE TEST** (см. таблицу выше)
2. **VERIFY RESULT** (execution success? данные в БД?)
3. **SCREENSHOT/LOG** в qa-notes если нужно
4. Только потом → close issue

### Self-Check
Перед словом "готово" спроси себя:
- [ ] Я ЗАПУСТИЛ тест (не validate, а test)?
- [ ] Я ВИДЕЛ результат (execution log, данные в БД)?
- [ ] Если workflow — был `n8n_test_workflow`?

**Если хоть один ответ "нет" — СТОП, сначала тест.**

## Post-Task Loop
Always run Post-Task Knowledge Loop after completing any task. No exceptions.
1. `/qa-notes/{task}.md` — edge-cases, gotchas, constraints
2. `/knowledge/{topic}.md` — create or update relevant notes
3. Summary в конце ответа

## Post-Task Checklist (MANDATORY)
**STOP before saying "done". Check ALL:**
- [ ] ⛔ **TEST EXECUTED** (n8n_test_workflow / curl / execute_sql) — ПЕРВЫЙ ПУНКТ
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

### n8n Deploy Cycle
```
1. Изменить JSON локально
2. validate_workflow с profile:"strict"
3. Fix all errors ЛОКАЛЬНО
4. ТОЛЬКО ПОТОМ deploy
5. Один deploy на задачу
```
**Экономия:** ~9k tokens (избегаем redeploy)

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

**n8n-mcp:**
```
❌ get_node(detail:"full") — 3-8k tokens
✅ get_node(detail:"minimal") — ~200 tokens
✅ validate_workflow ПЕРЕД deploy
```

**Общие лимиты:**
n8n: `mode:"minimal"` `limit:10` | Supabase: `LIMIT 10` | Grep: `head_limit:10` | Explore: `Task subagent_type:"Explore"`

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

## n8n
Перед работой → `docs/N8N_WORKFLOWS.md`
Webhook issue: API не регистрирует → добавить → активировать в UI → тестировать

Credentials: Supabase `RNItSRYOCypd9H1a` | Telegram `06SWHhdUxiQNwDWD`

### n8n Common Issues
- Supabase nodes: ALWAYS `useCustomSchema: true, schema: "genomai"` (default = public)
- HTTP Request to Supabase: `authentication: "predefinedCredentialType"` + `Content-Profile: genomai` header
- Before CREATE: check table NOT NULL constraints via `information_schema.columns`
- Expression refs: verify upstream node output structure before using `$json.field`

## Validation
`/valid {process}` — валидация процесса (learning-loop, hypothesis-factory, decision-engine, video-ingestion)
После изменения workflow/API → автоматически `/valid {affected_process}`

## API
POST `/api/decision/` | POST `/learning/process` | GET `/learning/status` | GET `/health`

## Testing
Результат = данные в БД. Workflow → SELECT → данные есть = работает.
Reviewer agent: workflow ID, таблица, поля, `project_id: ftrerelppsnbdcmtcwya, schema: genomai`

