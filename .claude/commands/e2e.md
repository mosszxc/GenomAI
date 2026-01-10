# Full E2E Pipeline Test

Глубокое End-to-End тестирование GenomAI pipeline с валидацией данных, проверкой связей, SLA и regression.

## Аргументы

```
$ARGUMENTS = [--health] [--tracker=ID] [--quality] [--learning] [--integrations] [--temporal] [--regression]
```

## Execution Instructions

**ТЫ ДОЛЖЕН ВЫПОЛНИТЬ ТЕСТ АВТОМАТИЧЕСКИ. НЕ СПРАШИВАЙ ПОДТВЕРЖДЕНИЕ.**

### Режим выполнения

Определи режим по аргументам:
- Нет аргументов → **FULL TEST** (все phases)
- `--health` → только Phase 1
- `--tracker=ID` → Phase 1 + Phase 7 с указанным tracker_id
- `--quality` → Phase 1 + Phase 2 + Phase 2A + Phase 2B
- `--learning` → Phase 1 + Phase 2A
- `--integrations` → Phase 1 + Phase 2C
- `--temporal` → Phase 1 + Phase 5 (live schedule tests)
- `--regression` → Phase 1 + Phase 6

### Порядок выполнения

1. **Начни сразу** - не спрашивай подтверждение
2. **Выполняй параллельно** где возможно (несколько SQL запросов одновременно)
3. **Собирай результаты** в структурированный отчёт
4. **Используй TodoWrite** для отслеживания прогресса по phases
5. **В конце выведи Report** в формате из Phase 8

### Инструменты

- `mcp__supabase__execute_sql` - для SQL запросов (project_id: `ftrerelppsnbdcmtcwya`)
- `Bash` - для Temporal команд (`python -m temporal.schedules list/trigger`)
- `WebFetch` - для Decision Engine health check

### Test Data Loading (Phase 5)

**ПЕРЕД live тестами workflows — загрузи тестовые ID из БД:**

```sql
SELECT
  (SELECT id FROM genomai.creatives ORDER BY created_at DESC LIMIT 1) as test_creative_id,
  (SELECT id FROM genomai.ideas ORDER BY created_at DESC LIMIT 1) as test_idea_id,
  (SELECT id FROM genomai.decisions WHERE decision = 'approve' ORDER BY created_at DESC LIMIT 1) as test_decision_id,
  (SELECT tracker_id FROM genomai.raw_metrics_current LIMIT 1) as test_tracker_id,
  (SELECT id FROM genomai.decomposed_creatives ORDER BY created_at DESC LIMIT 1) as test_decomposed_id;
```

Сохрани результат как `TEST_IDS` и используй в Phase 5 для тестовых payloads.

### Параллельное выполнение

Выполняй эти группы запросов параллельно:

**Group 1 (Health):**
- Decision Engine health (WebFetch)
- Temporal schedules status (Bash)
- Supabase connectivity
- Telegram Bot health (WebFetch or SQL fallback)

**Group 2 (Data Quality):**
- Все SQL запросы Phase 2 (2.1-2.8)

**Group 3 (Learning + Aux):**
- Все SQL запросы Phase 2A + 2B + 2C

**Group 4 (Relationships + SLA):**
- Все SQL запросы Phase 3 + Phase 4

### Формат вывода

После выполнения всех проверок, выведи отчёт в формате Phase 8.
Используй emoji для статусов: ✅ OK, ⚠️ WARNING, ❌ ERROR, ⏭️ SKIP

### Schema Adaptation Rules

**ПЕРЕД выполнением SQL запросов — проверь схему через Phase 0.**

1. **Таблица не существует** → SKIP проверку, статус: ⏭️ SKIP (table missing)
2. **Колонка не существует** → SKIP проверку или убрать из SELECT если некритична
3. **При ошибке SQL** → записать в отчёт как ⚠️ WARNING (query failed: {error})

**Не используй fallback колонки** — лучше явный SKIP чем неправильные данные.

---

## Использование

```
/e2e                          # Полный тест (все проверки)
/e2e --health                 # Только health checks
/e2e --tracker=ID             # Тест конкретного креатива
/e2e --quality                # Data quality audit
/e2e --learning               # Learning loop health
/e2e --integrations           # Integration checks (Keitaro, DE API)
/e2e --regression             # Regression suite
```

---

## Phase 0: Schema Discovery (ОБЯЗАТЕЛЬНО ПЕРВЫМ)

**Перед любыми проверками выполни этот запрос:**

```sql
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'genomai'
ORDER BY table_name, ordinal_position;
```

**Сохрани результат как `SCHEMA_MAP` и используй для:**
- Проверки существования таблиц перед запросами
- Проверки существования колонок в SELECT/WHERE
- Отметки SKIP в отчёте для отсутствующих проверок

**Пример использования:**
- Если `creatives.updated_at` отсутствует → SKIP проверку Phase 6.3
- Если `decisions.reasoning` отсутствует → убрать из SELECT (некритичная)
- Если таблица `premises` отсутствует → SKIP все проверки Phase 2.8

---

## Phase 1: Service Health

### 1.1 Decision Engine

```
WebFetch: GET https://genomai.onrender.com/health
```

**Критерии:**
- Response status 200
- `{"status": "ok"}`
- Response time < 5s (cold start допустим < 30s)

### 1.2 Supabase

```sql
SELECT
  (SELECT COUNT(*) FROM genomai.config) as config_count,
  (SELECT COUNT(*) FROM genomai.creatives WHERE created_at > now() - interval '24 hours') as recent_creatives
```

**Критерии:**
- Query executes < 1s
- config_count > 0

### 1.3 Temporal Schedules

```bash
cd decision-engine-service && python -m temporal.schedules list
```

**Критерии:**
- All 5 schedules exist and not paused
- Recent actions within expected intervals

**Expected Schedules:**

| Schedule ID | Interval | Max Staleness |
|-------------|----------|---------------|
| `keitaro-poller` | 10 min | 15 min |
| `metrics-processor` | 30 min | 45 min |
| `learning-loop` | 1 hour | 2 hours |
| `daily-recommendations` | Daily 09:00 UTC | 25 hours |
| `maintenance` | 6 hours | 8 hours |

### 1.4 Temporal Worker Health

Check via Decision Engine health endpoint (workers run in same process):

```
WebFetch: GET https://genomai.onrender.com/health
```

**Критерии:** `temporal_connected: true` (if exposed in health response)

### 1.5 Telegram Bot Health

```sql
SELECT value FROM genomai.config WHERE key = 'telegram_bot_token';
```

Используя полученный токен:

