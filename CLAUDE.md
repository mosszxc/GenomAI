# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GenomAI is an **Autonomous Creative Decision System** - a deterministic decision-making engine that evaluates which creative ideas to test and scale based on market outcomes. This is NOT a content generation system; it's a decision system that learns from market performance.

**Core Philosophy:** Market is the only ground truth. Decisions are deterministic (same input → same output with decision trace). LLM processes transcripts only - never makes decisions.

## Commands

### Decision Engine Service (Python/FastAPI)

```bash
# Install dependencies
pip install -r decision-engine-service/requirements.txt

# Run locally (development)
uvicorn main:app --reload --host 0.0.0.0 --port 10000

# Run from project root
cd decision-engine-service && uvicorn main:app --reload --host 0.0.0.0 --port 10000
```

### Database Migrations

SQL migrations are in `infrastructure/migrations/`. Run them sequentially (001-007) against Supabase PostgreSQL in the `genomai` schema.

### Testing

Test scripts are in `tests/scripts/` (JavaScript/Shell). Execute with Node.js:
```bash
node tests/scripts/test_ingestion.js
node tests/scripts/test_webhook_simple.js
```

## Architecture

### System Flow

```
Video URL → Ingestion (n8n) → LLM Decomposition → Idea Registry (Supabase)
    → Decision Engine (4 checks) → APPROVE/REJECT/DEFER
    → Hypothesis Factory → Outcome Ingestion (Keitaro) → Learning Loop → Telegram
```

### Decision Engine (Core Component)

Located in `decision-engine-service/`. Applies 4 deterministic checks:

1. **Schema Validity** (`src/checks/schema_validity.py`) - Idea conforms to canonical schema
2. **Death Memory** (`src/checks/death_memory.py`) - Idea/cluster not marked dead
3. **Fatigue Constraint** (`src/checks/fatigue_constraint.py`) - Audience exhaustion check
4. **Risk Budget** (`src/checks/risk_budget.py`) - Active ideas cap control

Results: APPROVE (all pass) | REJECT (checks 1-3 fail) | DEFER (check 4 fails)

### Key Directories

- `decision-engine-service/` - Python FastAPI service (Render-hosted)
- `infrastructure/migrations/` - SQL schema migrations for Supabase
- `infrastructure/schemas/` - JSON schema definitions
- `docs/layer-0-doctrine/` - Foundational principles (read ARCHITECTURE_LOCK.md first)
- `docs/layer-1-logic/` - Domain model, canonical schema, decision logic specs
- `docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/` - Implementation guides
- `.cursor/rules/` - 23 Cursor IDE rule files for n8n, Supabase, Render patterns

### Tech Stack

- **Database:** Supabase PostgreSQL (custom schema: `genomai`)
  - **Project ID:** `ftrerelppsnbdcmtcwya` (UnionGenerateBuying)
  - **Region:** ap-southeast-1
- **Backend:** Python 3.11+, FastAPI, Pydantic
- **Orchestration:** n8n workflows
- **Hosting:** Render (Decision Engine), Supabase (data)
  - **Render URL:** https://genomai.onrender.com
- **Tracking:** Keitaro (pull-based metrics)
- **UI:** Telegram Bot

### Database Schema Access

All Supabase operations use `Accept-Profile: genomai` header to access the custom schema. See `decision-engine-service/src/services/supabase.py` for implementation.

### Canonical Idea Schema

All ideas use strictly-typed enum fields (no free text). Key fields include: `angle_type`, `core_belief`, `promise_type`, `emotion_primary`, `emotion_intensity`, `message_structure`, `opening_type`, `risk_level`, `horizon`. Full spec in `docs/layer-1-logic/CANONICAL_SCHEMA.md`.

## Critical Rules (from ARCHITECTURE_LOCK.md)

1. Market outcomes are the only ground truth for decisions
2. Decisions must be deterministic with full trace
3. ML provides signals (buckets), never bypasses Decision Engine
4. LLM only processes video transcripts - never visuals or ad descriptions
5. Schema-first: all data structures defined in canonical schema before implementation

## Environment Variables

Required for Decision Engine:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `API_KEY` - Decision Engine authentication key
- `PORT` - Service port (default: 10000)

## Documentation Hierarchy

Read in order for full context:
1. `docs/layer-0-doctrine/CONCEPT.md` - System fundamentals
2. `docs/layer-0-doctrine/ARCHITECTURE_LOCK.md` - Non-negotiable rules
3. `docs/layer-1-logic/DOMAIN_MODEL.md` - Canonical terminology
4. `docs/layer-1-logic/CANONICAL_SCHEMA.md` - Data schema specification
5. `docs/layer-4-implementation-planning/TECH_DECISIONS.md` - Technology stack
