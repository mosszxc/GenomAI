# Карта процессов GenomAI для тестирования

## Обзор системы

**GenomAI** — автономная система принятия решений в сфере маркетинга креативов.
- Market = truth (реальные CPA данные определяют успех)
- Deterministic + Traceable (каждое решение трассируемо)
- 15 Temporal workflows, 24 activities, 38 сервисов, 12 API routes

---

## 1. ОСНОВНЫЕ ПРОЦЕССЫ (15 процессов)

### P1: Creative Pipeline (Обработка креативов)

```
Вход: video_url, buyer_id
  ↓
[1.1] Загрузка креатива → creatives table
  ↓
[1.2] Конвертация видео → n8n webhook (MP4→MP3)
  ↓
[1.3] Транскрипция → AssemblyAI → transcripts table
  ↓
[1.4] Декомпозиция → LLM (OpenAI) → decomposed_creatives table
  ↓
[1.5] Регистрация идеи → IdeaRegistry → ideas table
  ↓
[1.6] Принятие решения → DecisionEngine (4-check wall)
  │
  ├─ APPROVED:
  │   ├─ [1.7a] Генерация гипотез → hypotheses table
  │   ├─ [1.7b] Извлечение модулей → module_bank table
  │   └─ [1.7c] Отправка в Telegram
  │
  ├─ REJECTED → Уведомление + причина
  └─ DEFERRED → Отложено для пересмотра

Выход: decision, hypotheses, modules (если approved)
```

**Ключевые точки тестирования:**
- Video URL parsing (YouTube, Google Drive, Dropbox, direct)
- n8n webhook для конвертации
- Транскрипция timeout (15 минут) и heartbeats (5 минут)
- Recovery: проверка existing transcript при retry
- LLM decomposition → Canonical Schema validation
- 4-check wall: schema_validity → death_memory → fatigue_constraint → risk_budget
- Идемпотентность: UNIQUE(idea_id, decision_epoch)
- Module extraction logic
- Telegram delivery retry (3 attempts, exponential backoff)

---

### P2: Metrics Collection (Сбор метрик)

```
Schedule: Every 1 hour (KeitaroPollerWorkflow)
Task Queue: metrics

[2.1] Circuit Breaker check
  │
  ├─ OPEN → Degraded mode, emit warning, skip
  │
  └─ CLOSED/HALF-OPEN:
      ↓
     [2.2] get_all_trackers() → Keitaro API
      ↓
     [2.3] get_batch_metrics(tracker_ids) → raw_metrics_current
      ↓
     [2.4] create_daily_snapshot() → daily_metrics_snapshot
      ↓
     [2.5] Record circuit breaker success
      ↓
     [2.6] Trigger MetricsProcessingWorkflow (child)
           ↓
          [2.7] process_outcome() → outcome_aggregates
           ↓
          [2.8] Trigger LearningLoopWorkflow (child)

Выход: outcome_aggregates, learning_triggered flag
```

**Ключевые точки тестирования:**
- Circuit breaker states: closed → half-open → open (5 failures)
- Keitaro API: POST /admin_api/v1/report/build
- Retry policy: 3 attempts, 5s-2m exponential backoff
- Batch processing: tracker batching
- Snapshot aggregation logic
- Parent-child workflow chain
- Degraded mode behavior

---

### P3: Learning Loop (Обучение системы)

```
Trigger: MetricsProcessingWorkflow completion
Task Queue: metrics

[3.1] fetch_unprocessed_outcomes()
      (WHERE learning_applied = false)
  ↓
[3.2] Batch mode OR Individual mode:

      BATCH MODE (default, efficient):
      └─ process_learning_batch(outcomes[])

      INDIVIDUAL MODE (observable):
      └─ for each outcome:
           ├─ get_current_confidence()
           ├─ calculate_delta(CPA < 20 → +0.1, else → -0.15)
           ├─ apply_time_decay()
           ├─ insert_confidence_version()
           ├─ insert_fatigue_version(+1)
           ├─ check_death_conditions()
           └─ mark learning_applied = true
  ↓
[3.3] Sub-learnings:
      ├─ component_learnings (angle_type, hook, etc.)
      ├─ premise_learnings (narrative vehicles)
      ├─ module_learnings (modular system)
      └─ component_pair_winrate (feature)
  ↓
[3.4] Feature monitoring:
      ├─ update_feature_correlations()
      ├─ detect_feature_drift()
      └─ auto_deprecate_features()

Выход: confidence, fatigue, death_state, component stats
```

