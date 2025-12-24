# CLAUDE.md

## Response Style
- Short, dense answers. No restatements, redundancy, metaphors, motivational text
- Prefer lists/tables/schemas. 5 lines > 20 lines
- Only latest message relevant unless user says "use previous context"

## Project
**GenomAI** — Autonomous Creative Decision System. Deterministic decision engine for creative ideas based on market outcomes.

**Philosophy:** Market = ground truth. LLM processes transcripts only, never decides.

## Stack
| Component | Tech | Details |
|-----------|------|---------|
| DB | Supabase PostgreSQL | Schema: `genomai`, Project: `ftrerelppsnbdcmtcwya`, Region: ap-southeast-1 |
| Backend | Python 3.11+, FastAPI | `decision-engine-service/`, Render: genomai.onrender.com |
| Orchestration | n8n | Workflows |
| Tracking | Keitaro | Pull-based metrics |
| UI | Telegram Bot | |

**DB Access:** Header `Accept-Profile: genomai`. See `decision-engine-service/src/services/supabase.py`

## Flow
```
Video → n8n Ingestion → LLM Decomposition → Idea Registry
  → Decision Engine (4 checks) → APPROVE/REJECT/DEFER
  → Hypothesis Factory → Keitaro Outcomes → Learning Loop → Telegram
```

## Decision Engine Checks
| # | Check | File | Fail = |
|---|-------|------|--------|
| 1 | Schema Validity | `src/checks/schema_validity.py` | REJECT |
| 2 | Death Memory | `src/checks/death_memory.py` | REJECT |
| 3 | Fatigue Constraint | `src/checks/fatigue_constraint.py` | REJECT |
| 4 | Risk Budget | `src/checks/risk_budget.py` | DEFER |

All pass = APPROVE

## Commands
```bash
# Dev server
cd decision-engine-service && uvicorn main:app --reload --port 10000

# Tests
node tests/scripts/test_ingestion.js
```

## Directories
| Path | Purpose |
|------|---------|
| `decision-engine-service/` | FastAPI service |
| `infrastructure/migrations/` | SQL migrations (001-007) |
| `infrastructure/schemas/` | JSON schemas |
| `docs/layer-0-doctrine/` | CONCEPT.md, ARCHITECTURE_LOCK.md |
| `docs/layer-1-logic/` | DOMAIN_MODEL.md, CANONICAL_SCHEMA.md |

## Critical Rules
1. Market outcomes = only ground truth
2. Decisions deterministic with full trace
3. ML signals only, never bypasses Decision Engine
4. LLM: transcripts only, no visuals/ad descriptions
5. Schema-first: define before implement

## Env Vars
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `API_KEY`, `PORT=10000`

## Token Optimization

**MCP defaults (use full only for debugging):**
| Tool | Default | Full |
|------|---------|------|
| n8n_get_workflow | `mode:"minimal"` | `mode:"full"` |
| n8n_list_workflows | `limit:10` | `limit:100` |
| n8n_executions | `mode:"summary"` | `mode:"full"` |
| get_node | `detail:"standard"` | `detail:"full"` |

**Supabase:** `LIMIT 10`, select specific columns
**Context7:** Always specify `topic`, start `page:1`
**Files:** `Grep` with `head_limit:10`, `output_mode:"files_with_matches"`
**Exploration:** Use `Task` with `subagent_type:"Explore"`
