# E2E Test Reference

Полная документация для `/e2e` скилла. Thresholds, SQL запросы, критерии.

## Workflows

### Scheduled (Triggered in E2E)

| Schedule ID | Workflow | Queue | Interval | Event Type |
|-------------|----------|-------|----------|------------|
| `keitaro-poller` | KeitaroPollerWorkflow | metrics | 10 min | `RawMetricsObserved` |
| `metrics-processor` | MetricsProcessingWorkflow | metrics | 30 min | `OutcomeAggregated` |
| `learning-loop` | LearningLoopWorkflow | metrics | 1 hour | `learning.applied` |
| `maintenance` | MaintenanceWorkflow | metrics | 6 hours | `MaintenanceCompleted` |
| `health-check` | HealthCheckWorkflow | metrics | 3 hours | hygiene_reports record |
| `daily-recommendations` | DailyRecommendationWorkflow | metrics | Daily 09:00 | `RecommendationGenerated` |

### Event-Driven (History Verification)

| Workflow | Queue | Trigger | Event Type | Verification Table |
|----------|-------|---------|------------|-------------------|
| CreativePipelineWorkflow | creative-pipeline | webhook | multiple | creatives, transcripts, ideas |
| ModularHypothesisWorkflow | creative-pipeline | programmatic | none | hypotheses (generation_mode='modular') |
| BuyerOnboardingWorkflow | telegram | /start | none | buyers |
| HistoricalImportWorkflow | telegram | post-onboard | none | historical_import_queue |
| CreativeRegistrationWorkflow | telegram | video URL | `CreativeRegistered` | creatives |
| HistoricalVideoHandlerWorkflow | telegram | API | `HistoricalCreativeRegistered` | historical_import_queue |
| KnowledgeIngestionWorkflow | knowledge | API/file | none | knowledge_sources, knowledge_extractions |
| KnowledgeApplicationWorkflow | knowledge | approval | none | knowledge_extractions (status) |
| PremiseExtractionWorkflow | knowledge | programmatic | `PremiseExtracted` | premises, premise_learnings |
| BatchPremiseExtractionWorkflow | knowledge | programmatic | `PremiseExtracted` | same as above |
| SingleRecommendationDeliveryWorkflow | metrics | programmatic | `RecommendationDelivered` | recommendations |

## Thresholds

| Metric | OK | WARNING | ERROR |
|--------|-----|---------|-------|
| Data quality rate | < 1% | 1-5% | > 5% |
| SLA breach rate | < 10% | 10-20% | > 20% |
| Schedule staleness | within interval | 2x interval | > 3x |
| Stuck items | 0 | 1-5 | > 5 |
| Orphaned records | < 5 | 5-20 | > 20 |
| Learning applied rate | > 90% | 70-90% | < 70% |
| Stale pending outcomes | 0 | 1-5 | > 5 |
| Keitaro metrics staleness | < 25h | 25-48h | > 48h |

## Extended SQL Queries

### Data Quality - Creatives

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE video_url IS NULL OR video_url = '') as missing_url,
  COUNT(*) FILTER (WHERE status IS NULL) as missing_status,
  COUNT(*) FILTER (WHERE source_type NOT IN ('user', 'hypothesis', 'recommendation', 'historical', 'spy')) as invalid_source_type,
  COUNT(*) FILTER (WHERE created_at > now()) as future_dates
FROM genomai.creatives
WHERE created_at > now() - interval '7 days';
```

### Data Quality - Transcripts

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE transcript_text IS NULL) as null_text,
  COUNT(*) FILTER (WHERE LENGTH(transcript_text) < 50) as too_short,
  COUNT(*) FILTER (WHERE transcript_text LIKE '%[%]%' OR transcript_text LIKE '%TODO%') as placeholder_text,
  AVG(LENGTH(transcript_text)) as avg_length
FROM genomai.transcripts
WHERE created_at > now() - interval '7 days';
```

### Data Quality - Decomposed Creatives

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE payload IS NULL) as null_payload,
  COUNT(*) FILTER (WHERE idea_id IS NULL) as missing_idea_link,
  COUNT(*) FILTER (WHERE schema_version IS NULL) as missing_schema_version,
  COUNT(*) FILTER (WHERE jsonb_typeof(payload) != 'object') as invalid_payload_type
FROM genomai.decomposed_creatives
WHERE created_at > now() - interval '7 days';
```

### Data Quality - Ideas

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE canonical_hash IS NULL) as missing_hash,
  COUNT(*) FILTER (WHERE LENGTH(canonical_hash) != 64) as invalid_hash_length,
  COUNT(*) FILTER (WHERE death_state NOT IN ('soft_dead', 'hard_dead', 'permanent_dead') AND death_state IS NOT NULL) as invalid_death_state
FROM genomai.ideas
WHERE created_at > now() - interval '7 days';
```

