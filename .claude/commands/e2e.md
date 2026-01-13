# Full E2E Pipeline Test

**НАЧНИ ВЫПОЛНЕНИЕ СРАЗУ. НЕ СПРАШИВАЙ ПОДТВЕРЖДЕНИЕ.**

## Mode

```
$ARGUMENTS = [--prod] [--quick] [--skip-telegram] [--security] [--contracts] [--chaos] [--db] [--functional] [--decision] [--learning] [--buyer] [--workflows]
```

### Environment
- **По умолчанию → LOCAL** (localhost:10000) — для разработки
- `--prod` → PRODUCTION (genomai.onrender.com) — после деплоя

### Phase Selection
- Нет аргументов → Full test (все 14 фаз, 42 проверки)
- `--quick` → Только Phase 1: Health Checks
- `--skip-telegram` → Skip DailyRecommendation trigger
- `--security` → Только Phase 7: Security Testing
- `--contracts` → Только Phase 6: API Contract Testing
- `--chaos` → Только Phase 9-10: Chaos + Concurrency Testing
- `--db` → Только Phase 8: DB Constraints Testing
- `--functional` → Phase 11-13: Decision Engine + Learning Loop + Buyer
- `--decision` → Только Phase 11: Decision Engine Logic
- `--learning` → Только Phase 12: Learning Loop Logic
- `--buyer` → Только Phase 13: Buyer Interactions
- `--workflows` → Только Phase 2-2.5: Workflow Tests

---

## EXECUTION INSTRUCTIONS

### Environment URLs

```
LOCAL (default):
  API_BASE = http://localhost:10000
  Temporal = localhost (docker)

PRODUCTION (--prod):
  API_BASE = https://genomai.onrender.com
  Temporal = Temporal Cloud
```

### ВАЖНО: Как выполнять запросы

**SQL запросы через MCP Supabase:**
```
Используй mcp__supabase__sqlToRest для конвертации SQL в REST
Затем mcp__supabase__postgrestRequest для выполнения
```

**HTTP запросы:**
```
LOCAL:  curl или WebFetch к http://localhost:10000
PROD:   WebFetch к https://genomai.onrender.com
```

**Temporal команды:**
```
Используй Bash в директории decision-engine-service
LOCAL:  python -m temporal.schedules list (docker temporal)
PROD:   добавь --cloud флаг если нужно
```

---

## PHASE 1: Health Checks

### 1.1 Decision Engine Health

**Выполни:**
```
WebFetch: GET {API_BASE}/health
Prompt: "Верни статус из JSON ответа"
```
**PASS:** status = "ok"

### 1.2 Supabase Connection

**Выполни:**
```
mcp__supabase__postgrestRequest:
  method: GET
  path: /config?select=count
```
**PASS:** Ответ без ошибки

### 1.3 Temporal Schedules

**Выполни в Bash:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules list
```
**PASS:** 6 schedules, none paused

---

## PHASE 2: Workflow Live Tests (SCHEDULED)

**Порядок важен — каждый workflow может зависеть от данных предыдущего.**

### 2.1 KeitaroPollerWorkflow

**Шаг 1 - Trigger:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules trigger keitaro-poller
```

**Шаг 2 - Wait:** 45 секунд

**Шаг 3 - Verify (SQL → REST):**
```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, occurred_at FROM genomai.event_log WHERE event_type IN ('RawMetricsObserved', 'keitaro.polling.completed') AND occurred_at > now() - interval '2 minutes' ORDER BY occurred_at DESC LIMIT 1"
```
**PASS:** Event exists с occurred_at в последние 2 минуты

### 2.2 MetricsProcessingWorkflow

**Шаг 1 - Trigger:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules trigger metrics-processor
```

**Шаг 2 - Wait:** 45 секунд

**Шаг 3 - Verify:**
```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, occurred_at FROM genomai.event_log WHERE event_type IN ('OutcomeAggregated', 'metrics.processing.completed') AND occurred_at > now() - interval '2 minutes' ORDER BY occurred_at DESC LIMIT 1"
```
**PASS:** Event exists (0 outcomes OK если нет данных)

### 2.3 LearningLoopWorkflow

**Шаг 1 - Trigger:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules trigger learning-loop
```