```
WebFetch: GET https://api.telegram.org/bot{TOKEN}/getMe
```

**Критерии:**
- Response status 200
- `ok: true`
- `result.username` exists

**Note:** Если токен не найден в config → проверить env var `TELEGRAM_BOT_TOKEN`

**Альтернативная проверка (если нет доступа к токену):**

```sql
-- Проверить что deliveries отправляются
SELECT
  COUNT(*) as total_24h,
  COUNT(*) FILTER (WHERE status = 'sent') as sent,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  MAX(sent_at) as last_delivery
FROM genomai.deliveries
WHERE sent_at > now() - interval '24 hours';
```

**Критерии:**
- `failed / total_24h < 0.1` (< 10% failures)
- `last_delivery` within expected timeframe (if there was activity)

---

## Phase 2: Data Quality Checks

### 2.1 Creatives Quality

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

**Критерии:**
- `missing_url = 0`
- `missing_status = 0`
- `invalid_source_type = 0`
- `future_dates = 0`

**Severity:** missing_url > 0 = WARNING, invalid_source_type > 0 = ERROR

### 2.2 Transcripts Quality

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

**Критерии:**
- `null_text = 0`
- `too_short / total < 0.1` (< 10% слишком короткие)
- `placeholder_text = 0`
- `avg_length > 200`

### 2.3 Decomposed Creatives Quality

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

**Критерии:**
- `null_payload = 0`
- `missing_idea_link / total < 0.05` (< 5% без idea)
- `invalid_payload_type = 0`

### 2.4 Ideas Quality

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE canonical_hash IS NULL) as missing_hash,
  COUNT(*) FILTER (WHERE LENGTH(canonical_hash) != 64) as invalid_hash_length,
  COUNT(*) FILTER (WHERE death_state NOT IN ('soft_dead', 'hard_dead', 'permanent_dead') AND death_state IS NOT NULL) as invalid_death_state
FROM genomai.ideas
WHERE created_at > now() - interval '7 days';
```

**Критерии:**
- `missing_hash = 0`
- `invalid_hash_length = 0`
- `invalid_death_state = 0`

### 2.5 Decisions Quality

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE decision NOT IN ('approve', 'reject', 'defer')) as invalid_decision,
  COUNT(*) FILTER (WHERE idea_id IS NULL) as missing_idea,
  COUNT(*) FILTER (WHERE decision_epoch IS NULL OR decision_epoch < 1) as invalid_epoch
FROM genomai.decisions
WHERE created_at > now() - interval '7 days';
```

**Критерии:**
- `invalid_decision = 0`
- `missing_idea = 0`
- `invalid_epoch = 0`

**Note:** Reasoning хранится в `decision_traces.checks`, не в decisions

### 2.6 Hypotheses Quality

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

**Критерии:**
- `empty_content = 0`
- `too_short / total < 0.1`
- `invalid_status = 0`
- `delivered_no_timestamp = 0`

### 2.7 Deliveries Quality

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE channel IS NULL) as missing_channel,
  COUNT(*) FILTER (WHERE status IS NULL) as missing_status,
  COUNT(*) FILTER (WHERE idea_id IS NULL) as missing_idea,
  COUNT(*) FILTER (WHERE decision_id IS NULL) as missing_decision
FROM genomai.deliveries
WHERE sent_at > now() - interval '7 days';
```

**Критерии:**
- `missing_channel = 0`
- `missing_status = 0`
- `missing_idea = 0`
- `missing_decision = 0`

### 2.8 Premises Quality (#166)

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE name IS NULL OR name = '') as missing_name,
  COUNT(*) FILTER (WHERE premise_type NOT IN ('method', 'discovery', 'confession', 'secret', 'ingredient', 'mechanism', 'breakthrough', 'transformation')) as invalid_type,
  COUNT(*) FILTER (WHERE status NOT IN ('active', 'emerging', 'fatigued', 'dead')) as invalid_status,
  COUNT(*) FILTER (WHERE source NOT IN ('manual', 'llm_generated', 'extracted') AND source IS NOT NULL) as invalid_source
FROM genomai.premises;
```

**Критерии:**
- `missing_name = 0`
- `invalid_type = 0`
- `invalid_status = 0`
- `invalid_source = 0`

---

## Phase 2A: Learning Loop Health

### 2A.1 Learning Applied Check

```sql
SELECT
  COUNT(*) as total_outcomes,
  COUNT(*) FILTER (WHERE learning_applied = true) as learning_applied,
  COUNT(*) FILTER (WHERE learning_applied = false OR learning_applied IS NULL) as pending_learning,
  COUNT(*) FILTER (WHERE learning_applied = false AND created_at < now() - interval '1 hour') as stale_pending
FROM genomai.outcome_aggregates
WHERE created_at > now() - interval '7 days';
```

**Критерии:**
- `stale_pending = 0` (outcomes older than 1h should be processed)
- `learning_applied / total_outcomes > 0.9` (if total > 0)

**Severity:** stale_pending > 0 = WARNING, stale_pending > 5 = ERROR

### 2A.2 Confidence Versions Created

```sql
SELECT
  COUNT(*) as total_versions,
  COUNT(DISTINCT idea_id) as unique_ideas,
  MAX(updated_at) as last_confidence_update,
  now() - MAX(updated_at) as staleness
FROM genomai.idea_confidence_versions
WHERE updated_at > now() - interval '7 days';
```

**Критерии:**
- If outcomes exist with learning_applied=true, confidence versions should exist
- `staleness < interval '24 hours'` (if learning is active)

### 2A.3 Fatigue Versions Created

```sql
SELECT
  COUNT(*) as total_versions,
  COUNT(DISTINCT idea_id) as unique_ideas,
  MAX(updated_at) as last_fatigue_update,
  now() - MAX(updated_at) as staleness
FROM genomai.fatigue_state_versions
WHERE updated_at > now() - interval '7 days';
```

**Критерии:**
- Fatigue versions should be created alongside confidence versions
- `staleness < interval '24 hours'` (if learning is active)

### 2A.4 Component Learnings Freshness

```sql
SELECT
  COUNT(*) as total_components,
  COUNT(*) FILTER (WHERE sample_size > 0) as with_samples,
  MAX(updated_at) as last_update,
  now() - MAX(updated_at) as staleness,
  SUM(sample_size) as total_samples,
  AVG(win_rate) as avg_win_rate
FROM genomai.component_learnings;
```

**Критерии:**
- `staleness < interval '7 days'` (if learning is happening)
- `with_samples > 0` (if outcomes processed)

### 2A.5 Avatar Learnings Freshness

