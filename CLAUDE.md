# CLAUDE.md

## Style
Short, dense. Lists/tables > prose. Only latest message relevant unless "use previous context".

## Project
**GenomAI** — Autonomous Creative Decision System. Market = ground truth. LLM: transcripts only, never decides.

## Stack
| Component | Tech | Details |
|-----------|------|---------|
| DB | Supabase PostgreSQL | Schema: `genomai`, Project: `ftrerelppsnbdcmtcwya`, Header: `Accept-Profile: genomai` |
| Backend | Python 3.11+, FastAPI | `decision-engine-service/`, Render: genomai.onrender.com |
| Orchestration | n8n | Workflows |
| Tracking | Keitaro | Pull-based metrics |
| UI | Telegram Bot | |

## Flow
`Video → n8n → LLM Decomposition → Idea Registry → Decision Engine (4 checks) → APPROVE/REJECT/DEFER → Hypothesis Factory → Keitaro → Learning Loop → Telegram`

## Decision Engine
| Check | File | Fail |
|-------|------|------|
| Schema Validity | `src/checks/schema_validity.py` | REJECT |
| Death Memory | `src/checks/death_memory.py` | REJECT |
| Fatigue Constraint | `src/checks/fatigue_constraint.py` | REJECT |
| Risk Budget | `src/checks/risk_budget.py` | DEFER |

All pass = APPROVE

## Commands
```bash
cd decision-engine-service && uvicorn main:app --reload --port 10000  # Dev
node tests/scripts/test_ingestion.js  # Tests
```

## Directories
`decision-engine-service/` FastAPI | `infrastructure/migrations/` SQL | `infrastructure/schemas/` JSON | `docs/layer-0-doctrine/` CONCEPT, ARCH_LOCK | `docs/layer-1-logic/` DOMAIN, SCHEMA

## Rules
1. Market outcomes = only ground truth | 2. Decisions deterministic with trace | 3. ML signals only, never bypasses DE | 4. LLM: transcripts only | 5. Schema-first

## Env
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `API_KEY`, `PORT=10000`

## Token Optimization
| Tool | Default | Full |
|------|---------|------|
| n8n_get_workflow | `mode:"minimal"` | `mode:"full"` |
| n8n_list_workflows | `limit:10` | `limit:100` |
| n8n_executions | `mode:"summary"` | `mode:"full"` |
| get_node | `detail:"standard"` | `detail:"full"` |

Supabase: `LIMIT 10`, specific columns | Context7: specify `topic`, `page:1` | Files: `Grep` `head_limit:10` | Exploration: `Task` `subagent_type:"Explore"`

## n8n Workflow Reference
**ПЕРЕД работой с n8n** → читай `docs/N8N_WORKFLOWS.md`:
- Создание workflow → смотри паттерны и naming conventions
- Патч workflow → найди workflow по ID, изучи структуру
- Debugging → проверь flow diagram и events

| Действие | Что смотреть в доке |
|----------|---------------------|
| Новый workflow | Patterns, Node Naming, похожий workflow как шаблон |
| Добавить ноду | Connections существующего workflow |
| Emit event | Формат Emit нод, таблица events |
| Вызов другого WF | Chain Calls pattern, HTTP Request config |

## n8n Webhook Issue
Webhook через API не регистрируется (ограничение n8n). Workaround: добавить через API → пользователь активирует в UI → тестировать `n8n_test_workflow`.

## API Endpoints
| Path | Method | Purpose |
|------|--------|---------|
| `/api/decision/` | POST | Make decision for idea |
| `/learning/process` | POST | Process unprocessed outcomes |
| `/learning/status` | GET | Get pending outcomes count |
| `/health` | GET | Health check |

## Testing Philosophy
Результат = данные в БД, не execution status. Workflow executed → SELECT → данные есть → работает.

| Workflow | Таблица | Проверить |
|----------|---------|-----------|
| Ingestion | `ideas` | idea создана, статус |
| Decision Engine | `ideas` | статус APPROVE/REJECT/DEFER |
| Hypothesis Factory | `hypotheses` | гипотеза, связь с idea |
| Metrics Pull | `raw_metrics_current` | метрики записаны |
| Learning Loop | `idea_confidence_versions` | confidence обновлен |

**n8n-workflow-reviewer агент:** передавать workflow ID, целевую таблицу, ожидаемые поля, `project_id: ftrerelppsnbdcmtcwya, schema: genomai`
