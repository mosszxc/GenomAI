# GenomAI

> Autonomous Creative Decision System v2.0

## О проекте

**GenomAI** — автономная система принятия креативных решений для нестабильной рыночной среды.

- Обнаружение устойчивых связок креативных переменных
- Эволюция через контролируемые мутации паттернов
- Управление выгоранием аудитории на уровне кластеров
- Системное повышение hitrate решений

**Принцип:** Рынок — единственный источник истины. Решения оцениваются по последствиям. Обучение на результатах собственных действий.

---

## Архитектура

```
Video → Temporal → LLM → Idea Registry → Decision Engine → Hypothesis → Keitaro → Learning
```

### Decision Engine (4 checks)
```
schema_validity.py → REJECT
death_memory.py    → REJECT
fatigue_constraint → REJECT
risk_budget.py     → DEFER
All pass           → APPROVE
```

### Temporal Workflows

| Workflow | Queue | Trigger |
|----------|-------|---------|
| CreativePipelineWorkflow | creative-pipeline | Webhook |
| ModularHypothesisWorkflow | creative-pipeline | Internal |
| KeitaroPollerWorkflow | metrics | Every 10 min |
| MetricsProcessingWorkflow | metrics | Every 30 min |
| LearningLoopWorkflow | metrics | Every 1 hour |
| DailyRecommendationWorkflow | metrics | 09:00 UTC |
| MaintenanceWorkflow | metrics | Every 6 hours |
| BuyerOnboardingWorkflow | telegram | Telegram /start |
| HistoricalImportWorkflow | telegram | API trigger |
| KnowledgeIngestionWorkflow | knowledge | Transcript webhook |
| PremiseExtractionWorkflow | knowledge | Post-transcription |

---

## Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (`genomai` schema) |
| Backend | FastAPI (Render) |
| Orchestration | Temporal Cloud |
| Tracking | Keitaro |
| UI | Telegram Bot |
| LLM | OpenAI (transcripts only) |
| Transcription | AssemblyAI |

---

## Структура проекта

```
.
├── decision-engine-service/    # FastAPI + Temporal Workers
│   ├── main.py                 # FastAPI entry point
│   ├── src/
│   │   ├── checks/             # DE constraint checks (4)
│   │   ├── routes/             # API endpoints
│   │   └── services/           # Business logic
│   ├── temporal/
│   │   ├── workflows/          # 15 workflows
│   │   ├── activities/         # 24 activities
│   │   ├── worker.py           # Worker definitions
│   │   ├── schedules.py        # Schedule management
│   │   └── config.py           # Temporal config
│   └── tests/                  # Unit tests
├── infrastructure/
│   ├── migrations/             # 42 SQL migrations
│   └── schemas/                # JSON schemas
├── docs/                       # Documentation
│   ├── TEMPORAL_WORKFLOWS.md   # Workflow reference
│   ├── TEMPORAL_RUNBOOK.md     # Operations guide
│   ├── SCHEMA_REFERENCE.md     # DB schema
│   ├── API_REFERENCE.md        # API docs
│   └── layer-*/                # Architecture docs
├── scripts/                    # Dev utilities
│   ├── task-start.sh           # Start issue worktree
│   ├── task-done.sh            # Complete issue + PR
│   └── task-new.sh             # Create new issue
└── qa-notes/                   # Test documentation
```

---

## Быстрый старт

### Запуск сервиса

```bash
cd decision-engine-service

# FastAPI
uvicorn main:app --reload --port 10000

# Temporal Workers
python -m temporal.worker

# Управление schedules
python -m temporal.schedules list
python -m temporal.schedules trigger <schedule-id>
```

