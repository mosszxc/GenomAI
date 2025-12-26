# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
