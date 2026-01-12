# Full E2E Pipeline Test

**НАЧНИ ВЫПОЛНЕНИЕ СРАЗУ. НЕ СПРАШИВАЙ ПОДТВЕРЖДЕНИЕ.**

## Mode

```
$ARGUMENTS = [--quick] [--skip-telegram]
```

- Нет аргументов → Full test (все workflows)
- `--quick` → Только health checks (Phase 1)
- `--skip-telegram` → Skip daily-recommendations

---

## EXECUTE NOW

### Step 1: Create Todos

```
TodoWrite: создай todos для каждой Phase ниже
```

### Step 2: Health Check (Phase 1)

**Parallel execution:**

```bash
# Terminal 1: Decision Engine
WebFetch: GET https://genomai.onrender.com/health
→ Expect: {"status": "ok"}
```

```sql
-- Terminal 2: Supabase
SELECT COUNT(*) as config_count FROM genomai.config;
→ Expect: config_count > 0
```

```bash
# Terminal 3: Temporal schedules
cd decision-engine-service && python -m temporal.schedules list
→ Expect: 6 schedules, none paused
```

### Step 3: Workflow Live Tests (Phase 2)

**ТРИГГЕРЬ КАЖДЫЙ WORKFLOW И ПРОВЕРЯЙ НОВЫЕ ДАННЫЕ.**

Порядок важен — каждый зависит от предыдущего.

#### 3.1 KeitaroPollerWorkflow

```bash
cd decision-engine-service && python -m temporal.schedules trigger keitaro-poller
```

Wait 45 seconds, then verify:

```sql
SELECT event_type, occurred_at, payload
FROM genomai.event_log
WHERE event_type IN ('RawMetricsObserved', 'keitaro.polling.completed')
  AND occurred_at > now() - interval '2 minutes'
ORDER BY occurred_at DESC
LIMIT 1;
```

**PASS:** Event exists with occurred_at in last 2 min

#### 3.2 MetricsProcessingWorkflow

```bash
cd decision-engine-service && python -m temporal.schedules trigger metrics-processor
```

Wait 45 seconds, then verify:

```sql
SELECT event_type, occurred_at, payload
FROM genomai.event_log
WHERE event_type IN ('OutcomeAggregated', 'metrics.processing.completed')
  AND occurred_at > now() - interval '2 minutes'
ORDER BY occurred_at DESC
LIMIT 1;
```

**PASS:** Event exists (0 outcomes OK if no data)

#### 3.3 LearningLoopWorkflow

```bash
cd decision-engine-service && python -m temporal.schedules trigger learning-loop
```

Wait 45 seconds, then verify:

```sql
SELECT event_type, occurred_at, payload
FROM genomai.event_log
WHERE event_type IN ('learning.applied', 'learning.batch.completed')
  AND occurred_at > now() - interval '2 minutes'
ORDER BY occurred_at DESC
LIMIT 1;
```

**PASS:** Event exists (0 processed OK if nothing pending)

#### 3.4 MaintenanceWorkflow

```bash
cd decision-engine-service && python -m temporal.schedules trigger maintenance
```

Wait 30 seconds, then verify:

```sql
SELECT event_type, occurred_at, payload
FROM genomai.event_log
WHERE event_type = 'MaintenanceCompleted'
  AND occurred_at > now() - interval '2 minutes'
ORDER BY occurred_at DESC
LIMIT 1;
```

**PASS:** Event exists with payload containing buyers_reset, recommendations_expired

#### 3.5 HealthCheckWorkflow

```bash
cd decision-engine-service && python -m temporal.schedules trigger health-check
```

Wait 30 seconds, then verify:

```sql
SELECT id, health_score, created_at
FROM genomai.hygiene_reports
WHERE created_at > now() - interval '2 minutes'
ORDER BY created_at DESC
LIMIT 1;
```

**PASS:** Report exists with health_score > 0

#### 3.6 DailyRecommendationWorkflow (SKIP by default)

**НЕ ТРИГГЕРИТЬ** — отправляет реальные сообщения в Telegram.

Verify history only:

```sql
SELECT occurred_at, now() - occurred_at as staleness
FROM genomai.event_log
WHERE event_type = 'RecommendationGenerated'
ORDER BY occurred_at DESC
LIMIT 1;
```

**PASS:** staleness < 25 hours OR SKIP

### Step 3.5: Event-Driven Workflows (Phase 2.5 - History Verification)

