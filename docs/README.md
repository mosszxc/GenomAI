# GenomAI Documentation v2.0

> Документация системы GenomAI — Autonomous Creative Decision System

---

## Quick Links

| Document | Description |
|----------|-------------|
| [TEMPORAL_WORKFLOWS.md](./TEMPORAL_WORKFLOWS.md) | Workflow reference |
| [TEMPORAL_RUNBOOK.md](./TEMPORAL_RUNBOOK.md) | Operations guide |
| [SCHEMA_REFERENCE.md](./SCHEMA_REFERENCE.md) | Database schema |
| [API_REFERENCE.md](./API_REFERENCE.md) | API endpoints |
| [SYSTEM_CAPABILITIES.md](./SYSTEM_CAPABILITIES.md) | System capabilities |

---

## Структура документации

### Layer 0 — Doctrine
Фундаментальные принципы и архитектурные инварианты.

📁 [layer-0-doctrine/](./layer-0-doctrine/)
- `CONCEPT.md` — System concept
- `ARCHITECTURE_LOCK.md` — Invariants
- `USAGE_DOCTRINE.md` — Interaction model

### Layer 1 — System Design
Логическая архитектура, схемы данных, контракты.

📁 [layer-1-logic/](./layer-1-logic/)
- `DECISION_ENGINE.md` — DE specification
- `CANONICAL_SCHEMA.md` — Data schema
- `LEARNING_MEMORY_POLICY.md` — Learning rules
- `DATA_FLOW.md` — Data flow
- `LLM_USAGE_POLICY.md` — LLM rules

### Layer 2 — Product Specs
Спецификации продукта и интеграций.

📁 [layer-2-product/](./layer-2-product/)
- `USER_FLOWS.md` — User scenarios
- `TELEGRAM_INTERACTION_MODEL.md` — Telegram spec
- `INPUT_NORMALIZATION.md` — Input rules
- `OUTPUT_PAYLOADS.md` — Output format

### Layer 3 — Implementation Design
Спецификации реализации и инфраструктуры.

📁 [layer-3-implementation-design/](./layer-3-implementation-design/)
- `SERVICE_BOUNDARIES.md` — Service boundaries
- `EVENT_MODEL.md` — Event specification
- `STORAGE_MODEL.md` — Storage model
- `ERROR_HANDLING.md` — Error handling

---

## Operations

| Document | Description |
|----------|-------------|
| [TEMPORAL_WORKFLOWS.md](./TEMPORAL_WORKFLOWS.md) | All 15 Temporal workflows |
| [TEMPORAL_RUNBOOK.md](./TEMPORAL_RUNBOOK.md) | How to operate Temporal |
| [E2E_SERVER_CHECKLIST.md](./E2E_SERVER_CHECKLIST.md) | E2E testing checklist |
| [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) | Known issues & workarounds |

---

## Historical

| Document | Description |
|----------|-------------|
| [DEVELOPMENT_ORDER.md](./DEVELOPMENT_ORDER.md) | Historical development roadmap |

---

**Version:** 2.0.0 | **Updated:** 2026-01-12