**Шаг 2 - Wait:** 45 секунд

**Шаг 3 - Verify:**
```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, occurred_at FROM genomai.event_log WHERE event_type IN ('learning.applied', 'learning.batch.completed') AND occurred_at > now() - interval '2 minutes' ORDER BY occurred_at DESC LIMIT 1"
```
**PASS:** Event exists (0 processed OK если ничего pending)

### 2.4 MaintenanceWorkflow

**Шаг 1 - Trigger:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules trigger maintenance
```

**Шаг 2 - Wait:** 30 секунд

**Шаг 3 - Verify:**
```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, occurred_at, payload FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted' AND occurred_at > now() - interval '2 minutes' ORDER BY occurred_at DESC LIMIT 1"
```
**PASS:** Event exists с payload

### 2.5 HealthCheckWorkflow

**Шаг 1 - Trigger:**
```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/decision-engine-service && python -m temporal.schedules trigger health-check
```

**Шаг 2 - Wait:** 30 секунд

**Шаг 3 - Verify:**
```
mcp__supabase__sqlToRest:
  sql: "SELECT id, health_score, created_at FROM genomai.hygiene_reports WHERE created_at > now() - interval '2 minutes' ORDER BY created_at DESC LIMIT 1"
```
**PASS:** Report exists с health_score > 0

### 2.6 DailyRecommendationWorkflow (SKIP by default)

**НЕ ТРИГГЕРИТЬ** — отправляет реальные сообщения в Telegram.

**Verify history only:**
```
mcp__supabase__sqlToRest:
  sql: "SELECT occurred_at FROM genomai.event_log WHERE event_type = 'RecommendationGenerated' ORDER BY occurred_at DESC LIMIT 1"
```
**PASS:** staleness < 25 hours OR SKIP

---

## PHASE 2.5: Event-Driven Workflows (History Verification)

**Эти workflows НЕ триггерятся — проверяем историю.**

### 2.5.1 CreativePipelineWorkflow

```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, COUNT(*) as count_7d FROM genomai.event_log WHERE event_type IN ('TranscriptCreated', 'CreativeDecomposed', 'IdeaRegistered', 'DecisionMade', 'HypothesisGenerated') AND occurred_at > now() - interval '7 days' GROUP BY event_type"
```
**PASS:** Все event types присутствуют ИЛИ INFO (нет creatives)

### 2.5.2 BuyerOnboardingWorkflow

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as stuck_onboarding FROM genomai.buyer_states WHERE state NOT IN ('idle', 'completed') AND updated_at < now() - interval '1 hour'"
```
**PASS:** stuck_onboarding = 0

### 2.5.3 HistoricalImportWorkflow

```
mcp__supabase__sqlToRest:
  sql: "SELECT status, COUNT(*) as count FROM genomai.historical_import_queue WHERE created_at > now() - interval '7 days' GROUP BY status"
```
**INFO:** Report queue status

### 2.5.4 RecommendationDeliveryWorkflow

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) FILTER (WHERE status = 'delivered') as delivered, COUNT(*) FILTER (WHERE status = 'pending' AND created_at < now() - interval '1 hour') as stuck FROM genomai.recommendations WHERE created_at > now() - interval '7 days'"
```
**PASS:** stuck < 5

---

## PHASE 3: Data Quality

**Выполни все запросы параллельно:**

### 3.1 Creatives Quality

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE video_url IS NULL) as missing_url, COUNT(*) FILTER (WHERE status IS NULL) as missing_status FROM genomai.creatives WHERE created_at > now() - interval '7 days'"
```
**PASS:** missing_url = 0, missing_status = 0

### 3.2 Ideas Quality

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE canonical_hash IS NULL) as missing_hash, COUNT(*) FILTER (WHERE LENGTH(canonical_hash) != 64) as invalid_hash FROM genomai.ideas WHERE created_at > now() - interval '7 days'"
```
**PASS:** missing_hash = 0, invalid_hash = 0

### 3.3 Decisions Quality

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE decision NOT IN ('approve', 'reject', 'defer')) as invalid FROM genomai.decisions WHERE created_at > now() - interval '7 days'"
```
**PASS:** invalid = 0