**Ключевые точки тестирования:**
- Идемпотентность: source_outcome_id check
- Confidence bounds: clamp to [0.0, 1.0]
- Death transitions: active → soft_dead (3) → hard_dead (5)
- Resurrection blocking (hard_dead forever)
- Batch vs Individual mode
- Time decay calculation
- Feature correlation updates
- Drift detection thresholds

---

### P4: Recommendation Engine (Генерация рекомендаций)

```
Schedule: 09:00 UTC daily (DailyRecommendationWorkflow)
         + On-demand via API
Task Queue: metrics

[4.1] get_active_buyers()
  ↓
[4.2] For each buyer:
      ├─ check_existing_daily_recommendation()
      │   (skip if already has today's rec)
      ↓
      [4.3] Thompson Sampling decision:
            ├─ 75% Exploitation → best known components
            └─ 25% Exploration:
                 ├─ 10% Cross-segment transfer
                 └─ 15% Random exploration
      ↓
      [4.4] generate_recommendation():
            ├─ Select top components by win_rate
            ├─ Calculate avg_confidence
            ├─ Apply avatar/geo/vertical filters
            └─ Create recommendation record
      ↓
      [4.5] send_recommendation_to_telegram()
      ↓
      [4.6] emit_recommendation_event()

Выход: recommendation (id, components, mode, avg_confidence)
```

**Ключевые точки тестирования:**
- Thompson Sampling: 75/25 distribution
- Cross-segment transfer: 10% of explorations
- Min samples threshold: 10 for reliable confidence
- Skip logic for existing daily recommendation
- Avatar/geo/vertical filtering
- Telegram delivery retry

---

### P5: Buyer Onboarding (Регистрация пользователей)

```
Trigger: Telegram /start command
Task Queue: telegram

[5.1] Create BuyerOnboardingWorkflow
  ↓
[5.2] State Machine (Temporal Signals):

      AWAITING_NAME ─[signal: submit_name]→
      AWAITING_GEO ─[signal: submit_geos]→
      AWAITING_VERTICAL ─[signal: submit_vertical]→
      AWAITING_KEITARO ─[signal: submit_keitaro_source]→
        │
        ├─ Validation: check Keitaro campaigns exist
        │   (max 3 retries with error messages)
        │
        └─ Valid:
           LOADING_HISTORY
             ↓
           [5.3] Queue HistoricalImportWorkflow (child)
             ↓
           AWAITING_VIDEOS ─[signal: submit_video]→
             (loop for each campaign without video)
             ↓
           COMPLETED
             ↓
           [5.4] emit buyer_onboarding_completed event

Выход: buyer record, historical imports queued
```

**Ключевые точки тестирования:**
- Signal timeout: 5 minutes per step
- State transitions: exact sequence
- Keitaro source validation (sub10 format)
- Geo validation (RU, KZ, etc.)
- Vertical validation (nutra, gambling, etc.)
- Video URL validation
- Error message formatting
- State persistence on timeout

---

### P6: Historical Import (Импорт истории)

```
Trigger: Onboarding completion OR API POST
Task Queue: telegram

[6.1] HistoricalImportWorkflow:
      ├─ keitaro.get_campaigns_by_source(sub10)
      ├─ For each campaign (batched):
      │    ├─ queue_historical_import()
      │    └─ emit_event()
      └─ continue-as-new (if > 500 campaigns)
  ↓
[6.2] HistoricalVideoHandlerWorkflow (per campaign):
      ├─ Receive video URL via signal
      ├─ Validate URL format
      ├─ Create creative record
      └─ Trigger CreativePipelineWorkflow
  ↓
[6.3] HistoricalBulkImportWorkflow (массовый):
      └─ Process multiple campaigns in parallel

Выход: historical creatives queued for processing
```