### Data Quality - Decisions

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE decision NOT IN ('approve', 'reject', 'defer')) as invalid_decision,
  COUNT(*) FILTER (WHERE idea_id IS NULL) as missing_idea,
  COUNT(*) FILTER (WHERE decision_epoch IS NULL OR decision_epoch < 1) as invalid_epoch
FROM genomai.decisions
WHERE created_at > now() - interval '7 days';
```

### Data Quality - Hypotheses

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE content IS NULL OR content = '') as empty_content,
  COUNT(*) FILTER (WHERE LENGTH(content) < 100) as too_short,
  COUNT(*) FILTER (WHERE status NOT IN ('pending', 'ready_for_launch', 'delivered', 'failed')) as invalid_status,
  COUNT(*) FILTER (WHERE status = 'delivered' AND delivered_at IS NULL) as delivered_no_timestamp
FROM genomai.hypotheses
WHERE created_at > now() - interval '7 days';
```

### Learning Loop Health

```sql
-- Outcomes processing
SELECT
  COUNT(*) as total_outcomes,
  COUNT(*) FILTER (WHERE learning_applied = true) as learning_applied,
  COUNT(*) FILTER (WHERE learning_applied = false OR learning_applied IS NULL) as pending_learning,
  COUNT(*) FILTER (WHERE learning_applied = false AND created_at < now() - interval '1 hour') as stale_pending
FROM genomai.outcome_aggregates
WHERE created_at > now() - interval '7 days';

-- Component learnings
SELECT
  COUNT(*) as total_components,
  COUNT(*) FILTER (WHERE sample_size > 0) as with_samples,
  MAX(updated_at) as last_update,
  now() - MAX(updated_at) as staleness,
  SUM(sample_size) as total_samples,
  AVG(win_rate) as avg_win_rate
FROM genomai.component_learnings;
```

### Relationship Integrity

```sql
-- Orphaned decomposed (no creative)
SELECT d.id, d.creative_id, d.created_at
FROM genomai.decomposed_creatives d
LEFT JOIN genomai.creatives c ON c.id = d.creative_id
WHERE c.id IS NULL
LIMIT 10;

-- Decisions without traces
SELECT d.id, d.decision, d.created_at
FROM genomai.decisions d
LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id
WHERE t.id IS NULL
  AND d.created_at > now() - interval '7 days'
LIMIT 10;

-- Approved without hypothesis
SELECT d.id, d.idea_id, d.created_at
FROM genomai.decisions d
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
WHERE d.decision = 'approve'
  AND h.id IS NULL
  AND d.created_at > now() - interval '24 hours'
  AND d.created_at < now() - interval '1 hour'
LIMIT 10;

-- Broken creative chain (transcript but no decomposed)
SELECT c.id, c.tracker_id, c.status, t.created_at as transcript_at
FROM genomai.creatives c
JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = c.id
WHERE d.id IS NULL
  AND t.created_at < now() - interval '30 minutes'
LIMIT 10;
```

### SLA Monitoring

```sql
WITH pipeline_times AS (
  SELECT
    c.id as creative_id,
    c.created_at as creative_at,
    t.created_at as transcript_at,
    d.created_at as decomposed_at,
    dec.created_at as decision_at,
    h.created_at as hypothesis_at,
    h.delivered_at as delivered_at
  FROM genomai.creatives c
  LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
  LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = c.id
  LEFT JOIN genomai.decisions dec ON dec.idea_id = d.idea_id
  LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
  WHERE c.created_at > now() - interval '24 hours'
)
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE transcript_at - creative_at > interval '3 minutes') as transcription_sla_breach,
  AVG(EXTRACT(EPOCH FROM (transcript_at - creative_at))) as avg_transcription_sec,
  COUNT(*) FILTER (WHERE decomposed_at - transcript_at > interval '2 minutes') as decomposition_sla_breach,
  COUNT(*) FILTER (WHERE decision_at - decomposed_at > interval '1 minute') as decision_sla_breach,
  COUNT(*) FILTER (WHERE delivered_at - creative_at > interval '10 minutes') as full_pipeline_sla_breach
FROM pipeline_times
WHERE transcript_at IS NOT NULL;
```

### Stuck Items