### Environment

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
API_KEY=
TEMPORAL_ADDRESS=
TEMPORAL_NAMESPACE=
TEMPORAL_API_KEY=
OPENAI_API_KEY=
ASSEMBLYAI_API_KEY=
KEITARO_API_KEY=
```

---

## v2.0 Features

### Temporal Migration
- Полная миграция с n8n на Temporal Cloud
- 15 workflows, 24 activities
- Durable execution, built-in retry
- Temporal UI для мониторинга

### Modular Creative System
- Module extraction из креативов
- Module bank для повторного использования
- Module learning на outcomes
- Modular hypothesis generation

### Multi-Agent Orchestration
- Agent identity (`/ag1`-`/ag5`, `/next`)
- Temporal supervisor (2h interval)
- Supabase task queue
- Orphan task detection

### Knowledge Extraction
- Premise layer с обучением
- Transcript persistence
- Inspiration system
- Knowledge application workflow

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/genome` | Component performance heatmap |
| `/trends` | Win rate charts |
| `/confidence` | Confidence intervals |
| `/drift` | Performance drift detection |
| `/correlations` | Component synergy |
| `/recommend` | Auto-recommendations |
| `/feedback` | Bug report → GitHub issue |
| `/ag1`-`/ag5` | Agent identity |

### Developer Experience
- Pre-merge testing (git hooks)
- `/idea` command → issue + worktree + Cursor
- Local worktree system
- Auto-cleanup merged branches

---

## Testing

```bash
# Critical tests (~15s)
make test

# All unit tests (~45s)
make test-unit

# Full CI simulation
make ci

# E2E after deploy
make e2e-quick     # Health checks (~30s)
make e2e           # Full flow (~5min)
```

### Git Hooks

```bash
make setup-hooks   # Install once
```

| Stage | Time | Checks |
|-------|------|--------|
| pre-commit | ~20s | lint, format, critical tests |
| pre-push | ~60s | all unit tests |

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/decision/` | POST | Submit decision request |
| `/learning/process` | POST | Trigger learning |
| `/learning/status` | GET | Learning status |
| `/api/schedules/` | GET | List Temporal schedules |
| `/api/schedules/{id}/trigger` | POST | Trigger schedule |

---

## Documentation

### Layer 0 — Doctrine
- [CONCEPT.md](./docs/layer-0-doctrine/CONCEPT.md) — System concept
- [ARCHITECTURE_LOCK.md](./docs/layer-0-doctrine/ARCHITECTURE_LOCK.md) — Invariants

### Layer 1 — Logic
- [DECISION_ENGINE.md](./docs/layer-1-logic/DECISION_ENGINE.md) — DE spec
- [CANONICAL_SCHEMA.md](./docs/layer-1-logic/CANONICAL_SCHEMA.md) — Data schema
- [LEARNING_MEMORY_POLICY.md](./docs/layer-1-logic/LEARNING_MEMORY_POLICY.md) — Learning rules

### Operations
- [TEMPORAL_WORKFLOWS.md](./docs/TEMPORAL_WORKFLOWS.md) — Workflow reference
- [TEMPORAL_RUNBOOK.md](./docs/TEMPORAL_RUNBOOK.md) — Operations guide
- [SCHEMA_REFERENCE.md](./docs/SCHEMA_REFERENCE.md) — DB tables

---

## Releases

| Version | Date | Highlights |
|---------|------|------------|
| [v2.0.0](https://github.com/mosszxc/GenomAI/releases/tag/v2.0.0) | 2026-01-12 | Temporal migration, Modular Creative System |
| [v1.1.0](https://github.com/mosszxc/GenomAI/releases/tag/v1.1.0) | 2025-12-26 | Buyer Production Release |
| [v1.0.0](https://github.com/mosszxc/GenomAI/releases/tag/v1.0.0) | 2025-12-26 | Production Ready |

---

## Принципы

1. **Market = truth** — рынок единственный источник истины
2. **Deterministic + trace** — детерминированные решения с полным trace
3. **ML signals only** — ML только advisory, не decision
4. **LLM: transcripts** — LLM только для обработки транскриптов
5. **Schema-first** — schema определяет всё

---

**Production:** [genomai.onrender.com](https://genomai.onrender.com)