**Ключевые точки тестирования:**
- Batch limit: 500 campaigns before continue-as-new
- Campaign ID uniqueness
- Video URL formats (YouTube, Drive, Dropbox)
- Workflow chaining
- Error handling per campaign
- Progress tracking

---

### P7: Modular Hypothesis Generation (Модульные гипотезы)

```
Trigger: CreativePipelineWorkflow (alternative path)
Task Queue: creative-pipeline

[7.1] ModularHypothesisWorkflow:
      ├─ check_modular_readiness()
      │   (enough modules in bank?)
      ↓
      [7.2] select_module_combinations():
            ├─ 90% Exploitation (proven combinations)
            └─ 10% Exploration (new combinations)
      ↓
      [7.3] For each combination:
            ├─ synthesize_hypothesis_text() [LLM]
            └─ save_modular_hypothesis()
      ↓
      [7.4] Update module compatibility stats

Выход: modular hypotheses with module references
```

**Ключевые точки тестирования:**
- Module bank sufficiency check
- 90/10 exploit/explore ratio
- Module compatibility scoring
- LLM synthesis quality
- Hypothesis deduplication

---

### P8: Premise Extraction (Извлечение предпосылок)

```
Trigger: Creative conclusion (win/loss determined)
Task Queue: knowledge

[8.1] PremiseExtractionWorkflow:
      ├─ load_creative_data()
      ├─ extract_premises_via_llm()
      │   ├─ WIN → successful premise patterns
      │   └─ LOSS → anti-patterns
      ├─ For each premise:
      │    └─ upsert_premise_and_learning()
      └─ emit_premise_extraction_event()
  ↓
[8.2] PremiseExtractionBatchWorkflow (массовый):
      └─ Process multiple creatives

Выход: premise records, premise_learnings updated
```

**Ключевые точки тестирования:**
- Идемпотентность: safe on retry
- Win/loss determination
- LLM extraction quality
- Premise deduplication
- Learning stats update

---

### P9: Knowledge Extraction (Извлечение знаний)

```
Trigger: API upload or Telegram document
Task Queue: knowledge

[9.1] KnowledgeIngestionWorkflow:
      ├─ save_knowledge_source()
      ├─ extract_knowledge_from_transcript() [LLM]
      ├─ save_pending_extractions()
      └─ notify_admin() [Telegram]
  ↓
[9.2] Human Review (Telegram /approve, /reject):
      ├─ APPROVED → KnowledgeApplicationWorkflow
      └─ REJECTED → Update status, log reason
  ↓
[9.3] KnowledgeApplicationWorkflow:
      Route by knowledge_type:
      ├─ premise → apply_premise_knowledge()
      ├─ creative_attribute → apply_creative_attribute()
      ├─ process_rule → apply_process_rule()
      └─ component_weight → apply_component_weight()

Выход: applied knowledge, updated system parameters
```

**Ключевые точки тестирования:**
- Source types: youtube, file, manual, transcript
- LLM extraction accuracy
- Knowledge type routing
- Admin notification delivery
- Application side effects
- Approval/rejection flow

---

### P10: Maintenance (Обслуживание системы)

```
Schedule: Every 6 hours (MaintenanceWorkflow)
Task Queue: metrics

[10.1] reset_stale_buyer_states()
       (awaiting_* > 6 hours → reset)

[10.2] expire_old_recommendations()
       (older than 7 days)

[10.3] mark_stuck_transcriptions_failed()
       (processing > 5 minutes)

[10.4] archive_failed_creatives()
       (failed > 7 days → archived)

[10.5] check_data_integrity()
       (orphaned records, invalid references)

[10.6] check_staleness() [Inspiration System]
       (ideas without recent activity)

[10.7] release_orphaned_agent_tasks()
       (multi-agent cleanup)

[10.8] retry_failed_hypotheses()
       (Issue #313: up to 3 retries)

[10.9] cleanup_exhausted_hypotheses()
       (Issue #475: 3+ failures → archived)

[10.10] find_stuck_creatives()
        (Issue #481: force cancel + reset)

[10.11] run_hygiene_cleanup()

Выход: maintenance_report, alerts if critical
```

