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

## Git
Always push after commit. No exceptions.

## Env
`SUPABASE_URL` `SUPABASE_SERVICE_ROLE_KEY` `API_KEY` `PORT=10000`

## Token Opt
n8n: `mode:"minimal"` `limit:10` | Supabase: `LIMIT 10` | Grep: `head_limit:10` | Explore: `Task subagent_type:"Explore"`

## n8n
Перед работой → `docs/N8N_WORKFLOWS.md`
Webhook issue: API не регистрирует → добавить → активировать в UI → тестировать

Credentials: Supabase `RNItSRYOCypd9H1a` | Telegram `06SWHhdUxiQNwDWD`

## Validation
`/valid {process}` — валидация процесса (learning-loop, hypothesis-factory, decision-engine, video-ingestion)
После изменения workflow/API → автоматически `/valid {affected_process}`

## API
POST `/api/decision/` | POST `/learning/process` | GET `/learning/status` | GET `/health`

## Testing
Результат = данные в БД. Workflow → SELECT → данные есть = работает.
Reviewer agent: workflow ID, таблица, поля, `project_id: ftrerelppsnbdcmtcwya, schema: genomai`