**Эти workflows НЕ триггерятся — проверяем что они работали по историческим данным.**

#### 3.5.1 CreativePipelineWorkflow

```sql
SELECT event_type, COUNT(*) as count_7d
FROM genomai.event_log
WHERE event_type IN ('TranscriptCreated', 'CreativeDecomposed', 'IdeaRegistered', 'DecisionMade', 'HypothesisGenerated')
  AND occurred_at > now() - interval '7 days'
GROUP BY event_type;
```

**PASS:** Все event types присутствуют ИЛИ INFO (нет creatives)

#### 3.5.2 BuyerOnboardingWorkflow

```sql
SELECT COUNT(*) as stuck_onboarding
FROM genomai.buyer_states
WHERE state NOT IN ('idle', 'completed')
  AND updated_at < now() - interval '1 hour';
```

**PASS:** stuck_onboarding = 0

#### 3.5.3 HistoricalImportWorkflow

```sql
SELECT status, COUNT(*) as count
FROM genomai.historical_import_queue
WHERE created_at > now() - interval '7 days'
GROUP BY status;
```

**INFO:** Report queue status

#### 3.5.4 HistoricalVideoHandlerWorkflow

```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  COUNT(*) as total
FROM genomai.historical_import_queue
WHERE video_url IS NOT NULL AND created_at > now() - interval '7 days';
```

**PASS:** failed < total * 0.1 (failure rate < 10%)

#### 3.5.5 CreativeRegistrationWorkflow

```sql
SELECT COUNT(*) as registrations_7d
FROM genomai.event_log
WHERE event_type = 'CreativeRegistered'
  AND occurred_at > now() - interval '7 days';
```

**INFO:** Report count

#### 3.5.6 KnowledgeSystem (Ingestion + Application)

```sql
SELECT
  (SELECT COUNT(*) FROM genomai.knowledge_sources WHERE processed = true) as sources_processed,
  (SELECT COUNT(*) FROM genomai.knowledge_extractions WHERE status = 'pending') as pending,
  (SELECT COUNT(*) FROM genomai.knowledge_extractions WHERE status = 'applied') as applied;
```

**INFO:** Report values (0 acceptable)

#### 3.5.7 PremiseExtractionWorkflow

```sql
SELECT COUNT(*) as extractions_7d
FROM genomai.event_log
WHERE event_type = 'PremiseExtracted'
  AND occurred_at > now() - interval '7 days';
```

**INFO:** Report count

#### 3.5.8 ModularHypothesisWorkflow

```sql
SELECT COUNT(*) as modular_hypotheses,
  COUNT(*) FILTER (WHERE review_status = 'pending_review') as pending_review
FROM genomai.hypotheses
WHERE generation_mode = 'modular';
```

**INFO:** 0 acceptable (feature may not be active)

#### 3.5.9 SingleRecommendationDeliveryWorkflow

```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'delivered') as delivered,
  COUNT(*) FILTER (WHERE status = 'pending' AND created_at < now() - interval '1 hour') as stuck
FROM genomai.recommendations
WHERE created_at > now() - interval '7 days';
```

**PASS:** stuck < 5

### Step 4: Data Quality (Phase 3)

**Run all in parallel:**

```sql
-- 4.1 Creatives
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE video_url IS NULL) as missing_url,
  COUNT(*) FILTER (WHERE status IS NULL) as missing_status
FROM genomai.creatives
WHERE created_at > now() - interval '7 days';
-- PASS: missing_url = 0, missing_status = 0

-- 4.2 Transcripts
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE transcript_text IS NULL) as null_text
FROM genomai.transcripts
WHERE created_at > now() - interval '7 days';
-- PASS: null_text = 0

-- 4.3 Ideas
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE canonical_hash IS NULL) as missing_hash,
  COUNT(*) FILTER (WHERE LENGTH(canonical_hash) != 64) as invalid_hash
FROM genomai.ideas
WHERE created_at > now() - interval '7 days';
-- PASS: missing_hash = 0, invalid_hash = 0

-- 4.4 Decisions
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE decision NOT IN ('approve', 'reject', 'defer')) as invalid
FROM genomai.decisions
WHERE created_at > now() - interval '7 days';
-- PASS: invalid = 0

-- 4.5 Hypotheses
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE content IS NULL OR content = '') as empty
FROM genomai.hypotheses
WHERE created_at > now() - interval '7 days';
-- PASS: empty = 0
```