**Ключевые точки тестирования:**
- Timeout thresholds для каждой операции
- Idempotency всех cleanup операций
- Alert triggers (critical vs warning)
- Stuck recovery: force cancel logic
- Hypothesis retry counter (max 3)
- Agent task orphan detection

---

### P11: Health Check (Проверка здоровья)

```
Schedule: Every 3 hours (HealthCheckWorkflow)
Task Queue: metrics

[11.1] check_supabase_connection()
       ├─ Connection test
       └─ Latency measurement

[11.2] get_table_sizes()
       (row counts for key tables)

[11.3] get_pending_counts()
       ├─ Unprocessed outcomes
       ├─ Pending transcriptions
       └─ Queued imports

[11.4] Calculate health_score (weighted)

[11.5] Alert thresholds:
       ├─ Critical: score < 0.5 → send_admin_alert()
       └─ Warning: score < 0.8 → send_admin_alert()

[11.6] save_hygiene_report()

Выход: health_report (DB), alerts (Telegram if needed)
```

**Ключевые точки тестирования:**
- Supabase connection resilience
- Threshold calculations
- Health score formula
- Alert delivery (Telegram)
- Report persistence
- Latency thresholds

---

### P12: Telegram Bot Commands (30 команд)

```
Trigger: Telegram message/command
Handler: /src/routes/telegram.py

ИНФОРМАЦИОННЫЕ:
├─ /start → BuyerOnboardingWorkflow
├─ /help → справка
├─ /stats → статистика buyer
├─ /status → статус системы
└─ /activity → активность покупателя

АНАЛИТИКА:
├─ /genome → тепловая карта генома
├─ /confidence → уровень уверенности
├─ /trends → тренды метрик
├─ /drift → детектор дрейфа
└─ /correlations → корреляции

УПРАВЛЕНИЕ:
├─ /recommend → генерация рекомендации
├─ /buyers → список покупателей
├─ /decisions → история решений
├─ /creatives → история креативов
├─ /pending → ожидающие действия
├─ /approve {id} → одобрить экстракцию
├─ /reject {id} → отклонить экстракцию
├─ /knowledge → управление знаниями
└─ /errors → показать ошибки

ИНТЕРАКТИВНЫЕ:
├─ /simulate → what-if симуляции
├─ /feedback → обратная связь → GitHub Issue
├─ Video URL detection → CreativePipelineWorkflow
├─ Document upload → KnowledgeIngestionWorkflow
└─ Callback queries → button handlers

MESSAGE HANDLERS:
├─ handle_user_message() → onboarding signals
├─ handle_video_url() → creative registration
├─ handle_document_upload() → knowledge ingestion
└─ handle_callback_query() → inline buttons
```

**Ключевые точки тестирования:**
- Command parsing и routing
- Authorization (buyer_id from telegram_id)
- Rate limiting (Telegram 429 handling)
- Error tracking (WebhookErrorStats)
- Chart generation (genome_heatmap, trends)
- Inline keyboard callbacks
- File upload handling
- Video URL detection regex
- GitHub issue creation from /feedback

---

### P13: Webhook Processing (Обработка вебхуков)

```
[13.1] Telegram Webhook (POST /webhook/telegram):
       ├─ Parse TelegramUpdate
       ├─ Route by message type:
       │    ├─ Command → command handler
       │    ├─ Text → onboarding signal OR video URL detection
       │    ├─ Document → knowledge ingestion
       │    └─ Callback → button handler
       ├─ Error tracking (in-memory counter)
       └─ Response: 200 OK always (Telegram requirement)

[13.2] Transcript Status Webhook (POST /webhook/transcript-status):
       ├─ Source: Supabase pg_net trigger
       ├─ Payload: {creative_id, ConvertStatus, TranscribeStatus, TranslateStatus}
       ├─ Update transcript record
       └─ Trigger next pipeline step if ready

Выход: workflow triggers, status updates
```