```sql
SELECT
  (SELECT COUNT(*) FROM genomai.creatives c
   LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
   WHERE t.id IS NULL
     AND c.created_at < now() - interval '5 minutes'
     AND c.created_at > now() - interval '24 hours') as stuck_transcription,

  (SELECT COUNT(*) FROM genomai.transcripts t
   LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = t.creative_id
   WHERE d.id IS NULL
     AND t.created_at < now() - interval '5 minutes'
     AND t.created_at > now() - interval '24 hours') as stuck_decomposition,

  (SELECT COUNT(*) FROM genomai.decomposed_creatives d
   LEFT JOIN genomai.decisions dec ON dec.idea_id = d.idea_id
   WHERE dec.id IS NULL
     AND d.idea_id IS NOT NULL
     AND d.created_at < now() - interval '5 minutes'
     AND d.created_at > now() - interval '24 hours') as stuck_decision,

  (SELECT COUNT(*) FROM genomai.decisions d
   LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
   WHERE d.decision = 'approve'
     AND h.id IS NULL
     AND d.created_at < now() - interval '5 minutes'
     AND d.created_at > now() - interval '24 hours') as stuck_hypothesis,

  (SELECT COUNT(*) FROM genomai.hypotheses h
   WHERE h.status NOT IN ('delivered', 'failed')
     AND h.created_at < now() - interval '5 minutes'
     AND h.created_at > now() - interval '24 hours') as stuck_delivery;
```

### Integration Health

```sql
-- Keitaro metrics freshness
SELECT
  COUNT(*) as total_trackers,
  MAX(updated_at) as last_update,
  now() - MAX(updated_at) as staleness,
  COUNT(*) FILTER (WHERE updated_at > now() - interval '1 hour') as fresh_count,
  COUNT(*) FILTER (WHERE updated_at < now() - interval '24 hours') as stale_count
FROM genomai.raw_metrics_current;

-- Keitaro config
SELECT
  COUNT(*) as total_configs,
  COUNT(*) FILTER (WHERE is_active = true) as active_configs
FROM genomai.keitaro_config;

-- Daily snapshots
SELECT
  COUNT(*) as total_snapshots,
  MAX(date) as last_snapshot_date,
  current_date - MAX(date) as days_since_last
FROM genomai.daily_metrics_snapshot;
```

### Auxiliary Tables

```sql
-- Buyers
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE telegram_id IS NULL) as missing_telegram,
  COUNT(*) FILTER (WHERE name IS NULL OR name = '') as missing_name
FROM genomai.buyers;

-- Historical import queue
SELECT COUNT(*) as stuck_pending_video
FROM genomai.historical_import_queue
WHERE status = 'pending_video'
  AND created_at < now() - interval '7 days';

-- Expired recommendations
SELECT COUNT(*) as expired_pending
FROM genomai.recommendations
WHERE status = 'pending'
  AND expires_at < now();
```

### Regression Checks

```sql
-- Orphan ideas
SELECT COUNT(*) as orphan_ideas
FROM genomai.ideas i
LEFT JOIN genomai.decomposed_creatives d ON d.idea_id = i.id
WHERE d.id IS NULL
  AND i.created_at > now() - interval '7 days';

-- Missing decision traces (all time)
SELECT COUNT(*) as decisions_without_traces
FROM genomai.decisions d
LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id
WHERE t.id IS NULL;

-- Duplicate decisions
SELECT idea_id, COUNT(*) as decision_count
FROM genomai.decisions
GROUP BY idea_id
HAVING COUNT(*) > 3
ORDER BY decision_count DESC
LIMIT 10;

-- Failed deliveries not retried
SELECT COUNT(*) as failed_not_retried
FROM genomai.hypotheses
WHERE status = 'failed'
  AND created_at < now() - interval '1 hour'
  AND created_at > now() - interval '24 hours';

-- Event log coverage
SELECT
  event_type,
  COUNT(*) as count_24h,
  MAX(occurred_at) as last_event
FROM genomai.event_log
WHERE occurred_at > now() - interval '24 hours'
GROUP BY event_type
ORDER BY count_24h DESC;
```

## Schedule Staleness Matrix

| Schedule | Interval | OK | WARNING | ERROR |
|----------|----------|-----|---------|-------|
| keitaro-poller | 10 min | < 15 min | 15-30 min | > 30 min |
| metrics-processor | 30 min | < 45 min | 45-90 min | > 90 min |
| learning-loop | 1 hour | < 2 hours | 2-4 hours | > 4 hours |
| maintenance | 6 hours | < 8 hours | 8-12 hours | > 12 hours |
| health-check | 3 hours | < 4 hours | 4-6 hours | > 6 hours |
| daily-recommendations | Daily | < 25 hours | 25-48 hours | > 48 hours |

