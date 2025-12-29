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

## Issue-First Workflow
**ПЕРЕД любой задачей:**
1. Создать issue: `gh issue create` или `scripts/create-issue.sh`
2. Указать зависимости: `Blocked By`, `Blocks`, `Related`
3. Добавить sphere label

**ПОСЛЕ изменений:**
1. Проверить `infrastructure/schemas/dependency_manifest.json` — кто calls/reads/writes затронутые компоненты
2. Запустить `/valid {affected_process}`
3. Cascade check: downstream impacts, затронутые workflows

**Автоматизировано:** sync-dependencies (daily), issue-context (on open)
**Вручную:** создание issue, заполнение зависимостей, cascade check

## Git
Always push after commit. No exceptions.

## Post-Task Loop
Always run Post-Task Knowledge Loop after completing any task. No exceptions.
1. `/qa-notes/{task}.md` — edge-cases, gotchas, constraints
2. `/knowledge/{topic}.md` — create or update relevant notes
3. Summary в конце ответа

## Env
`SUPABASE_URL` `SUPABASE_SERVICE_ROLE_KEY` `API_KEY` `PORT=10000`

## Token Opt
n8n: `mode:"minimal"` `limit:10` | Supabase: `LIMIT 10` | Grep: `head_limit:10` | Explore: `Task subagent_type:"Explore"`

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