**Ключевые точки тестирования:**
- Telegram update parsing
- pg_net trigger format
- Status transition logic
- Always 200 response for Telegram
- Error counter limits
- Concurrent webhook handling

---

### P14: Circuit Breaker (Отказоустойчивость)

```
Location: /temporal/circuit_breaker.py

[14.1] States:
       ├─ CLOSED → normal operation
       ├─ HALF-OPEN → testing recovery
       └─ OPEN → blocking requests

[14.2] Transitions:
       CLOSED ─[5 consecutive failures]→ OPEN
       OPEN ─[timeout 60s]→ HALF-OPEN
       HALF-OPEN ─[success]→ CLOSED
       HALF-OPEN ─[failure]→ OPEN

[14.3] Usage in KeitaroPollerWorkflow:
       ├─ check_circuit() before API calls
       ├─ record_circuit_outcome() after each call
       └─ Degraded mode if OPEN

[14.4] Metrics staleness detection:
       └─ GET /health/metrics → is_stale, circuit_state
```

**Ключевые точки тестирования:**
- State transitions (all 4)
- Failure counter
- Timeout reset
- Degraded mode behavior
- Staleness calculation
- Recovery flow

---

### P15: Analytics Services (Аналитические сервисы)

```
Services in /src/services/:

[15.1] genome_heatmap.py:
       └─ Generate visual genome matrix

[15.2] what_if_simulator.py:
       └─ Simulate "what if" scenarios

[15.3] drift_detection.py:
       └─ Detect performance drift over time

[15.4] staleness_detector.py:
       └─ Identify stale ideas for inspiration

[15.5] correlation_discovery.py:
       └─ Find correlations between variables

[15.6] feature_correlation.py:
       └─ Track feature correlation metrics

[15.7] cross_transfer.py:
       └─ Transfer learnings across segments

[15.8] external_inspiration.py:
       └─ Integrate external market signals

[15.9] charts.py:
       └─ Generate chart URLs for Telegram
```

**Ключевые точки тестирования:**
- Chart generation accuracy
- Drift detection thresholds
- Correlation calculations
- Cross-transfer conditions
- Staleness criteria

---

## 2. ВНЕШНИЕ ИНТЕГРАЦИИ (8 интеграций)

### I1: Keitaro API
```
Endpoint: POST /admin_api/v1/report/build
Auth: API Key header
Operations:
├─ get_all_trackers()
├─ get_batch_metrics()
└─ get_campaigns_by_source()

Retry: 3 attempts, 5s-2m exponential backoff
Circuit Breaker: opens after 5 consecutive failures
```

### I2: Supabase (PostgreSQL + PostgREST)
```
URL: https://ftrerelppsnbdcmtcwya.supabase.co
Schema: genomai
Auth: Service Role Key (Bearer token)
Extensions: pg_cron, pg_net

Key Tables (42 migrations):
├─ ideas, decisions, decision_traces
├─ decomposed_creatives, transcripts
├─ outcome_aggregates, raw_metrics_current
├─ idea_confidence_versions, fatigue_state_versions
├─ buyers, buyer_interactions
├─ hypotheses, recommendations
├─ module_bank, component_learnings
├─ premise_registry, premise_learnings
├─ knowledge_sources, knowledge_extractions
├─ avatars, feature_correlations
└─ hygiene_reports, event_log

Retry: 5 attempts, 1s-30s exponential backoff
```

### I3: Telegram Bot API
```
URL: https://api.telegram.org/bot{token}/
Operations:
├─ sendMessage()
├─ sendPhoto()
├─ sendDocument()
└─ setWebhook()

Webhook: POST /webhook/telegram
Retry: 3 attempts, 1s-10s exponential backoff
Rate limit: respects Retry-After header
```

### I4: AssemblyAI (Transcription)
```
Operations:
├─ transcribe_audio()
└─ get_transcription_status()

Timeout: 15 minutes
Heartbeat: every 5 minutes
Recovery: saves transcript early, checks existing on retry
```