```sql
SELECT
  COUNT(*) as total_avatar_learnings,
  COUNT(*) FILTER (WHERE sample_size > 0) as with_samples,
  MAX(created_at) as last_created,
  SUM(sample_size) as total_samples
FROM genomai.avatar_learnings;
```

**Критерии:**
- Avatar learnings should exist if avatars are being used

### 2A.6 Premise Learnings Check (#166)

```sql
SELECT
  COUNT(*) as total_premise_learnings,
  COUNT(*) FILTER (WHERE sample_size > 0) as with_samples,
  MAX(updated_at) as last_update,
  SUM(sample_size) as total_samples
FROM genomai.premise_learnings;
```

**Критерии:**
- Premise learnings should exist if premises are being used in hypotheses

---

## Phase 2B: Auxiliary Tables Quality

### 2B.1 Buyers Quality

```sql
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE telegram_id IS NULL) as missing_telegram,
  COUNT(*) FILTER (WHERE name IS NULL OR name = '') as missing_name,
  COUNT(*) FILTER (WHERE status NOT IN ('active', 'inactive', 'blocked') AND status IS NOT NULL) as invalid_status,
  COUNT(*) FILTER (WHERE geos = '{}' OR geos IS NULL) as missing_geos,
  COUNT(*) FILTER (WHERE verticals = '{}' OR verticals IS NULL) as missing_verticals
FROM genomai.buyers;
```

**Критерии:**
- `missing_telegram = 0`
- `missing_name = 0`
- `invalid_status = 0`
- `missing_geos / total < 0.2` (< 20% without geos = OK)

### 2B.2 Stuck Buyer States

```sql
SELECT
  COUNT(*) as total_states,
  COUNT(*) FILTER (WHERE state != 'idle') as active_states,
  COUNT(*) FILTER (WHERE state != 'idle' AND updated_at < now() - interval '1 hour') as stuck_states
FROM genomai.buyer_states;
```

**Критерии:**
- `stuck_states = 0`

**Severity:** stuck_states > 0 = WARNING, stuck_states > 5 = ERROR

### 2B.3 Historical Import Queue

```sql
SELECT
  status,
  COUNT(*) as count,
  MIN(created_at) as oldest
FROM genomai.historical_import_queue
GROUP BY status;
```

```sql
-- Stuck pending_video
SELECT COUNT(*) as stuck_pending_video
FROM genomai.historical_import_queue
WHERE status = 'pending_video'
  AND created_at < now() - interval '7 days';
```

**Критерии:**
- `stuck_pending_video < 10` (some pending is OK)

**Severity:** stuck_pending_video > 50 = WARNING, > 100 = ERROR

### 2B.4 Avatars Quality

```sql
-- Note: avatars use MD5 hash (32 chars), ideas use SHA-256 (64 chars)
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE name IS NULL OR name = '') as missing_name,
  COUNT(*) FILTER (WHERE vertical IS NULL) as missing_vertical,
  COUNT(*) FILTER (WHERE status NOT IN ('emerging', 'validated', 'dead') AND status IS NOT NULL) as invalid_status,
  COUNT(*) FILTER (WHERE canonical_hash IS NOT NULL AND LENGTH(canonical_hash) != 32) as invalid_hash
FROM genomai.avatars;
```

**Критерии:**
- `missing_name = 0`
- `invalid_status = 0`
- `invalid_hash = 0`

### 2B.5 Unused Avatars

```sql
SELECT a.id, a.name, a.vertical, a.created_at
FROM genomai.avatars a
LEFT JOIN genomai.ideas i ON i.avatar_id = a.id
WHERE i.id IS NULL
  AND a.created_at < now() - interval '7 days'
  AND a.status != 'dead'
LIMIT 10;
```

**Критерии:** count < 10 (some unused is OK for new avatars)

### 2B.6 Recommendations Status

```sql
SELECT
  status,
  COUNT(*) as count
FROM genomai.recommendations
WHERE created_at > now() - interval '7 days'
GROUP BY status;
```

```sql
-- Expired not processed
SELECT COUNT(*) as expired_pending
FROM genomai.recommendations
WHERE status = 'pending'
  AND expires_at < now();
```

**Критерии:**
- `expired_pending = 0` (expired should be marked as 'expired')

### 2B.7 Exploration Log Health

```sql
SELECT
  exploration_type,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE was_successful IS NOT NULL) as with_outcome,
  AVG(CASE WHEN was_successful THEN 1 ELSE 0 END) as success_rate
FROM genomai.exploration_log
WHERE created_at > now() - interval '30 days'
GROUP BY exploration_type;
```

**Критерии:**
- Exploration decisions are being logged (if exploration is enabled)

---

## Phase 2C: Integration Checks

### 2C.1 Keitaro Metrics Freshness

```sql
SELECT
  COUNT(*) as total_trackers,
  MAX(updated_at) as last_update,
  now() - MAX(updated_at) as staleness,
  COUNT(*) FILTER (WHERE updated_at > now() - interval '1 hour') as fresh_count,
  COUNT(*) FILTER (WHERE updated_at < now() - interval '24 hours') as stale_count
FROM genomai.raw_metrics_current;
```

**Критерии:**
- `staleness < interval '25 hours'` (Keitaro Poller runs every 10 min)
- `stale_count / total_trackers < 0.5` (< 50% stale = OK)

**Severity:** staleness > 25h = WARNING, > 48h = ERROR

### 2C.2 Keitaro Config Active

```sql
SELECT
  COUNT(*) as total_configs,
  COUNT(*) FILTER (WHERE is_active = true) as active_configs,
  MAX(updated_at) as last_config_update
FROM genomai.keitaro_config;
```

**Критерии:**
- `active_configs = 1` (exactly one active config)

**Severity:** active_configs = 0 = ERROR, active_configs > 1 = WARNING

### 2C.3 Daily Metrics Snapshots

```sql
SELECT
  COUNT(*) as total_snapshots,
  MAX(date) as last_snapshot_date,
  current_date - MAX(date) as days_since_last
FROM genomai.daily_metrics_snapshot;
```

**Критерии:**
- `days_since_last <= 1` (snapshots should be daily)

**Severity:** days_since_last > 1 = WARNING, > 3 = ERROR

### 2C.4 Config Keys Validation

```sql
SELECT key, is_secret, updated_at
FROM genomai.config;
```

**Required keys:**
- `decision_engine_api_url`
- `decision_engine_api_key`

**Критерии:**
- All required keys present
- Keys not older than 30 days (security)

### 2C.5 Decision Engine API Smoke Test

