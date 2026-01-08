# Temporal Workflows Reference

## Overview

GenomAI использует Temporal для оркестрации бизнес-процессов. Temporal заменяет n8n workflows, обеспечивая:
- **Durability** — workflows переживают перезапуски и сбои
- **Visibility** — полная история выполнения в Temporal UI
- **Scalability** — горизонтальное масштабирование workers
- **Built-in retry** — автоматические повторы с backoff

**Миграция:** n8n → Temporal (Issue #241, Phases 1-5)
**Статус:** Phase 5 Complete

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Temporal Cloud                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Schedules                         │   │
│  │  • keitaro-poller (10 min)                          │   │
│  │  • metrics-processor (30 min)                       │   │
│  │  • learning-loop (1 hour)                           │   │
│  │  • daily-recommendations (09:00 UTC)                │   │
│  │  • maintenance (6 hours)                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Task Queues                             │   │
│  │  • creative-pipeline                                 │   │
│  │  • metrics                                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Workers                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Creative Pipeline Worker                   │   │
│  │  Queue: creative-pipeline                            │   │
│  │  Workflows: CreativePipelineWorkflow                 │   │
│  │  Activities: transcription, decomposition,           │   │
│  │              hypothesis, telegram, decision          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Metrics Worker                         │   │
│  │  Queue: metrics                                       │   │
│  │  Workflows: KeitaroPoller, MetricsProcessing,        │   │
│  │             LearningLoop, DailyRecommendation,       │   │
│  │             SingleRecommendationDelivery,            │   │
│  │             Maintenance                               │   │
│  │  Activities: keitaro, metrics, learning,             │   │
│  │              recommendation, maintenance              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Workflows

### CreativePipelineWorkflow

**Queue:** `creative-pipeline`
**Trigger:** Webhook (new creative registration)

Полный pipeline обработки креатива:
1. Транскрипция видео (AssemblyAI)
2. LLM декомпозиция (OpenAI)
3. Создание idea
4. Decision Engine (APPROVE/REJECT/DEFER)
5. Генерация гипотез (если APPROVE)
6. Доставка в Telegram

```python
@workflow.defn
class CreativePipelineWorkflow:
    @workflow.run
    async def run(self, input: CreativePipelineInput) -> CreativePipelineResult:
        # Transcription → Decomposition → Idea → Decision → Hypothesis → Telegram
```

**Input:**
- `creative_id`: UUID креатива
- `video_url`: URL видео для транскрипции
- `buyer_id`: Optional buyer ID

**Replaces n8n workflows:**
- `WMnFHqsFh8i7ddjV` GenomAI - Creative Transcription
- `mv6diVtqnuwr7qev` creative_decomposition_llm
- `cGSyJPROrkqLVHZP` idea_registry_create
- `YT2d7z5h9bPy1R4v` decision_engine_mvp
- `oxG1DqxtkTGCqLZi` hypothesis_factory_generate
- `5q3mshC9HRPpL6C0` Telegram Hypothesis Delivery

### KeitaroPollerWorkflow

**Queue:** `metrics`
**Schedule:** Every 10 minutes

Сбор метрик из Keitaro API:
1. Получить список trackers
2. Для каждого получить метрики
3. Upsert в raw_metrics
4. Создать daily snapshots

**Replaces:** `0TrVJOtHiNEEAsTN` Keitaro Poller

### MetricsProcessingWorkflow

**Queue:** `metrics`
**Schedule:** Every 30 minutes

Обработка метрик:
1. Получить unprocessed snapshots
2. Создать outcomes
3. Emit events

**Replaces:**
- `Gii8l2XwnX43Wqr4` Snapshot Creator
- `bbbQC4Aua5E3SYSK` Outcome Processor
- `243QnGrUSDtXLjqU` Outcome Aggregator

### LearningLoopWorkflow

**Queue:** `metrics`
**Schedule:** Every hour

Обновление scores:
1. Получить unprocessed outcomes
2. Обновить component_learnings
3. Проверить death conditions
4. Emit learning events

**Replaces:** `fzXkoG805jQZUR3S` Learning Loop v2

### DailyRecommendationWorkflow

**Queue:** `metrics`
**Schedule:** Daily at 09:00 UTC

Генерация и доставка рекомендаций:
1. Получить активных buyers
2. Для каждого сгенерировать recommendation
3. Отправить в Telegram
4. Обновить статус

**Replaces:**
- `wgEdEqt2BA3P9JlA` Daily Recommendation Generator
- `QC8bmnAYdH5mkntG` Recommendation Delivery

### MaintenanceWorkflow

**Queue:** `metrics`
**Schedule:** Every 6 hours

Периодические задачи обслуживания:
1. Reset stale buyer states (> 6h)
2. Expire old recommendations (> 7 days)
3. Data integrity checks
4. Emit maintenance event

**Replaces:** `H1uuOanSy627H4kg` Pipeline Health Monitor

## Activities

### Supabase Activities
| Activity | Description |
|----------|-------------|
| `get_creative` | Get creative by ID |
| `get_idea` | Get idea by ID |
| `check_idea_exists` | Check if idea exists by hash |
| `create_idea` | Create new idea |
| `save_decomposed_creative` | Save decomposition result |
| `update_creative_status` | Update creative processing status |
| `emit_event` | Emit event to event log |

### Transcription Activities
| Activity | Description |
|----------|-------------|
| `transcribe_audio` | Submit audio to AssemblyAI |
| `get_transcript` | Poll for transcript result |

### LLM Activities
| Activity | Description |
|----------|-------------|
| `decompose_creative` | LLM decomposition (OpenAI) |
| `validate_decomposition` | Validate decomposition schema |
| `generate_hypotheses` | Generate hypotheses for idea |
| `save_hypotheses` | Save hypotheses to database |

### Telegram Activities
| Activity | Description |
|----------|-------------|
| `send_hypothesis_to_telegram` | Send hypothesis message |
| `get_buyer_chat_id` | Get buyer's Telegram chat ID |
| `update_hypothesis_delivery_status` | Update delivery status |
| `emit_delivery_event` | Emit delivery event |

### Keitaro Activities
| Activity | Description |
|----------|-------------|
| `get_all_trackers` | Get all trackers from Keitaro |
| `get_tracker_metrics` | Get metrics for single tracker |
| `get_batch_metrics` | Get metrics for batch of trackers |

### Metrics Activities
| Activity | Description |
|----------|-------------|
| `upsert_raw_metrics` | Upsert raw metrics from Keitaro |
| `create_daily_snapshot` | Create daily metrics snapshot |
| `check_snapshot_exists` | Check if snapshot exists |
| `process_outcome` | Process outcome from snapshot |
| `get_unprocessed_snapshots` | Get snapshots needing processing |
| `emit_metrics_event` | Emit metrics event |

### Learning Activities
| Activity | Description |
|----------|-------------|
| `process_learning_batch` | Process batch of outcomes |
| `get_unprocessed_outcomes` | Get outcomes needing learning |
| `process_single_outcome` | Process single outcome |
| `check_death_conditions` | Check if idea should be marked dead |
| `emit_learning_event` | Emit learning event |

### Recommendation Activities
| Activity | Description |
|----------|-------------|
| `get_active_buyers` | Get all active buyers |
| `generate_recommendation_for_buyer` | Generate recommendation |
| `send_recommendation_to_telegram` | Send recommendation to Telegram |
| `update_recommendation_delivery` | Update delivery status |
| `emit_recommendation_event` | Emit recommendation event |
| `get_recommendation_by_id` | Get recommendation by ID |
| `check_existing_daily_recommendation` | Check if buyer has today's recommendation |

### Maintenance Activities
| Activity | Description |
|----------|-------------|
| `reset_stale_buyer_states` | Reset stuck buyer states |
| `expire_old_recommendations` | Expire old pending recommendations |
| `check_data_integrity` | Run integrity checks |
| `emit_maintenance_event` | Emit maintenance event |

## Schedules

| Schedule ID | Workflow | Interval | Description |
|-------------|----------|----------|-------------|
| `keitaro-poller` | KeitaroPollerWorkflow | 10 min | Collect Keitaro metrics |
| `metrics-processor` | MetricsProcessingWorkflow | 30 min | Process metrics into outcomes |
| `learning-loop` | LearningLoopWorkflow | 1 hour | Update component scores |
| `daily-recommendations` | DailyRecommendationWorkflow | 09:00 UTC | Generate daily recommendations |
| `maintenance` | MaintenanceWorkflow | 6 hours | Cleanup and integrity checks |

### Schedule Management

```bash
# Create all schedules
python -m temporal.schedules create

# Delete all schedules
python -m temporal.schedules delete

# List schedules
python -m temporal.schedules list

# Pause schedule
python -m temporal.schedules pause keitaro-poller

# Resume schedule
python -m temporal.schedules resume keitaro-poller

# Trigger immediately
python -m temporal.schedules trigger daily-recommendations
```

## Configuration

Environment variables:
```bash
# Temporal
TEMPORAL_ADDRESS=your-namespace.tmprl.cloud:7233
TEMPORAL_NAMESPACE=genomai.xxxxx
TEMPORAL_API_KEY=your-api-key

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx

# External APIs
ASSEMBLYAI_API_KEY=xxx
OPENAI_API_KEY=xxx
TELEGRAM_BOT_TOKEN=xxx
KEITARO_API_KEY=xxx
KEITARO_API_URL=https://xxx.keitaro.io
```

## Task Queues

| Queue | Workers | Purpose |
|-------|---------|---------|
| `creative-pipeline` | 1+ | Creative processing pipeline |
| `metrics` | 1+ | Metrics, learning, recommendations, maintenance |

## Migration from n8n

### Migrated Workflows (31 total)

| n8n ID | Name | Temporal Workflow |
|--------|------|-------------------|
| `WMnFHqsFh8i7ddjV` | Creative Transcription | CreativePipelineWorkflow |
| `mv6diVtqnuwr7qev` | creative_decomposition_llm | CreativePipelineWorkflow |
| `cGSyJPROrkqLVHZP` | idea_registry_create | CreativePipelineWorkflow |
| `YT2d7z5h9bPy1R4v` | decision_engine_mvp | CreativePipelineWorkflow |
| `oxG1DqxtkTGCqLZi` | hypothesis_factory_generate | CreativePipelineWorkflow |
| `5q3mshC9HRPpL6C0` | Telegram Hypothesis Delivery | CreativePipelineWorkflow |
| `0TrVJOtHiNEEAsTN` | Keitaro Poller | KeitaroPollerWorkflow |
| `Gii8l2XwnX43Wqr4` | Snapshot Creator | MetricsProcessingWorkflow |
| `bbbQC4Aua5E3SYSK` | Outcome Processor | MetricsProcessingWorkflow |
| `243QnGrUSDtXLjqU` | Outcome Aggregator | MetricsProcessingWorkflow |
| `fzXkoG805jQZUR3S` | Learning Loop v2 | LearningLoopWorkflow |
| `wgEdEqt2BA3P9JlA` | Daily Recommendation Generator | DailyRecommendationWorkflow |
| `QC8bmnAYdH5mkntG` | Recommendation Delivery | DailyRecommendationWorkflow |
| `H1uuOanSy627H4kg` | Pipeline Health Monitor | MaintenanceWorkflow |
| `ClXUPP2IvWRgu99y` | keep_alive_decision_engine | **DELETED** (not needed) |

### Deleted Workflows

| n8n ID | Name | Reason |
|--------|------|--------|
| `ClXUPP2IvWRgu99y` | keep_alive_decision_engine | Temporal has persistent workers |

### Archived Workflows

Legacy workflows archived in `infrastructure/n8n-archive/`:
- Performance Metrics Collector
- Backfill Cost for Historical Queue
- And other legacy/manual workflows

## See Also

- [TEMPORAL_RUNBOOK.md](./TEMPORAL_RUNBOOK.md) — Operational runbook
- [N8N_WORKFLOWS.md](./N8N_WORKFLOWS.md) — Legacy n8n documentation (archived)