### I5: OpenAI/LLM
```
Operations:
├─ decompose_creative() → Canonical Schema
├─ generate_hypotheses() → Hypothesis text
├─ synthesize_hypothesis_text() → Modular hypothesis
├─ extract_knowledge() → Knowledge extraction
└─ extract_premises_via_llm() → Premise extraction

Retry: 2 attempts, 5s-2m backoff (expensive)
```

### I6: n8n Webhook (Video Conversion)
```
URL: https://aideportment.nl.tuna.am/webhook/MP3MP4
Operation: MP4 → MP3 conversion
Input: video URL (YouTube, Google Drive, Dropbox)
Output: MP3 URL for AssemblyAI
```

### I7: GitHub API
```
URL: https://api.github.com/repos/mosszxc/GenomAI/issues
Auth: GitHub Token
Operation: Create issue from Telegram /feedback
Trigger: /feedback command
```

### I8: Temporal Cloud
```
Address: auto-detect (.temporal.io or .tmprl.cloud)
Namespace: genomai.production (prod), default (local)
TLS: auto-enabled for cloud
Task Queues:
├─ creative-pipeline
├─ metrics
├─ telegram
└─ knowledge
```

---

## 3. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ВХОДЫ (INPUTS)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  [Telegram Bot]         [Keitaro API]      [Knowledge Upload]           │
│  /start, /help          Metrics            Documents                    │
│  Video URLs             Trackers           Transcripts                  │
│  Commands               Campaigns          YouTube/Files                │
│  Feedback               CPA data                                        │
│  Documents                                                              │
└────────────┬─────────────────┬──────────────────┬────────────────────────┘
             │                 │                  │
             ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ОБРАБОТКА (PROCESSING)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐              │
│  │   Creative    │  │   Metrics    │  │    Knowledge    │              │
│  │   Pipeline    │  │  Collection  │  │   Extraction    │              │
│  │ (transcribe,  │  │  (Keitaro)   │  │   (LLM parse)   │              │
│  │  decompose)   │  │              │  │                 │              │
│  └───────┬───────┘  └───────┬──────┘  └────────┬────────┘              │
│          │                  │                   │                       │
│          ▼                  ▼                   ▼                       │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐              │
│  │   Decision    │  │   Learning   │  │  Recommendation │              │
│  │    Engine     │◄─┤    Loop      │─►│     Engine      │              │
│  │  (4-check)    │  │  (outcomes)  │  │ (Thompson)      │              │
│  └───────┬───────┘  └──────────────┘  └────────┬────────┘              │
│          │                                      │                       │
│          ▼                                      ▼                       │
│  ┌───────────────┐                   ┌─────────────────┐               │
│  │   Hypothesis  │                   │    Analytics    │               │
│  │  Generation   │                   │  (drift, heatmap│               │
│  │  (modular)    │                   │   correlations) │               │
│  └───────────────┘                   └─────────────────┘               │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    MAINTENANCE & HEALTH                           │ │
│  │  cleanup, staleness, circuit breaker, retry, hygiene              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           ВЫХОДЫ (OUTPUTS)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  [Decisions]          [Recommendations]       [Alerts]                  │
│  approve/reject       Daily suggestions       Health warnings           │
│  + full traces        Component rankings      Maintenance reports       │
│                       Modular hypotheses      Circuit breaker state     │
│                                                                         │
│  [State Updates]      [Events]                [Telegram Messages]       │
│  Confidence           event_log               Hypotheses                │
│  Fatigue              Temporal events         Onboarding steps          │
│  Death state          Webhook triggers        Charts/heatmaps           │
│  Module stats                                 Recommendations           │
│  Premise stats                                Feedback → GitHub         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. TEMPORAL WORKFLOW SCHEDULE