## Event-Driven Workflows SQL

### CreativePipelineWorkflow

```sql
-- Verify pipeline events exist
SELECT event_type, COUNT(*) as count_7d
FROM genomai.event_log
WHERE event_type IN ('TranscriptCreated', 'CreativeDecomposed', 'IdeaRegistered', 'DecisionMade', 'HypothesisGenerated')
  AND occurred_at > now() - interval '7 days'
GROUP BY event_type;
-- PASS: All event types present OR INFO (no creatives)
```

### HistoricalImportWorkflow

```sql
-- Import queue status distribution
SELECT status, COUNT(*) as count
FROM genomai.historical_import_queue
WHERE created_at > now() - interval '7 days'
GROUP BY status;
-- INFO: Report queue status
```

### HistoricalVideoHandlerWorkflow

```sql
-- Check failure rate
SELECT
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  COUNT(*) as total
FROM genomai.historical_import_queue
WHERE video_url IS NOT NULL AND created_at > now() - interval '7 days';
-- PASS: failed < total * 0.1 (failure rate < 10%)
```

### CreativeRegistrationWorkflow

```sql
-- Check CreativeRegistered events
SELECT COUNT(*) as registrations_7d
FROM genomai.event_log
WHERE event_type = 'CreativeRegistered'
  AND occurred_at > now() - interval '7 days';
-- INFO: Report count
```

### KnowledgeSystem (Ingestion + Application)

```sql
-- Knowledge system state
SELECT
  (SELECT COUNT(*) FROM genomai.knowledge_sources WHERE processed = true) as sources_processed,
  (SELECT COUNT(*) FROM genomai.knowledge_extractions WHERE status = 'pending') as pending,
  (SELECT COUNT(*) FROM genomai.knowledge_extractions WHERE status = 'applied') as applied;
-- INFO: Report values (0 acceptable)
```

### PremiseExtractionWorkflow

```sql
-- Check PremiseExtracted events
SELECT COUNT(*) as extractions_7d
FROM genomai.event_log
WHERE event_type = 'PremiseExtracted'
  AND occurred_at > now() - interval '7 days';
-- INFO: Report count
```

### ModularHypothesisWorkflow

```sql
-- Check modular hypotheses
SELECT COUNT(*) as modular_hypotheses,
  COUNT(*) FILTER (WHERE review_status = 'pending_review') as pending_review
FROM genomai.hypotheses
WHERE generation_mode = 'modular';
-- INFO: 0 acceptable (feature may not be active)
```

### SingleRecommendationDeliveryWorkflow

```sql
-- Check stuck recommendations
SELECT
  COUNT(*) FILTER (WHERE status = 'delivered') as delivered,
  COUNT(*) FILTER (WHERE status = 'pending' AND created_at < now() - interval '1 hour') as stuck
FROM genomai.recommendations
WHERE created_at > now() - interval '7 days';
-- PASS: stuck < 5
```

## Event Types

Expected events in event_log:

### Scheduled Workflows

| Event Type | Source | Description |
|------------|--------|-------------|
| `RawMetricsObserved` | KeitaroPollerWorkflow | Metrics collected |
| `OutcomeAggregated` | MetricsProcessingWorkflow | Outcome created |
| `learning.applied` | LearningLoopWorkflow | Learning processed |
| `MaintenanceCompleted` | MaintenanceWorkflow | Maintenance done |
| `RecommendationGenerated` | DailyRecommendationWorkflow | Recommendation sent |

### Event-Driven Workflows

| Event Type | Source | Description |
|------------|--------|-------------|
| `CreativeRegistered` | CreativeRegistrationWorkflow | New creative from Telegram |
| `TranscriptCreated` | CreativePipelineWorkflow | Transcription completed |
| `CreativeDecomposed` | CreativePipelineWorkflow | LLM decomposition done |
| `IdeaRegistered` | CreativePipelineWorkflow | Idea created/linked |
| `DecisionMade` | Decision Engine | Decision rendered |
| `HypothesisGenerated` | CreativePipelineWorkflow | Hypothesis created |
| `HypothesisDelivered` | CreativePipelineWorkflow | Telegram delivery success |
| `DeliveryFailed` | CreativePipelineWorkflow | Telegram delivery failed |
| `HistoricalCreativeRegistered` | HistoricalVideoHandlerWorkflow | Historical creative created |
| `PremiseExtracted` | PremiseExtractionWorkflow | Premises extracted from creative |
| `RecommendationDelivered` | SingleRecommendationDeliveryWorkflow | Individual recommendation sent |
