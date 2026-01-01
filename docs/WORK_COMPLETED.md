# GenomAI - Work Completed Summary

**Дата:** 2026-01-01
**Период работы:** 2025-12-21 - 2026-01-01
**Версия:** v1.1.0

---

## Статус системы: OPERATIONAL (с 2025-12-26)

Все основные пайплайны системы GenomAI работают. Есть открытые issues для data pipeline (#199, #209).

### Database State (genomai schema)
| Table | Records | Status |
|-------|---------|--------|
| creatives | 9 | OK |
| ideas | 3 | OK |
| decisions | 5 | OK |
| hypotheses | 2 | OK |
| transcripts | 1 | OK |
| decomposed_creatives | 4 | OK |
| deliveries | 0 | - |
| decision_traces | 4 | OK |
| event_log | 161 | OK |
| buyers | 1 | OK |
| raw_metrics_current | 2 | OK |
| daily_metrics_snapshot | 4 | OK |
| component_learnings | 0 | ⚠️ |

---

## Active Workflows (32)

| Pipeline | Workflow | ID | Status |
|----------|----------|-----|--------|
| **Telegram Router** | Telegram Router | `BuyQncnHNb7ulL6z` | ACTIVE |
| **Buyer** | Buyer Onboarding | `hgTozRQFwh4GLM0z` | ACTIVE |
| | Buyer Creative Registration | `d5i9dB2GNqsbfmSD` | ACTIVE |
| | Buyer Stats Command | `rHuT8dYyIXoiHMAV` | ACTIVE |
| | Buyer Daily Digest | `WkS1fPSxZaLmWcYy` | ACTIVE |
| | Buyer Test Conclusion Checker | `4uluD04qYHhsetBy` | ACTIVE |
| | Zaliv Session Handler | `97cj3kRY6zzlAy0M` | ACTIVE |
| | Creative Reply Handler | `9nCezru94d0ABHh4` | ACTIVE |
| **Creative Ingestion** | GenomAI - Creative Transcription | `WMnFHqsFh8i7ddjV` | ACTIVE |
| | creative_decomposition_llm | `mv6diVtqnuwr7qev` | ACTIVE |
| | creative_ingestion_webhook | `dvZvUUmhtPzYOK7X` | ACTIVE |
| | Spy Creative Registration | `pL6C4j1uiJLfVRIi` | ACTIVE |
| **Idea Registry** | idea_registry_create | `cGSyJPROrkqLVHZP` | ACTIVE |
| **Decision Engine** | decision_engine_mvp | `YT2d7z5h9bPy1R4v` | ACTIVE |
| | keep_alive_decision_engine | `ClXUPP2IvWRgu99y` | ACTIVE |
| **Hypothesis Factory** | hypothesis_factory_generate | `oxG1DqxtkTGCqLZi` | ACTIVE |
| | Telegram Hypothesis Delivery | `5q3mshC9HRPpL6C0` | ACTIVE |
| **Metrics & Learning** | Keitaro Poller | `0TrVJOtHiNEEAsTN` | ACTIVE |
| | Snapshot Creator | `Gii8l2XwnX43Wqr4` | ACTIVE |
| | Outcome Processor | `bbbQC4Aua5E3SYSK` | ACTIVE |
| | Outcome Aggregator | `243QnGrUSDtXLjqU` | ACTIVE |
| | Learning Loop v2 | `fzXkoG805jQZUR3S` | ACTIVE |
| **Recommendations** | Daily Recommendation Generator | `wgEdEqt2BA3P9JlA` | ACTIVE |
| | Recommendation Delivery | `QC8bmnAYdH5mkntG` | ACTIVE |
| **Historical Import** | Historical Creative Import | `1FC7amTd3dCRZPEa` | ACTIVE |
| | Buyer Historical Loader | `lmiWkYTRZPSpydJH` | ACTIVE |
| | Buyer Historical URL Handler v2 | `6tu8j4M4wvwi0pyB` | ACTIVE |
| | Historical Import Video Handler | `UYgvqpsU3TMzb2Qd` | ACTIVE |
| **Infrastructure** | Pipeline Health Monitor | `H1uuOanSy627H4kg` | ACTIVE |
| | Data Integrity Check | `IEu0VguJiGwZsr92` | ACTIVE |
| **Utility** | TranslateText | `fcnpPrj9sCFUqoWF` | ACTIVE |
| | AudioTranscribe | `zwtqav0d2R35zQot` | ACTIVE |

---

## Completed Issues (80+)

### Recent Fixes (Issues #175-202) — December 2025

- [x] #202: Learning Loop not populating component_learnings - FIXED (UPSERT pattern)
- [x] #201: Premise Layer not operational - FIXED
- [x] #198: Hypothesis Factory not generating hypotheses - FIXED
- [x] #197: Spy Creative Registration Insert node empty URL - FIXED
- [x] #196: Add vertical/geo filtering to DE checks - DONE
- [x] #195: Implement fatigue_constraint with vertical/geo - DONE
- [x] #194: Include geo in avatar canonical hash - DONE
- [x] #193: Add target_vertical/target_geo to creatives - DONE
- [x] #191: Audit multi-vertical/geo support for buyers - DONE
- [x] #190: 12 creatives stuck in transcription - FIXED
- [x] #189: Decision values lowercase→uppercase - FIXED
- [x] #188: Auto-reset buyer_states after 15 min AFK - DONE
- [x] #187: Keitaro Poller broken connection - FIXED
- [x] #186: Keitaro Poller broken Loop→GetMetrics - FIXED
- [x] #183: Double-encoded JSON payload - FIXED
- [x] #182: OOM crash on large files >50MB - FIXED
- [x] #181: Repeat creative no bot response - FIXED
- [x] #180: Zaliv session 0 creatives on /done - FIXED
- [x] #179: Decomposition duplicate transcript - FIXED
- [x] #178: Spy Creative Registration invalid creative_id - FIXED
- [x] #177: Transcription fails for non-public GDrive - FIXED
- [x] #176: JSON string iteration bug in Recommendations - FIXED
- [x] #175: Spy Creative Telegram markdown error - FIXED

### Critical Fixes (Issues #75-89)
- [x] #75: Learning Loop v2 workflow validation errors - FIXED
- [x] #76: hypothesis_factory_generate 5 validation errors - FIXED
- [x] #77: Buyer Creative Registration 7 Supabase errors - FIXED
- [x] #78: Keitaro Poller 2 expression format errors - FIXED
- [x] #79: 9 creatives stuck without decomposition - FIXED
- [x] #80: 12 DecisionAborted events idea_not_found - FIXED
- [x] #81: All MVP workflows typeVersions updated - FIXED
- [x] #82: Buyer onboarding tested - DONE
- [x] #83-89: Various bug fixes - FIXED

### Infrastructure (Issues #52, #70-74, #91)
- [x] #52: Decision Engine Supabase credentials on Render - FIXED
- [x] #70: Migrations 008-012 applied (learning loop, buyer tracking)
- [x] #71: Learning Loop backend deployed to Render
- [x] #72: Buyer Onboarding flow validated
- [x] #73: Component Learnings aggregation implemented
- [x] #74: End-to-end Learning Loop test - PASSED
- [x] #91: Render cold start 503 error - FIXED (keep-alive workflow)

### Test Issues (Issues #93-101)
- [x] #93: Creative Ingestion Pipeline - ALL TESTS PASSED
- [x] #94: Idea Registry Pipeline - ALL TESTS PASSED
- [x] #95: Decision Engine API & Checks - ALL TESTS PASSED
- [x] #96: Hypothesis Factory & Telegram Delivery - ALL TESTS PASSED
- [x] #97: Buyer Pipeline - ALL TESTS PASSED
- [x] #98: Metrics & Learning Pipeline - ALL TESTS PASSED
- [x] #99: Telegram Router - ALL TESTS PASSED
- [x] #100: Historical Import Pipeline - ALL TESTS PASSED
- [x] #101: Keep-alive & Cold Start Recovery - ALL TESTS PASSED

---

## Key Fixes Applied

### 1. Check→If Anti-pattern (CRITICAL)
**Problem:** Supabase `getAll` → If node → Create/Update. Empty array stops flow silently.

**Fixed in:**
- Keitaro Poller: Direct Supabase create + `onError: continueRegularOutput`
- Snapshot Creator: Added bypass connection
- Outcome Aggregator: Direct connection

### 2. SplitInBatches Wrong Output
**Problem:** Processing connected to output 0 (done) instead of output 1 (loop).

**Fixed in:**
- Keitaro Poller: Loop Over Campaigns connected to output 1

### 3. Wrong Webhook URLs
**Fixed URLs:**
- `unighaz.app.n8n.cloud` → `kazamaqwe.app.n8n.cloud`
- `learning-loop` → `learning-loop-v2`
- HTTP method GET → POST with body

### 4. Cold Start Protection (Issue #91)
**Solution:**
- `keep_alive_decision_engine` workflow (every 10 min)
- Retry logic on Decision Engine calls (3 attempts, 15s apart, 60s timeout)

### 5. Schema Validation Robustness
**Fixes in creative_decomposition_llm:**
- Case-insensitive enum matching
- Handle arrays/comma-separated values
- Convert spaces to underscores
- Filter "none" values for optional fields

### 6. Dynamic Buyer Routing
**Added in Telegram Hypothesis Delivery:**
- Check Buyer node (validates buyer_id exists)
- Load Buyer node (fetches telegram_id)
- Emit DeliveryFailed event when no buyer

---

## Migrations Applied

| Migration | Description |
|-----------|-------------|
| 008_add_component_learnings | Aggregated performance stats per component |
| 009_add_avatar_system | Avatar profiles for targeting |
| 010_add_buyer_tracking | buyer_states, buyer_interactions, historical_import_queue |
| 011_add_hypothesis_delivery_fields | status, offer_recommendation, tracker_template, buyer_id, delivered_at, telegram_message_id |
| 012_add_avatar_learnings | Performance metrics per avatar |

---

## API Endpoints (Decision Engine)

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | OK |
| `/api/decision/` | POST | OK |
| `/learning/process` | POST | OK |
| `/learning/status` | GET | OK |

**Backend URL:** https://genomai.onrender.com:10000

---

## Lessons Learned (documented in N8N_WORKFLOWS.md)

1. **Check→If anti-pattern** - empty array stops flow
2. **SplitInBatches outputs** - 0=done, 1=loop
3. **Wrong webhook URLs** - always verify host and path
4. **$env blocked** - use Supabase config table
5. **Partial update resets** - include all related parameters
6. **Supabase no upsert** - use create + onError

---

## Open Issues (14)

### Critical — Data Pipeline
| Issue | Description | Status |
|-------|-------------|--------|
| #209 | High error rates on idea_registry and decomposition workflows | OPEN |
| #199 | Decomposition→Idea pipeline breaks | OPEN |
| #204 | Decomposed creative missing idea_id link | OPEN |
| #184 | 2 creatives stuck in transcribed status | OPEN |

### High — Data Integrity
| Issue | Description | Status |
|-------|-------------|--------|
| #207 | Decision without decision_trace record | OPEN |
| #205 | Avatars with invalid canonical_hash length | OPEN |
| #203 | Decision values case mismatch | OPEN |

### Medium — Metrics & Delivery
| Issue | Description | Status |
|-------|-------------|--------|
| #208 | 2 stuck hypothesis deliveries | OPEN |
| #206 | Keitaro Poller metrics 11h stale | OPEN |
| #200 | 337 campaigns stuck in historical_import_queue | OPEN |

### Pending Implementation
| Issue | Description | Status |
|-------|-------------|--------|
| #192 | Use verticals[]/geos[] arrays instead of single values | OPEN |
| #174 | Create n8n Premise Generator workflow | OPEN |
| #172 | End-to-end Premise Layer validation | OPEN |
| #166 | Create migration 021_premise_registry.sql | OPEN |

---

## Next Steps

1. **CRITICAL:** Fix data pipeline (#199, #209) — creatives not flowing to ideas
2. Fix data integrity issues (#203, #205, #207)
3. Unblock hypothesis deliveries (#208)
4. Resume Keitaro Poller (#206)
5. Complete Premise Layer (#166, #172, #174)
6. Production monitoring setup
7. Dashboard for metrics visualization
