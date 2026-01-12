## [v1.1.2] - 2026-01-12

### Changes
- f31e2cf feat: complete issue #486 (#532)
- 3ee1a71 docs: document existing E2E testing infrastructure for #529 (#531)
- e4ec09d fix(scripts): complete task-done.sh flow with CI wait, merge, issue close (#530)
- 506b1c1 feat: increase orphan cleanup batch to 500, add error logging (#485) (#528)
- c824790 Closes #483 (#526)
- cd3328a fix(maintenance): add force recovery for stuck creatives > 2h (#481) (#525)
- e07bd25 feat: complete issue #482 (#527)
- f17e513 Heartbeat timeout 60 сек слишком короткий для transcription (#524)
- bbdb273 feat: complete issue #487
- bea497e feat: complete issue #483 (#522)
- 8b11db2 feat: complete issue #476 (#521)
- 2bb0968 feat: increase orphan cleanup batch to 500 with error logging (#485) (#520)
- c5c7408 feat(temporal): add 'failed' status for stuck creatives (#472) (#518)
- da42b91 feat(temporal): add structured logging with trace IDs (#519)
- 28745b5 feat: complete issue #475 (#517)
- 998e170 Closes #471 (#516)
- fb0db56 feat: complete issue #484 (#515)
- c66fe14 fix(temporal): increase heartbeat_timeout from 60s to 5min for transcription (#510)
- 24333d4 feat: complete issue #474 (#513)
- 03bd262 fix(qa-notes): fix test path for issue-473 (#514)
- cf78387 fix: Learning Loop idempotency - prevent duplicate processing (#473) (#512)
- d99c5fa feat: complete issue #479 (#509)
- f369cbe feat: complete issue #468 (#511)
- 60a3fd6 Closes #467 (#508)
- cbfd91f fix: validate --geo flag against VALID_GEOS in /simulate command (#506)
- 2e2e857 docs: require specific functional test before issue completion
- d697b5f docs: add strict warnings about transcript creation rules
- adaf1bb docs: update TRANSCRIPT_WEBHOOK.md with full pipeline documentation
- 0a8e064 Closes #466

### Issues
- Closes #466
- Closes #467
- Closes #468
- Closes #471
- Closes #472
- Closes #473
- Closes #474
- Closes #475
- Closes #476
- Closes #479
- Closes #481
- Closes #482
- Closes #483
- Closes #484
- Closes #485
- Closes #486
- Closes #487
- Closes #506
- Closes #508
- Closes #509
- Closes #510
- Closes #511
- Closes #512
- Closes #513
- Closes #514
- Closes #515
- Closes #516
- Closes #517
- Closes #518
- Closes #519
- Closes #520
- Closes #521
- Closes #522
- Closes #523
- Closes #524
- Closes #525
- Closes #526
- Closes #527
- Closes #528
- Closes #529
- Closes #530
- Closes #531
- Closes #532

---

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.1] - 2026-01-12

### Fixed
- BuyerOnboardingInput telegram_id backward compatibility (#505)

---

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