### 3.4 Hypotheses Quality

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE content IS NULL OR content = '') as empty FROM genomai.hypotheses WHERE created_at > now() - interval '7 days'"
```
**PASS:** empty = 0

---

## PHASE 4: Relationship Integrity

### 4.1 Orphaned Decomposed Creatives

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as orphaned FROM genomai.decomposed_creatives d LEFT JOIN genomai.creatives c ON c.id = d.creative_id WHERE c.id IS NULL"
```
**PASS:** orphaned = 0

### 4.2 Decisions Without Traces

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as missing_traces FROM genomai.decisions d LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id WHERE t.id IS NULL AND d.created_at > now() - interval '7 days'"
```
**PASS:** missing_traces = 0

### 4.3 Approved Without Hypothesis

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as missing_hypothesis FROM genomai.decisions d LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id WHERE d.decision = 'approve' AND h.id IS NULL AND d.created_at > now() - interval '24 hours' AND d.created_at < now() - interval '1 hour'"
```
**PASS:** missing_hypothesis = 0

---

## PHASE 5: Learning Health

### 5.1 Stale Outcomes

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as stale_pending FROM genomai.outcome_aggregates WHERE learning_applied = false AND created_at < now() - interval '2 hours'"
```
**PASS:** stale_pending < 5

### 5.2 Component Learnings Activity

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, MAX(updated_at) as last_update FROM genomai.component_learnings"
```
**INFO:** Report values

---

## PHASE 6: API Contract Testing

### 6.1 Health Endpoint (No Auth)

```
WebFetch:
  url: {API_BASE}/health
  prompt: "Верни полный JSON ответ"
```
**PASS:** status = "ok"

### 6.2 Metrics Health Endpoint

```
WebFetch:
  url: {API_BASE}/health/metrics
  prompt: "Верни is_stale и circuit_state из ответа"
```
**PASS:** Ответ без ошибки

### 6.3 Protected Endpoint Without Auth

```
WebFetch:
  url: {API_BASE}/api/decision/
  prompt: "Сделай POST запрос без Authorization header и верни HTTP статус код"
```
**PASS:** 401 OR 403

---

## PHASE 7: Security Testing

### 7.1 Auth Required Check

```
WebFetch:
  url: {API_BASE}/api/decision/
  prompt: "POST без auth header, какой статус код?"
```
**PASS:** 401 OR 403

### 7.2 Invalid Token Check

```
WebFetch:
  url: {API_BASE}/learning/status
  prompt: "GET с header Authorization: Bearer invalid-token-12345, какой статус?"
```
**PASS:** 401 OR 403

### 7.3 Secrets Not Exposed

```
WebFetch:
  url: {API_BASE}/health
  prompt: "Есть ли в ответе слова key, secret, password, token? Ответь да/нет"
```
**PASS:** Нет

---

## PHASE 8: DB Constraints Testing

### 8.1 Unique Constraint: decisions(idea_id, decision_epoch)

```
mcp__supabase__sqlToRest:
  sql: "SELECT idea_id, decision_epoch, COUNT(*) as cnt FROM genomai.decisions GROUP BY idea_id, decision_epoch HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

### 8.2 Foreign Key: decomposed → creatives

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as orphaned FROM genomai.decomposed_creatives d LEFT JOIN genomai.creatives c ON c.id = d.creative_id WHERE c.id IS NULL"
```
**PASS:** orphaned = 0

### 8.3 Foreign Key: decisions → ideas

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as orphaned FROM genomai.decisions d LEFT JOIN genomai.ideas i ON i.id = d.idea_id WHERE i.id IS NULL"
```
**PASS:** orphaned = 0

### 8.4 Hash Integrity

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as invalid FROM genomai.ideas WHERE canonical_hash IS NOT NULL AND LENGTH(canonical_hash) != 64"
```
**PASS:** invalid = 0

### 8.5 Valid Decision Enum

```
mcp__supabase__sqlToRest:
  sql: "SELECT decision, COUNT(*) as cnt FROM genomai.decisions GROUP BY decision"
```
**PASS:** Only 'approve', 'reject', 'defer' values

