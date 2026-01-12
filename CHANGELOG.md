# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-12

### Temporal Migration & Production Release

Major release marking migration from n8n to Temporal workflow orchestration and full production readiness.

### Added

- **Temporal Workflows** - Complete migration from n8n (#241-#245)
  - CreativePipelineWorkflow - video ingestion to idea
  - LearningLoopWorkflow - market feedback processing
  - KeitaroPollerWorkflow - metrics collection
  - MetricsProcessingWorkflow - outcome aggregation
  - HygieneWorkflow - system health monitoring
- **Modular Creative System** - Hook/Promise/Proof module bank (#377, #380, #382)
- **Knowledge Ingestion** - YouTube transcript extraction and premise learning (#453, #455)
- **Multi-Agent Orchestration** - Agent registry and task queue (#351)
- **Feature Experiments** - Shadow/active/deprecated ML feature lifecycle (#303)
- **Staleness Detection** - Auto-injection of external inspiration when system stales

### Fixed

- 200+ bug fixes across all workflows
- Fatigue versioning in Learning Loop (#237, #240)
- HypothesisDelivered events missing (#223)
- Buyer_id propagation through creative chain (#226)
- Avatar hash length validation (#205)
- Keitaro metrics staleness (#206)
- Decision traces integrity (#207)

### Changed

- **BREAKING**: n8n workflows deprecated, Temporal is now primary orchestrator
- Database schema v1.2.0 with 45+ tables
- 7-phase issue workflow for development
- Schema-first coding enforced

### Infrastructure

- 455 issues resolved
- 127 commits since v1.1.0
- Full E2E test coverage
- Automated worktree management

## [1.1.0] - 2025-12-27

### Buyer Production Release

This release marks the production readiness of the Buyer System with full automation pipeline.

### Added

- **Outcome Service** - Centralized outcome aggregation with `/api/outcomes/aggregate` endpoint (#141-#146)
- **Schema Validator** - JSON Schema validation for LLM outputs with API endpoint (#135-#138)
- **Recommendation Engine** - Smart recommendations with Thompson Sampling exploration (#123, #124)
- **Recommendation Delivery** - n8n workflow for automated Telegram delivery (#125)
- **Component Learning** - Granular learning tracking for creative components (#122)
- **Idea Registry API** - Endpoint with canonical hashing utilities
- **Emergent Avatar System** - Dynamic avatar generation with canonical hash
- **Multi-geo Buyers** - Support for multiple geos and verticals per buyer
- **Geo/Vertical Lookup Tables** - Normalized reference data for geos and verticals

### Fixed

- **Death Memory Check** - Now correctly checks `death_state` instead of `status` (#158)
- **Recommendations Routing** - Reordered routes for correct matching
- **Learning Pipeline** - Removed generated columns from inserts, improved error handling
- **Telegram Bot** - `/help` command now works regardless of conversation state

### Changed

- CI pipeline now runs unit tests on push
- Added Schema-First Coding guidelines to development workflow

### Testing

- 22 unit tests for Outcome Service
- 126 system capabilities documented and verified

## [1.0.0] - 2025-12-26

### Production Ready

Initial production release with complete Decision Engine pipeline.

### Added

- Decision Engine with 4-stage validation (schema, death_memory, fatigue, risk_budget)
- Learning Loop with market feedback integration
- Hypothesis Factory for creative generation
- Video Ingestion pipeline
- Telegram Bot for buyer interaction
- n8n orchestration workflows

## [0.1.0] - 2025-12-25

### Initial Release

- Project scaffolding
- Basic Decision Engine structure
- Supabase schema setup