```
WebFetch: POST https://genomai.onrender.com/api/decision/
Headers: X-API-Key: {from genomai.config}
Body: {
  "idea_id": "00000000-0000-0000-0000-000000000000",
  "canonical_hash": "test_e2e_smoke_" + timestamp,
  "payload": {"test": true}
}
```

**Критерии:**
- Response status 200 or 400 (reject for test data is OK)
- Response contains `decision` field
- Response time < 5s

**Note:** This creates a test decision that will be rejected by schema_validity check

### 2C.6 Hypothesis-Premise Link (#166)

```sql
SELECT
  COUNT(*) as total_hypotheses,
  COUNT(*) FILTER (WHERE premise_id IS NOT NULL) as with_premise,
  COUNT(*) FILTER (WHERE premise_id IS NULL) as without_premise
FROM genomai.hypotheses
WHERE created_at > now() - interval '7 days';
```

**Критерии:**
- `with_premise / total_hypotheses > 0.5` (> 50% should have premise if feature is active)

**Severity:** without_premise / total > 0.8 = WARNING (premise layer may not be integrated)

---

## Phase 3: Relationship Integrity

### 3.1 Orphaned Decomposed Creatives (no creative)

```sql
SELECT d.id, d.creative_id, d.created_at
FROM genomai.decomposed_creatives d
LEFT JOIN genomai.creatives c ON c.id = d.creative_id
WHERE c.id IS NULL
LIMIT 10;
```

**Критерии:** count = 0, **Severity:** ERROR

### 3.2 Orphaned Ideas (no decomposed)

```sql
SELECT i.id, i.canonical_hash, i.created_at
FROM genomai.ideas i
LEFT JOIN genomai.decomposed_creatives d ON d.idea_id = i.id
WHERE d.id IS NULL
  AND i.created_at > now() - interval '7 days'
LIMIT 10;
```

**Критерии:** count = 0, **Severity:** WARNING (могут быть легитимные)

### 3.3 Decisions Without Traces

```sql
SELECT d.id, d.decision, d.created_at
FROM genomai.decisions d
LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id
WHERE t.id IS NULL
  AND d.created_at > now() - interval '7 days'
LIMIT 10;
```

**Критерии:** count = 0, **Severity:** ERROR (traces обязательны)

### 3.4 Approved Without Hypothesis

```sql
SELECT d.id, d.idea_id, d.created_at
FROM genomai.decisions d
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
WHERE d.decision = 'approve'
  AND h.id IS NULL
  AND d.created_at > now() - interval '24 hours'
  AND d.created_at < now() - interval '1 hour'
LIMIT 10;
```

**Критерии:** count = 0, **Severity:** ERROR (approved должны иметь hypothesis)

### 3.5 Broken Creative Chain

```sql
-- Креативы с transcript но без decomposed (застряли)
SELECT c.id, c.tracker_id, c.status, t.created_at as transcript_at
FROM genomai.creatives c
JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = c.id
WHERE d.id IS NULL
  AND t.created_at < now() - interval '30 minutes'
LIMIT 10;
```

**Критерии:** count = 0, **Severity:** WARNING (pipeline stuck)

---

## Phase 4: SLA Monitoring

### 4.1 Stage Processing Times

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
  -- Transcription SLA: < 3 min
  COUNT(*) FILTER (WHERE transcript_at - creative_at > interval '3 minutes') as transcription_sla_breach,
  AVG(EXTRACT(EPOCH FROM (transcript_at - creative_at))) as avg_transcription_sec,

  -- Decomposition SLA: < 2 min
  COUNT(*) FILTER (WHERE decomposed_at - transcript_at > interval '2 minutes') as decomposition_sla_breach,
  AVG(EXTRACT(EPOCH FROM (decomposed_at - transcript_at))) as avg_decomposition_sec,

  -- Decision SLA: < 1 min
  COUNT(*) FILTER (WHERE decision_at - decomposed_at > interval '1 minute') as decision_sla_breach,
  AVG(EXTRACT(EPOCH FROM (decision_at - decomposed_at))) as avg_decision_sec,

  -- Hypothesis SLA: < 2 min
  COUNT(*) FILTER (WHERE hypothesis_at - decision_at > interval '2 minutes') as hypothesis_sla_breach,
  AVG(EXTRACT(EPOCH FROM (hypothesis_at - decision_at))) as avg_hypothesis_sec,

  -- Delivery SLA: < 1 min
  COUNT(*) FILTER (WHERE delivered_at - hypothesis_at > interval '1 minute') as delivery_sla_breach,
  AVG(EXTRACT(EPOCH FROM (delivered_at - hypothesis_at))) as avg_delivery_sec,

  -- Full pipeline SLA: < 10 min
  COUNT(*) FILTER (WHERE delivered_at - creative_at > interval '10 minutes') as full_pipeline_sla_breach,
  AVG(EXTRACT(EPOCH FROM (delivered_at - creative_at))) as avg_full_pipeline_sec
FROM pipeline_times
WHERE transcript_at IS NOT NULL;
```

**SLA Thresholds:**
| Stage | Target | Warning | Error |
|-------|--------|---------|-------|
| Transcription | < 3 min | > 3 min | > 5 min |
| Decomposition | < 2 min | > 2 min | > 4 min |
| Decision | < 1 min | > 1 min | > 2 min |
| Hypothesis | < 2 min | > 2 min | > 4 min |
| Delivery | < 1 min | > 1 min | > 2 min |
| Full Pipeline | < 10 min | > 10 min | > 15 min |

**Критерии:**
- `*_sla_breach / total < 0.1` (< 10% breaches = OK)
- `*_sla_breach / total < 0.2` (< 20% = WARNING)
- `*_sla_breach / total >= 0.2` (>= 20% = ERROR)

### 4.2 Stuck Items (Processing Backlog)

```sql
SELECT
  -- Pending transcription > 5 min
  (SELECT COUNT(*) FROM genomai.creatives c
   LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
   WHERE t.id IS NULL
     AND c.created_at < now() - interval '5 minutes'
     AND c.created_at > now() - interval '24 hours') as stuck_transcription,

  -- Pending decomposition > 5 min
  (SELECT COUNT(*) FROM genomai.transcripts t
   LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = t.creative_id
   WHERE d.id IS NULL
     AND t.created_at < now() - interval '5 minutes'
     AND t.created_at > now() - interval '24 hours') as stuck_decomposition,

  -- Pending decision > 5 min
  (SELECT COUNT(*) FROM genomai.decomposed_creatives d
   LEFT JOIN genomai.decisions dec ON dec.idea_id = d.idea_id
   WHERE dec.id IS NULL
     AND d.idea_id IS NOT NULL
     AND d.created_at < now() - interval '5 minutes'
     AND d.created_at > now() - interval '24 hours') as stuck_decision,

  -- Pending hypothesis > 5 min (only for approved)
  (SELECT COUNT(*) FROM genomai.decisions d
   LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
   WHERE d.decision = 'approve'
     AND h.id IS NULL
     AND d.created_at < now() - interval '5 minutes'
     AND d.created_at > now() - interval '24 hours') as stuck_hypothesis,

  -- Pending delivery > 5 min
  (SELECT COUNT(*) FROM genomai.hypotheses h
   WHERE h.status != 'delivered'
     AND h.status != 'failed'
     AND h.created_at < now() - interval '5 minutes'
     AND h.created_at > now() - interval '24 hours') as stuck_delivery;