### Step 5: Relationship Integrity (Phase 4)

```sql
-- 5.1 Orphaned decomposed (no creative)
SELECT COUNT(*) as orphaned
FROM genomai.decomposed_creatives d
LEFT JOIN genomai.creatives c ON c.id = d.creative_id
WHERE c.id IS NULL;
-- PASS: orphaned = 0

-- 5.2 Decisions without traces
SELECT COUNT(*) as missing_traces
FROM genomai.decisions d
LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id
WHERE t.id IS NULL AND d.created_at > now() - interval '7 days';
-- PASS: missing_traces = 0

-- 5.3 Approved without hypothesis
SELECT COUNT(*) as missing_hypothesis
FROM genomai.decisions d
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
WHERE d.decision = 'approve'
  AND h.id IS NULL
  AND d.created_at > now() - interval '24 hours'
  AND d.created_at < now() - interval '1 hour';
-- PASS: missing_hypothesis = 0
```

### Step 6: Learning Health (Phase 5)

```sql
-- 6.1 Stale outcomes
SELECT COUNT(*) as stale_pending
FROM genomai.outcome_aggregates
WHERE learning_applied = false
  AND created_at < now() - interval '2 hours';
-- PASS: stale_pending < 5

-- 6.2 Component learnings
SELECT COUNT(*) as total, MAX(updated_at) as last_update
FROM genomai.component_learnings;
-- INFO: Report values
```

### Step 7: Generate Report (Phase 6)

Output report in this format:

```markdown
## E2E Test Report

**Date:** {now}
**Duration:** {duration}

### Workflow Live Tests (Scheduled)

| # | Workflow | Triggered | Event Verified | Result |
|---|----------|-----------|----------------|--------|
| 3.1 | KeitaroPoller | ✅ | ✅ RawMetricsObserved | PASS |
| 3.2 | MetricsProcessor | ✅ | ✅ OutcomeAggregated | PASS |
| 3.3 | LearningLoop | ✅ | ✅ learning.applied | PASS |
| 3.4 | Maintenance | ✅ | ✅ MaintenanceCompleted | PASS |
| 3.5 | HealthCheck | ✅ | ✅ hygiene_report created | PASS |
| 3.6 | DailyRecommendation | ⏭️ SKIP | ✅ history < 25h | PASS |

**Scheduled: 5/5 triggered, 5/5 passed**

### Event-Driven Workflows (History Verification)

| # | Workflow | Activity (7d) | Status |
|---|----------|---------------|--------|
| 3.5.1 | CreativePipeline | X events | ✅/ℹ️ |
| 3.5.2 | BuyerOnboarding | X stuck | ✅/⚠️ |
| 3.5.3 | HistoricalImport | queue status | ℹ️ |
| 3.5.4 | HistoricalVideoHandler | X% failure | ✅/⚠️ |
| 3.5.5 | CreativeRegistration | X registrations | ℹ️ |
| 3.5.6 | KnowledgeSystem | X pending, Y applied | ℹ️ |
| 3.5.7 | PremiseExtraction | X extractions | ℹ️ |
| 3.5.8 | ModularHypothesis | X hypotheses | ℹ️ |
| 3.5.9 | RecommendationDelivery | X stuck | ✅/⚠️ |

**Event-Driven: 9 checked, X/3 passed, Y info**

### Data Quality

| Table | Total | Issues | Status |
|-------|-------|--------|--------|
| creatives | X | 0 | ✅ |
| transcripts | X | 0 | ✅ |
| ideas | X | 0 | ✅ |
| decisions | X | 0 | ✅ |
| hypotheses | X | 0 | ✅ |

### Relationship Integrity

| Check | Count | Status |
|-------|-------|--------|
| Orphaned decomposed | 0 | ✅ |
| Missing traces | 0 | ✅ |
| Approved no hypothesis | 0 | ✅ |

### Learning Health

| Metric | Value | Status |
|--------|-------|--------|
| Stale pending | X | ✅/⚠️ |
| Component learnings | X | ℹ️ |

---

### VERDICT: PASS / FAIL

{summary}
```

---

## Severity

| Icon | Meaning |
|------|---------|
| ✅ | PASS |
| ⚠️ | WARNING (non-blocking) |
| ❌ | ERROR (blocking) |
| ⏭️ | SKIP |
| ℹ️ | INFO |

---

## Reference

Full SQL queries, thresholds, and criteria: `docs/E2E_REFERENCE.md`