---

## PHASE 9: Chaos/Resilience Testing

### 9.1 Circuit Breaker Events

```
mcp__supabase__sqlToRest:
  sql: "SELECT event_type, COUNT(*) as count FROM genomai.event_log WHERE event_type LIKE '%circuit%' AND occurred_at > now() - interval '24 hours' GROUP BY event_type"
```
**INFO:** Report activity

### 9.2 Retry Exhausted Hypotheses

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as exhausted FROM genomai.hypotheses WHERE retry_count >= 3 AND status NOT IN ('delivered', 'failed')"
```
**PASS:** exhausted = 0

### 9.3 Stuck Workflows

```
mcp__supabase__sqlToRest:
  sql: "SELECT status, COUNT(*) as cnt FROM genomai.creatives WHERE status IN ('transcribing', 'decomposing', 'processing') AND updated_at < now() - interval '30 minutes' GROUP BY status"
```
**PASS:** Total stuck < 3

### 9.4 Unhandled Failures

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as unhandled FROM genomai.creatives WHERE status = 'failed' AND error_message IS NULL"
```
**PASS:** unhandled = 0

---

## PHASE 10: Concurrent Access Testing

### 10.1 Duplicate Ideas (Same Hash)

```
mcp__supabase__sqlToRest:
  sql: "SELECT canonical_hash, COUNT(*) as cnt FROM genomai.ideas WHERE canonical_hash IS NOT NULL GROUP BY canonical_hash HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

### 10.2 Duplicate Outcome Aggregates

```
mcp__supabase__sqlToRest:
  sql: "SELECT creative_id, window_start, COUNT(*) as cnt FROM genomai.outcome_aggregates GROUP BY creative_id, window_start HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

### 10.3 Learning Applied Multiple Times

```
mcp__supabase__sqlToRest:
  sql: "SELECT source_outcome_id, COUNT(*) as cnt FROM genomai.idea_confidence_versions WHERE source_outcome_id IS NOT NULL GROUP BY source_outcome_id HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

---

## PHASE 11: Decision Engine Logic

### 11.1 Decision Idempotency

```
mcp__supabase__sqlToRest:
  sql: "SELECT idea_id, decision_epoch, COUNT(*) as cnt FROM genomai.decisions GROUP BY idea_id, decision_epoch HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

### 11.2 Decision Trace Completeness

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as missing FROM genomai.decisions d LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id WHERE t.id IS NULL AND d.created_at > now() - interval '7 days'"
```
**PASS:** missing = 0

### 11.3 Hard Dead No Approves

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as violations FROM genomai.decisions d JOIN genomai.ideas i ON i.id = d.idea_id WHERE i.death_state = 'hard_dead' AND d.decision = 'approve'"
```
**PASS:** violations = 0

---

## PHASE 12: Learning Loop Logic

### 12.1 Confidence Bounds

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as out_of_bounds FROM genomai.idea_confidence_versions WHERE confidence_value < 0.0 OR confidence_value > 1.0"
```
**PASS:** out_of_bounds = 0

### 12.2 Learning Idempotency

```
mcp__supabase__sqlToRest:
  sql: "SELECT source_outcome_id, COUNT(*) as cnt FROM genomai.idea_confidence_versions WHERE source_outcome_id IS NOT NULL GROUP BY source_outcome_id HAVING COUNT(*) > 1"
```
**PASS:** Empty result (0 rows)

### 12.3 Outcome Processing

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as unprocessed FROM genomai.outcome_aggregates WHERE learning_applied = false AND created_at < now() - interval '4 hours'"
```
**PASS:** unprocessed < 10

---

## PHASE 13: Buyer Interactions

### 13.1 Buyer States Validity

```
mcp__supabase__sqlToRest:
  sql: "SELECT state, COUNT(*) as cnt FROM genomai.buyer_states GROUP BY state"
```
**INFO:** Valid states: idle, awaiting_name, awaiting_geo, awaiting_vertical, awaiting_keitaro, loading_history, awaiting_videos, completed, cancelled, timed_out