| Workflow | Schedule | Task Queue | Trigger |
|----------|----------|------------|---------|
| KeitaroPollerWorkflow | Every 1 hour | metrics | Scheduled |
| MetricsProcessingWorkflow | - | metrics | Child of KeitaroPoller |
| LearningLoopWorkflow | - | metrics | Child of MetricsProcessing |
| DailyRecommendationWorkflow | 09:00 UTC | metrics | Scheduled |
| MaintenanceWorkflow | Every 6 hours | metrics | Scheduled |
| HealthCheckWorkflow | Every 3 hours | metrics | Scheduled |
| CreativePipelineWorkflow | - | creative-pipeline | API/Webhook |
| ModularHypothesisWorkflow | - | creative-pipeline | Optional child |
| BuyerOnboardingWorkflow | - | telegram | Telegram /start |
| HistoricalImportWorkflow | - | telegram | Child of Onboarding |
| HistoricalVideoHandlerWorkflow | - | telegram | Signal |
| KnowledgeIngestionWorkflow | - | knowledge | API/Telegram |
| KnowledgeApplicationWorkflow | - | knowledge | Approval signal |
| PremiseExtractionWorkflow | - | knowledge | Creative conclusion |
| SingleRecommendationDeliveryWorkflow | - | metrics | Manual trigger |

---

## 5. КРИТИЧЕСКИЕ БИЗНЕС-ПРАВИЛА

### R1: Decision Engine Rules
- **4-Check Wall** (fixed order): schema → death → fatigue → risk
- **Idempotency**: один decision на idea_id + epoch
- **Trace requirement**: каждое решение имеет полный trace
- **Atomic save**: RPC save_decision_with_trace

### R2: Learning Rules
- **CPA Threshold**: TARGET_CPA = 20.0
- **Confidence Delta**: +0.1 (good), -0.15 (bad)
- **Death Conditions**: 3 consecutive → soft_dead, 5 (after resurrect) → hard_dead
- **Idempotency**: source_outcome_id prevents double-processing
- **Time decay**: older outcomes have less weight

### R3: Recommendation Rules
- **Thompson Sampling**: 75% exploit / 25% explore
- **Cross-transfer**: 10% of explorations
- **Min samples**: 10 for reliable confidence
- **Daily limit**: 1 per buyer per day

### R4: Modular Rules
- **Module exploitation**: 90% / 10% exploration
- **Compatibility tracking**: module pair stats
- **Bank threshold**: minimum modules required

### R5: Onboarding Rules
- **Signal Timeout**: 5 minutes per step
- **Keitaro Validation**: max 3 retries
- **Batch Limit**: 500 campaigns before continue-as-new
- **Geo validation**: allowed list (RU, KZ, etc.)

### R6: Maintenance Rules
- **Stale State**: 6 hours timeout
- **Recommendation Expiry**: 7 days
- **Stuck Transcription**: 5 minutes timeout
- **Failed Creative Retention**: 7 days before archive
- **Hypothesis retry**: max 3 attempts

### R7: Circuit Breaker Rules
- **Failure threshold**: 5 consecutive failures → OPEN
- **Recovery timeout**: 60 seconds → HALF-OPEN
- **Degraded mode**: skip downstream workflows

---

## 6. API ENDPOINTS (12 routers, 37+ endpoints)

| Route | Methods | Auth | Description |
|-------|---------|------|-------------|
| `/health` | GET | No | Health check |
| `/health/metrics` | GET | No | Metrics staleness + circuit breaker |
| `/api/decision/` | POST | API_KEY | Make decision |
| `/learning/process` | POST | API_KEY | Process learning |
| `/learning/status` | GET | API_KEY | Learning status |
| `/api/idea-registry/register` | POST | API_KEY | Register idea |
| `/recommendations/*` | GET/POST | API_KEY | Recommendations CRUD |
| `/api/outcomes/aggregate` | POST | API_KEY | Aggregate outcomes |
| `/premise/*` | GET/POST | API_KEY | Premise operations |
| `/api/schema/validate` | POST | API_KEY | Validate schema |
| `/webhook/telegram` | POST | No | Telegram webhook |
| `/webhook/transcript-status` | POST | No | Transcript status |
| `/api/historical/*` | GET/POST | API_KEY | Historical import |
| `/api/schedules/*` | GET/POST | X-API-Key | Temporal schedules |
| `/api/knowledge/*` | GET/POST | API_KEY | Knowledge management |