```

**Критерии:**
- Any stuck > 0 = WARNING
- Any stuck > 5 = ERROR

---

## Phase 5: Temporal Schedule Tests (LIVE)

### Без локального Temporal

Workers запущены на Render, не локально. Тестирование работает через **Temporal Cloud**:

```bash
cd decision-engine-service

# 1. schedules module подключается к удалённому Temporal Cloud
python -m temporal.schedules list

# 2. Trigger отправляет задачу в Cloud
python -m temporal.schedules trigger keitaro-poller

# 3. Workers на Render подхватывают и выполняют
# 4. Результат проверяем в БД
```

**Почему это работает:**
- `temporal.schedules` использует те же credentials что и workers
- Подключение к Temporal Cloud (не localhost)
- Workers на Render polling тот же task queue
- Результат = данные в Supabase

**Если нет доступа к schedules CLI:**

```bash
# Через API endpoint (если есть)
curl -X POST https://genomai.onrender.com/api/trigger-workflow \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"workflow": "learning-loop"}'

# Через Temporal CLI к Cloud
temporal workflow start \
  --address <temporal-cloud-address> \
  --namespace <namespace> \
  --task-queue metrics \
  --type LearningLoopWorkflow
```

### Execution Rules

1. **Триггерить все safe schedules** — реальные тесты, не просто история
2. **Verify DB changes** after each trigger
3. **SKIP только** `daily-recommendations` (отправляет в Telegram)

### Schedule Safety Matrix

| Schedule | Action | Reason |
|----------|--------|--------|
| `keitaro-poller` | ✅ TRIGGER | Только читает из Keitaro API |
| `metrics-processor` | ✅ TRIGGER | Обрабатывает существующие snapshots |
| `learning-loop` | ✅ TRIGGER | Обновляет scores (нормальная работа) |
| `maintenance` | ✅ TRIGGER | Cleanup операции |
| `daily-recommendations` | ⏭️ SKIP | Отправляет сообщения в Telegram |

### 5.0 Schedule Status via Event Log (Recommended)

**Если Temporal CLI недоступен локально**, используй event_log для проверки:

```sql
-- Проверка всех schedules через события завершения
-- Event types: RawMetricsObserved, OutcomeAggregated, learning.applied, MaintenanceCompleted, RecommendationGenerated
SELECT
  'keitaro-poller' as schedule, '10 min' as interval,
  (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RawMetricsObserved') as last_run,
  now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RawMetricsObserved') as staleness,
  CASE WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RawMetricsObserved') < interval '15 min' THEN 'OK'
       WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RawMetricsObserved') < interval '30 min' THEN 'WARN' ELSE 'ERROR' END as status
UNION ALL SELECT 'metrics-processor', '30 min',
  (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'OutcomeAggregated'),
  now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'OutcomeAggregated'),
  CASE WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'OutcomeAggregated') < interval '45 min' THEN 'OK'
       WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'OutcomeAggregated') < interval '90 min' THEN 'WARN' ELSE 'ERROR' END
UNION ALL SELECT 'learning-loop', '1 hour',
  (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'learning.applied'),
  now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'learning.applied'),
  CASE WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'learning.applied') < interval '2 hours' THEN 'OK'
       WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'learning.applied') < interval '4 hours' THEN 'WARN' ELSE 'ERROR' END
UNION ALL SELECT 'maintenance', '6 hours',
  (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted'),
  now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted'),
  CASE WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted') < interval '8 hours' THEN 'OK'
       WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'MaintenanceCompleted') < interval '12 hours' THEN 'WARN' ELSE 'ERROR' END