### 13.2 Stuck Onboarding

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as stuck FROM genomai.buyer_states WHERE state NOT IN ('idle', 'completed', 'cancelled', 'timed_out') AND updated_at < now() - interval '2 hours'"
```
**PASS:** stuck = 0

### 13.3 Buyer Data Completeness

```
mcp__supabase__sqlToRest:
  sql: "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE name IS NULL OR name = '') as missing_name FROM genomai.buyers WHERE status = 'active'"
```
**PASS:** missing_name = 0

---

## PHASE 14: Generate Report

**Сформируй отчёт в следующем формате:**

```markdown
## E2E Test Report

**Date:** {текущая дата и время}
**Duration:** {время выполнения}
**Mode:** {full|quick|skip-telegram|etc}

### Phase 1: Health Checks

| Component | Status | Details |
|-----------|--------|---------|
| Decision Engine | {status} | /health → {result} |
| Supabase | {status} | connection test |
| Temporal Schedules | {status} | {count} schedules |

### Phase 2: Workflow Live Tests

| Workflow | Triggered | Event Verified | Result |
|----------|-----------|----------------|--------|
| KeitaroPoller | {yes/no} | {event} | {PASS/FAIL} |
| MetricsProcessor | {yes/no} | {event} | {PASS/FAIL} |
| LearningLoop | {yes/no} | {event} | {PASS/FAIL} |
| Maintenance | {yes/no} | {event} | {PASS/FAIL} |
| HealthCheck | {yes/no} | {event} | {PASS/FAIL} |
| DailyRecommendation | SKIP | history check | {PASS/SKIP} |

### Phase 3-5: Data Quality & Integrity

| Check | Result | Status |
|-------|--------|--------|
| Creatives quality | {values} | {status} |
| Ideas quality | {values} | {status} |
| Decisions quality | {values} | {status} |
| Orphaned records | {count} | {status} |
| Learning health | {values} | {status} |

### Phase 6-7: API & Security

| Test | Result | Status |
|------|--------|--------|
| Health endpoint | {result} | {status} |
| Auth required | {result} | {status} |
| Invalid token | {result} | {status} |
| No secrets exposed | {result} | {status} |

### Phase 8-10: DB & Resilience

| Check | Issues | Status |
|-------|--------|--------|
| Unique constraints | {count} | {status} |
| Foreign keys | {count} | {status} |
| Circuit breaker | {info} | {status} |
| Stuck workflows | {count} | {status} |
| Concurrent access | {count} | {status} |

### Phase 11-13: Business Logic

| Check | Result | Status |
|-------|--------|--------|
| Decision idempotency | {count} duplicates | {status} |
| Trace completeness | {count} missing | {status} |
| Confidence bounds | {count} out of range | {status} |
| Learning idempotency | {count} duplicates | {status} |
| Buyer states | {info} | {status} |

---

## Summary

| Phase | Passed | Total | Status |
|-------|--------|-------|--------|
| Health Checks | X | 3 | {status} |
| Workflows | X | 6 | {status} |
| Data Quality | X | 4 | {status} |
| Relationships | X | 3 | {status} |
| Learning | X | 2 | {status} |
| API/Security | X | 6 | {status} |
| DB Constraints | X | 5 | {status} |
| Resilience | X | 4 | {status} |
| Decision Engine | X | 3 | {status} |
| Learning Loop | X | 3 | {status} |
| Buyer | X | 3 | {status} |

**TOTAL: X/42 checks passed**

### VERDICT: {PASS / FAIL}

{краткое резюме проблем если есть}
```

---

## Severity Legend

| Icon | Meaning |
|------|---------|
| PASS | Check passed |
| WARN | Warning (non-blocking) |
| FAIL | Error (blocking) |
| SKIP | Skipped |
| INFO | Informational |

---

## Quick Reference

**Phase mapping:**
- `--quick` → Phase 1
- `--workflows` → Phase 2, 2.5
- `--contracts` → Phase 6
- `--security` → Phase 7
- `--db` → Phase 8
- `--chaos` → Phase 9, 10
- `--decision` → Phase 11
- `--learning` → Phase 12
- `--buyer` → Phase 13
- `--functional` → Phase 11, 12, 13