---

## 7. РЕКОМЕНДУЕМЫЕ ТИПЫ ТЕСТИРОВАНИЯ

### Unit Tests (16+ существующих модулей)
- [ ] Decision Engine: each check individually
- [ ] Confidence delta calculations
- [ ] Death condition logic
- [ ] Thompson Sampling distribution
- [ ] Schema validation (Canonical Schema)
- [ ] Circuit breaker states
- [ ] Hashing (idempotency)
- [ ] Module extraction
- [ ] Premise extraction
- [ ] Geo validation
- [ ] Staleness detection
- [ ] Learning idempotency

### Integration Tests
- [ ] API endpoints: auth, validation, responses
- [ ] Supabase: CRUD, RPC calls (save_decision_with_trace)
- [ ] Temporal: workflow starts, signals, queries
- [ ] Webhooks: Telegram, transcript status

### E2E Tests
- [ ] Full Creative Pipeline: video → decision → hypothesis
- [ ] Full Learning Loop: outcome → confidence update
- [ ] Buyer Onboarding: /start → completion
- [ ] Daily Recommendation cycle
- [ ] Historical Import flow
- [ ] Knowledge extraction → approval → application

### Contract Tests
- [ ] Keitaro API responses
- [ ] Telegram Bot API
- [ ] Supabase PostgREST
- [ ] AssemblyAI responses
- [ ] OpenAI/LLM responses

### Load/Performance Tests
- [ ] Batch processing: 100+ outcomes
- [ ] Concurrent workflow executions
- [ ] API rate limits
- [ ] Telegram webhook throughput

### Resilience Tests
- [ ] Circuit breaker transitions
- [ ] Keitaro API failures
- [ ] Supabase connection failures
- [ ] Telegram delivery failures
- [ ] Workflow retry behavior

---

## 8. ENVIRONMENT VARIABLES

```bash
# Core
SUPABASE_URL=https://ftrerelppsnbdcmtcwya.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<key>
API_KEY=<api-key>
PORT=10000

# Temporal
TEMPORAL_ADDRESS=<address>
TEMPORAL_NAMESPACE=<namespace>
TEMPORAL_API_KEY=<key>

# External APIs
OPENAI_API_KEY=<key>
ASSEMBLYAI_API_KEY=<key>
TELEGRAM_BOT_TOKEN=<token>
KEITARO_API_KEY=<key>
KEITARO_BASE_URL=<url>
GITHUB_TOKEN=<token>
N8N_TRANSCRIBE_WEBHOOK=<url>

# Feature flags
USE_TEMPORAL_CREATIVE_PIPELINE=<true|false>
USE_TEMPORAL_TELEGRAM=<true|false>
USE_TEMPORAL_METRICS=<true|false>
```

---

## 9. SCRIPTS & CLI

### Task Management
- `task-start.sh <issue>` — создать ветку, worktree
- `task-done.sh <issue>` — PR в develop + qa-notes тест
- `task-new.sh` — создать новую задачу

### Development
- `make up` — запустить Temporal + Worker + FastAPI
- `make down` — остановить всё
- `make dev` — только FastAPI

### Testing
- `make test` — Critical tests (15s)
- `make test-unit` — All unit (45s)
- `make ci` — Full CI simulation
- `make e2e` — Full E2E (5 min)

### Deployment
- `deploy.sh` — develop → main → Render
- `safe-deploy.sh` — с проверками

---

## Итого

**Найдено процессов:** 15 основных + 9 аналитических сервисов
**Workflows:** 15 Temporal workflows
**Activities:** 24 activity modules
**API Routes:** 12 routers, 37+ endpoints
**Telegram Commands:** 30 команд
**External Integrations:** 8 (Keitaro, Supabase, Telegram, AssemblyAI, OpenAI, n8n, GitHub, Temporal)
**Database Tables:** 42 migrations
**Unit Tests:** 16 модулей

Эта карта процессов является полной основой для создания Test Plan.