UNION ALL SELECT 'daily-recommendations', 'Daily 09:00',
  (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RecommendationGenerated'),
  now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RecommendationGenerated'),
  CASE WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RecommendationGenerated') < interval '25 hours' THEN 'OK'
       WHEN now() - (SELECT MAX(occurred_at) FROM genomai.event_log WHERE event_type = 'RecommendationGenerated') < interval '48 hours' THEN 'WARN' ELSE 'ERROR' END;
```

**Критерии:** Все schedules имеют события в пределах интервалов.

### 5.0.1 Idle Schedule Detection (#287)

**Если schedule показывает WARN/ERROR**, проверь есть ли данные для обработки:

```sql
SELECT
  (SELECT COUNT(*) FROM genomai.outcome_aggregates WHERE learning_applied = false) as pending_outcomes,
  (SELECT COUNT(*) FROM genomai.daily_metrics_snapshot WHERE date = current_date) as today_snapshots;
```

**Интерпретация:**
| Schedule | pending = 0 | Event Stale | Verdict |
|----------|-------------|-------------|---------|
| metrics-processor | ✅ | Yes | OK (idle) — нет данных |
| metrics-processor | ❌ | Yes | ERROR — сломан |
| learning-loop | ✅ | Yes | OK (idle) — всё обработано |
| learning-loop | ❌ | Yes | ERROR — сломан |

### 5.1 Check Schedules Status

```bash
cd decision-engine-service && python -m temporal.schedules list
```

**Критерии:**
- All 5 schedules exist
- None paused

**Fallback:** Если CLI недоступен (Connection refused), используй 5.0 + 5.0.1

### 5.2 Trigger Keitaro Poller

```bash
cd decision-engine-service && python -m temporal.schedules trigger keitaro-poller
```

**DB Verification (wait 30s):**
```sql
SELECT
  event_type,
  occurred_at,
  payload->>'metrics_collected' as metrics_collected,
  payload->>'snapshots_created' as snapshots_created
FROM genomai.event_log
WHERE event_type = 'keitaro.polling.completed'
ORDER BY occurred_at DESC
LIMIT 1;
```

**Критерии:**
- Event emitted within last 2 minutes
- `metrics_collected >= 0`

**Alternative verification:**
```sql
SELECT MAX(updated_at) as last_update
FROM genomai.raw_metrics_current;
```
- `last_update` within last 2 minutes

### 5.3 Trigger Metrics Processor

```bash
cd decision-engine-service && python -m temporal.schedules trigger metrics-processor
```

**DB Verification (wait 30s):**
```sql
SELECT
  event_type,
  occurred_at,
  payload->>'outcomes_created' as outcomes_created,
  payload->>'snapshots_processed' as snapshots_processed
FROM genomai.event_log
WHERE event_type = 'metrics.processing.completed'
ORDER BY occurred_at DESC
LIMIT 1;
```

**Критерии:**
- Event emitted within last 2 minutes
- Execution completed (even if 0 outcomes created — OK if no data to process)

### 5.4 Trigger Learning Loop

```bash
cd decision-engine-service && python -m temporal.schedules trigger learning-loop
```

**DB Verification (wait 30s):**
```sql
SELECT
  event_type,
  occurred_at,
  payload->>'processed_count' as processed_count,
  payload->>'component_updates' as component_updates
FROM genomai.event_log
WHERE event_type = 'learning.batch.completed'
ORDER BY occurred_at DESC
LIMIT 1;
```

**Критерии:**
- Event emitted within last 2 minutes
- Execution completed (0 processed is OK if no pending outcomes)

**Alternative verification:**
```sql
SELECT MAX(updated_at) as last_learning_update
FROM genomai.component_learnings;
```

### 5.5 Trigger Maintenance

```bash
cd decision-engine-service && python -m temporal.schedules trigger maintenance
```

**DB Verification (wait 15s):**
```sql
SELECT
  event_type,
  occurred_at,
  payload->>'buyers_reset' as buyers_reset,
  payload->>'recommendations_expired' as recommendations_expired
FROM genomai.event_log
WHERE event_type = 'MaintenanceCompleted'
ORDER BY occurred_at DESC
LIMIT 1;
```

**Критерии:**
- Event emitted within last 2 minutes
- `buyers_reset` and `recommendations_expired` fields exist

### 5.6 Daily Recommendations (SKIP)

**НЕ ТРИГГЕРИТЬ** — отправляет реальные сообщения в Telegram.

Проверка только по истории:
```sql
SELECT
  occurred_at as last_recommendation,
  now() - occurred_at as staleness
FROM genomai.event_log
WHERE event_type = 'RecommendationGenerated'
ORDER BY occurred_at DESC
LIMIT 1;
```

**Критерии:**
- `staleness < 25 hours` (runs daily at 09:00 UTC)

### Execution Order

**ВАЖНО:** Триггерить последовательно с паузами:

```
1. keitaro-poller  → wait 30s → verify
2. metrics-processor → wait 30s → verify
3. learning-loop → wait 30s → verify
4. maintenance → wait 15s → verify
5. daily-recommendations → SKIP (verify history only)
```

**Причина:** Каждый schedule зависит от предыдущего:
- metrics-processor использует snapshots от keitaro-poller
- learning-loop использует outcomes от metrics-processor

### Phase 5 Report Format

```markdown
### 5. Temporal Live Tests

| # | Schedule | Triggered | Wait | Event Verified | Result |
|---|----------|-----------|------|----------------|--------|
| 5.2 | keitaro-poller | ✅ | 30s | ✅ keitaro.polling.completed | PASS |
| 5.3 | metrics-processor | ✅ | 30s | ✅ metrics.processing.completed | PASS |
| 5.4 | learning-loop | ✅ | 30s | ✅ learning.batch.completed | PASS |
| 5.5 | maintenance | ✅ | 15s | ✅ MaintenanceCompleted | PASS |
| 5.6 | daily-recommendations | ⏭️ SKIP | - | ✅ history < 25h | PASS |

**Live Tests: 4/4 triggered, 4/4 passed**
**Skipped: daily-recommendations (Telegram side effects)**

**Execution Details:**
- keitaro-poller: 15 metrics collected, 3 snapshots created
- metrics-processor: 2 outcomes created
- learning-loop: 2 outcomes processed, 5 component updates
- maintenance: 0 buyers reset, 1 recommendation expired
```

---

## Phase 6: Regression Suite

### 6.1 Known Issue: Orphan Ideas (#80)

```sql
SELECT COUNT(*) as orphan_ideas
FROM genomai.ideas i
LEFT JOIN genomai.decomposed_creatives d ON d.idea_id = i.id
WHERE d.id IS NULL
  AND i.created_at > now() - interval '7 days';
```

**Критерии:** count < 5 (some orphans acceptable from testing)

### 6.2 Known Issue: Missing Decision Traces

```sql
SELECT COUNT(*) as decisions_without_traces
FROM genomai.decisions d
LEFT JOIN genomai.decision_traces t ON t.decision_id = d.id
WHERE t.id IS NULL;
```

**Критерии:** count = 0

### 6.3 Known Issue: Stuck Creatives (#79)

```sql
-- SKIP если updated_at не существует в SCHEMA_MAP
SELECT COUNT(*) as stuck_creatives
FROM genomai.creatives c
WHERE c.status IN ('transcribing', 'decomposing', 'processing')
  AND c.updated_at < now() - interval '30 minutes';
```

**Критерии:** count = 0

**Schema Note:** Если `updated_at` не существует → ⏭️ SKIP эту проверку

### 6.4 Known Issue: Duplicate Decisions

```sql
SELECT idea_id, COUNT(*) as decision_count
FROM genomai.decisions
GROUP BY idea_id
HAVING COUNT(*) > 3
ORDER BY decision_count DESC
LIMIT 10;
```

**Критерии:** No idea with > 3 decisions (some retries OK)

### 6.5 Known Issue: Failed Deliveries Not Retried

```sql
SELECT COUNT(*) as failed_not_retried
FROM genomai.hypotheses
WHERE status = 'failed'
  AND created_at < now() - interval '1 hour'
  AND created_at > now() - interval '24 hours';
```

**Критерии:** count = 0 (failed should be retried or resolved)

### 6.6 Event Log Gaps

```sql
-- Проверить что события эмитятся
SELECT
  event_type,
  COUNT(*) as count_24h,
  MAX(occurred_at) as last_event
FROM genomai.event_log
WHERE occurred_at > now() - interval '24 hours'
GROUP BY event_type
ORDER BY count_24h DESC;
```

**Ожидаемые события:**
- `CreativeRegistered`
- `TranscriptCreated`
- `IdeaRegistered`
- `DecisionMade`
- `HypothesisGenerated`
- `HypothesisDelivered`

**Критерии:** All expected events present in last 24h (if there was activity)

---

## Phase 7: Pipeline Flow Test (--tracker=ID)

### 7.1 Load Creative

```sql
SELECT
  id, tracker_id, video_url, status, source_type, buyer_id, created_at
FROM genomai.creatives
WHERE tracker_id = '{tracker_id}';
```

### 7.2 Check Full Chain

```sql
-- Note: reasoning не существует в decisions, проверяем через decision_traces.checks
SELECT
  c.id as creative_id,
  c.status as creative_status,
  c.source_type,

  t.id as transcript_id,
  LENGTH(t.transcript_text) as transcript_length,
  t.created_at as transcript_at,

  d.id as decomposed_id,
  d.idea_id,
  d.schema_version,
  jsonb_typeof(d.payload) as payload_type,
  d.created_at as decomposed_at,

  i.canonical_hash,
  i.death_state,

  dec.id as decision_id,
  dec.decision,
  dec.created_at as decision_at,

  dt.id as trace_id,
  dt.checks IS NOT NULL as has_checks,

  h.id as hypothesis_id,
  h.status as hypothesis_status,
  LENGTH(h.content) as hypothesis_length,
  h.delivered_at,
  h.premise_id,

  p.name as premise_name,
  p.premise_type,

  rm.metrics IS NOT NULL as has_metrics,
  rm.updated_at as metrics_at,

  oa.id as outcome_id,
  oa.learning_applied,
  oa.created_at as outcome_at

FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives d ON d.creative_id = c.id
LEFT JOIN genomai.ideas i ON i.id = d.idea_id
LEFT JOIN genomai.decisions dec ON dec.idea_id = d.idea_id
LEFT JOIN genomai.decision_traces dt ON dt.decision_id = dec.id
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
LEFT JOIN genomai.premises p ON p.id = h.premise_id
LEFT JOIN genomai.raw_metrics_current rm ON rm.tracker_id = c.tracker_id
LEFT JOIN genomai.outcome_aggregates oa ON oa.creative_id = c.id
WHERE c.tracker_id = '{tracker_id}';
```

**Schema Note:** Reasoning хранится в `decision_traces.checks`, не в `decisions.reasoning`

### 7.3 Validate Each Stage

| Stage | Check | Pass Criteria |
|-------|-------|---------------|
| Creative | exists | status != null |
| Transcript | exists | length > 50 |
| Decomposition | exists | payload is object, idea_id set |
| Idea | exists | canonical_hash length = 64 |
| Decision | exists | decision in [approve,reject,defer], epoch >= 1 |
| Trace | exists | checks is not null (contains reasoning) |
| Hypothesis | if approved | content length > 100, premise_id set |
| Delivery | if hypothesis | status = delivered, delivered_at set |
| Metrics | exists | metrics is not null |
| Outcome | exists | window_start, window_end set |
| Learning | processed | learning_applied = true |

### 7.4 Timeline Analysis

```sql
SELECT
  'creative' as stage, c.created_at as timestamp
FROM genomai.creatives c WHERE c.tracker_id = '{tracker_id}'
UNION ALL
SELECT 'transcript', t.created_at
FROM genomai.transcripts t
JOIN genomai.creatives c ON c.id = t.creative_id
WHERE c.tracker_id = '{tracker_id}'
UNION ALL
SELECT 'decomposed', d.created_at
FROM genomai.decomposed_creatives d
JOIN genomai.creatives c ON c.id = d.creative_id
WHERE c.tracker_id = '{tracker_id}'
-- ... continue for all stages
ORDER BY timestamp;
```

---

## Phase 8: Report Generation

```markdown
## E2E Test Report

**Date:** {timestamp}
**Mode:** {mode}
**Duration:** {test_duration}

---

### Executive Summary

| Category | Status | Issues | Skipped |
|----------|--------|--------|---------|
| Services | OK/WARN/FAIL | {count} | {skip_count} |
| Data Quality | OK/WARN/FAIL | {count} | {skip_count} |
| Learning Loop | OK/WARN/FAIL | {count} | {skip_count} |
| Auxiliary Tables | OK/WARN/FAIL | {count} | {skip_count} |
| Integrations | OK/WARN/FAIL | {count} | {skip_count} |
| Relationships | OK/WARN/FAIL | {count} | {skip_count} |
| SLA | OK/WARN/FAIL | {count} | {skip_count} |
| **Temporal Live Tests** | OK/WARN/FAIL | {triggered}/{passed} | {skipped} |
| Regression | OK/WARN/FAIL | {count} | {skip_count} |

**Overall: PASS / WARNING / FAIL**
**Temporal Live Tests: 4/4 triggered, 1 skipped (daily-recommendations)**
**Schema Drift:** {count} missing columns detected

---

### 1. Service Health

| Service | Status | Response Time | Details |
|---------|--------|---------------|---------|
| Decision Engine | OK | 245ms | status=ok |
| Supabase | OK | 89ms | 2 config rows |
| Temporal | OK | - | 5/5 schedules active |
| Telegram Bot | OK | 120ms | @genomai_bot |

### 2. Data Quality

| Table | Total | Issues | Rate | Status |
|-------|-------|--------|------|--------|
| creatives | 150 | 0 | 0% | OK |
| transcripts | 145 | 2 | 1.4% | OK |
| decomposed | 140 | 0 | 0% | OK |
| ideas | 120 | 0 | 0% | OK |
| decisions | 120 | 0 | 0% | OK |
| hypotheses | 80 | 1 | 1.25% | OK |

**Issues Found:**
- 2 transcripts with length < 50 chars
- 1 hypothesis with empty content

### 2A. Learning Loop Health

| Check | Value | Status |
|-------|-------|--------|
| Outcomes processed | 45/50 (90%) | OK |
| Stale pending | 0 | OK |
| Confidence versions | 42 | OK |
| Fatigue versions | 42 | OK |
| Component learnings | 156 samples | OK |
| Avatar learnings | 12 records | OK |
| Premise learnings | 8 records | OK |

### 2B. Auxiliary Tables

| Table | Check | Count | Status |
|-------|-------|-------|--------|
| buyers | data quality | 0 issues | OK |
| buyer_states | stuck states | 0 | OK |
| historical_import | pending_video > 7d | 15 | WARN |
| avatars | quality | 0 issues | OK |
| avatars | unused | 3 | OK |
| recommendations | expired pending | 0 | OK |
| exploration_log | logged | 25 records | OK |

### 2C. Integration Health

| Integration | Check | Value | Status |
|-------------|-------|-------|--------|
| Keitaro | metrics freshness | 45 min ago | OK |
| Keitaro | config active | 1 | OK |
| Keitaro | daily snapshots | yesterday | OK |
| Config | required keys | all present | OK |
| Decision Engine | API smoke test | 200ms, reject | OK |
| Premises | hypothesis link rate | 65% | OK |

### 3. Relationship Integrity

| Check | Count | Status |
|-------|-------|--------|
| Orphaned decomposed | 0 | OK |
| Orphaned ideas | 2 | WARN |
| Decisions without traces | 0 | OK |
| Approved without hypothesis | 0 | OK |
| Broken creative chain | 0 | OK |

### 4. SLA Performance

| Stage | Avg | P95 | Breaches | Status |
|-------|-----|-----|----------|--------|
| Transcription | 45s | 120s | 2% | OK |
| Decomposition | 30s | 60s | 1% | OK |
| Decision | 15s | 30s | 0% | OK |
| Hypothesis | 25s | 50s | 3% | OK |
| Delivery | 5s | 10s | 0% | OK |
| Full Pipeline | 2m | 4m | 5% | OK |

**Stuck Items:**
| Stage | Count | Status |
|-------|-------|--------|
| Transcription | 0 | OK |
| Decomposition | 0 | OK |
| Decision | 0 | OK |
| Hypothesis | 1 | WARN |
| Delivery | 0 | OK |

### 5. Temporal Live Tests

| # | Schedule | Triggered | Wait | Event Verified | Result |
|---|----------|-----------|------|----------------|--------|
| 5.2 | keitaro-poller | ✅ | 30s | ✅ 15 metrics, 3 snapshots | PASS |
| 5.3 | metrics-processor | ✅ | 30s | ✅ 2 outcomes created | PASS |
| 5.4 | learning-loop | ✅ | 30s | ✅ 2 processed, 5 updates | PASS |
| 5.5 | maintenance | ✅ | 15s | ✅ 0 reset, 1 expired | PASS |
| 5.6 | daily-recommendations | ⏭️ SKIP | - | ✅ history < 25h | PASS |

**Live Tests: 4/4 triggered, 4/4 passed**
**Skipped: daily-recommendations (Telegram side effects)**
**Schedules: 5/5 active, 0 paused**

### 6. Regression Suite

| Test | Result | Details |
|------|--------|---------|
| Orphan ideas (#80) | PASS | 2 found (< 5 threshold) |
| Missing traces | PASS | 0 found |
| Stuck creatives (#79) | PASS | 0 found |
| Duplicate decisions | PASS | max 2 per idea |
| Failed deliveries | PASS | 0 unresolved |
| Event log gaps | PASS | all events present |

### 7. Pipeline Test (tracker: {id})

| Stage | Status | Duration | Details |
|-------|--------|----------|---------|
| Creative | PASS | - | status=transcribed |
| Transcript | PASS | 42s | 1,245 chars |
| Decomposition | PASS | 28s | idea_id=abc123 |
| Idea | PASS | - | hash=def456... |
| Decision | PASS | 12s | APPROVE |
| Trace | PASS | - | 4 checks |
| Hypothesis | PASS | 35s | 856 chars |
| Delivery | PASS | 3s | delivered |
| Metrics | SKIP | - | no keitaro data |
| Outcome | SKIP | - | pending metrics |
| Learning | SKIP | - | pending outcome |

**Pipeline Timeline:**
```
00:00 Creative registered
00:42 Transcript created (+42s)
01:10 Decomposed (+28s)
01:10 Idea linked
01:22 Decision: APPROVE (+12s)
01:57 Hypothesis generated (+35s)
02:00 Delivered to Telegram (+3s)
─────────────────────────────
Total: 2m 00s (SLA: < 10m) OK
```

---

### Schema Drift Detected

| Expected Column | Status | Impact |
|-----------------|--------|--------|
| creatives.updated_at | MISSING | Phase 6.3 SKIPPED |
| decisions.reasoning | MISSING | Removed from Phase 7.2 SELECT |

*(Если все колонки существуют — эту секцию можно пропустить)*

---

### Issues Summary

**Errors (must fix):**
- None

**Warnings (should review):**
- 2 orphaned ideas (cleanup recommended)
- 1 stuck hypothesis (check workflow)

**Skipped checks:**
- *(list any SKIP checks due to missing tables/columns)*

**Info:**
- 2 transcripts below length threshold (edge case)

---

### VERDICT: PASS

All critical checks passed. 2 warnings require attention.
```

---

## Примеры

```bash
# Full test with all phases
/e2e

# Quick health check only
/e2e --health

# Test specific creative through pipeline
/e2e --tracker=54321

# Data quality audit only
/e2e --quality

# Learning loop health check
/e2e --learning

# Integration checks (Keitaro, DE API, configs)
/e2e --integrations

# Temporal live schedule tests
/e2e --temporal

# Run regression suite only
/e2e --regression

# Combined: quality + learning
/e2e --quality --learning
```

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| ❌ **ERROR** | Critical issue, pipeline broken | Immediate fix required |
| ⚠️ **WARNING** | Non-critical issue, degraded | Review within 24h |
| ⏭️ **SKIP** | Check skipped (missing table/column) | Review schema drift |
| ℹ️ **INFO** | Observation, edge case | Log for analysis |
| ✅ **OK** | All checks passed | No action needed |

## Thresholds

| Metric | OK | WARNING | ERROR |
|--------|-----|---------|-------|
| Data quality rate | < 1% issues | 1-5% | > 5% |
| SLA breach rate | < 10% | 10-20% | > 20% |
| Schedule staleness | within interval | 2x interval | > 3x interval |
| Stuck items | 0 | 1-5 | > 5 |
| Orphaned records | < 5 | 5-20 | > 20 |
| Learning applied rate | > 90% | 70-90% | < 70% |
| Stale pending outcomes | 0 | 1-5 | > 5 |
| Keitaro metrics staleness | < 25h | 25-48h | > 48h |
| Daily snapshots gap | ≤ 1 day | 2-3 days | > 3 days |
| Stuck buyer states | 0 | 1-5 | > 5 |
| Stuck historical import | < 10 | 10-50 | > 50 |
| Expired recommendations | 0 | 1-10 | > 10 |
| Premise link rate | > 50% | 20-50% | < 20% |
| Unused avatars | < 10 | 10-25 | > 25 |

## Связанные команды

- `/valid {process}` — валидация конкретного процесса
- `python -m temporal.schedules list` — список schedules
- `python -m temporal.schedules trigger <id>` — ручной триггер
