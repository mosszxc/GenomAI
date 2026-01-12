# Temporal Workflows Reference

## Overview

GenomAI использует Temporal для оркестрации бизнес-процессов:
- **Durability** — workflows переживают перезапуски и сбои
- **Visibility** — полная история выполнения в Temporal UI
- **Scalability** — горизонтальное масштабирование workers
- **Built-in retry** — автоматические повторы с backoff

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Temporal Cloud                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Schedules                         │   │
│  │  • keitaro-poller (1 hour) → chain trigger          │   │
│  │  • daily-recommendations (09:00 UTC)                │   │
│  │  • maintenance (6 hours)                            │   │
│  │  • health-check (3 hours)                           │   │
│  │                                                      │   │
│  │  Child workflows (not scheduled):                   │   │
│  │  • metrics-processor (child of keitaro)             │   │
│  │  • learning-loop (child of metrics-processor)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Task Queues                             │   │
│  │  • creative-pipeline                                 │   │
│  │  • metrics                                           │   │
│  │  • telegram                                          │   │
│  │  • agent-supervisor                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Workers                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Creative Pipeline Worker                   │   │
│  │  Queue: creative-pipeline                            │   │
│  │  Workflows: CreativePipelineWorkflow,               │   │
│  │             ModularHypothesisWorkflow               │   │
│  │  Activities: transcription, decomposition,           │   │
│  │              hypothesis, telegram, decision,         │   │
│  │              modular_generation                      │   │
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
│  ┌─────────────────────────────────────────────────────┐   │
│  │                Telegram Worker                       │   │
│  │  Queue: telegram                                     │   │
│  │  Workflows: BuyerOnboarding, HistoricalImport,      │   │
│  │             CreativeRegistration,                    │   │
│  │             HistoricalVideoHandler                   │   │
│  │  Activities: buyer, keitaro, supabase               │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Agent Supervisor Worker                   │   │
│  │  Queue: agent-supervisor                             │   │
│  │  Workflows: AgentSupervisorWorkflow                  │   │
│  │  Activities: github polling, task assignment,       │   │
│  │              agent management, orphan detection      │   │
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

### ModularHypothesisWorkflow

**Queue:** `creative-pipeline`
**Trigger:** Programmatic (from CreativePipelineWorkflow or manual)

Генерация гипотез из комбинаций модулей (Modular Creative System):
1. Проверка готовности модулей (check_modular_readiness)
2. Выбор комбинаций hook → promise → proof (select_module_combinations)
3. LLM синтез текста (synthesize_hypothesis_text)
4. Сохранение с review_status=pending_review (save_modular_hypothesis)

```python
@workflow.defn
class ModularHypothesisWorkflow:
    @workflow.run
    async def run(self, input: ModularHypothesisInput) -> ModularHypothesisResult:
        # Check readiness → Select combinations → LLM synthesis → Save
```

**Input:**
- `idea_id`: UUID idea
- `decision_id`: UUID decision
- `count`: Количество гипотез (default: 3)
- `vertical`: Optional фильтр по вертикали
- `geo`: Optional фильтр по GEO
- `buyer_id`: Optional buyer ID

**Requirements:**
- hooks >= 3 (status=active)
- promises >= 3 (status=active)
- proofs >= 2 (status=active)
- explored modules >= 2 (sample_size >= 5)

### KeitaroPollerWorkflow

**Queue:** `metrics`
**Schedule:** Every 1 hour (triggers metrics-processor → learning-loop chain)

Сбор метрик из Keitaro API:
1. Получить список trackers
2. Для каждого получить метрики
3. Upsert в raw_metrics
4. Создать daily snapshots

### MetricsProcessingWorkflow

**Queue:** `metrics`
**Schedule:** Child workflow of KeitaroPollerWorkflow (triggers learning-loop)

Обработка метрик:
1. Получить unprocessed snapshots
2. Создать outcomes
3. Emit events

### LearningLoopWorkflow

**Queue:** `metrics`
**Schedule:** Child workflow of MetricsProcessingWorkflow

Обновление scores:
1. Получить unprocessed outcomes
2. Обновить component_learnings
3. Проверить death conditions
4. Emit learning events

### DailyRecommendationWorkflow

**Queue:** `metrics`
**Schedule:** Daily at 09:00 UTC

Генерация и доставка рекомендаций:
1. Получить активных buyers
2. Для каждого сгенерировать recommendation
3. Отправить в Telegram
4. Обновить статус

### MaintenanceWorkflow

**Queue:** `metrics`
**Schedule:** Every 6 hours

Периодические задачи обслуживания:
1. Reset stale buyer states (> 6h)
2. Expire old recommendations (> 7 days)
3. Mark stuck transcriptions as failed (> 10 min)
4. Archive old failed creatives (> 7 days)
5. Data integrity checks
6. Staleness detection (Inspiration System)
7. Data cleanup (Hygiene Agent)
8. Emit maintenance event

**Event payload (`MaintenanceCompleted`):**
```json
{
  "buyers_reset": 0,
  "recommendations_expired": 0,
  "integrity_issues": 0,
  "integrity_issues_details": ["issue description 1", "..."]
}
```

**Replaces:** `H1uuOanSy627H4kg` Pipeline Health Monitor

### HealthCheckWorkflow

**Queue:** `metrics`
**Schedule:** Every 3 hours

Мониторинг здоровья системы (Hygiene Agent):
1. Check Supabase connection + latency
2. Get table sizes (8 tables)
3. Get pending counts (4 queue tables)
4. Compute health score (0.0-1.0)
5. Send Telegram alert if threshold breached
6. Save report to hygiene_reports

**Alerts:**
- CRITICAL: score < 0.5 (connection failure)
- WARNING: score < 0.8 (high latency, backlog)

### BuyerOnboardingWorkflow

**Queue:** `telegram`
**Trigger:** Telegram /start command

Workflow для онбординга новых байеров через Telegram.

### HistoricalImportWorkflow

**Queue:** `telegram`
**Trigger:** After buyer onboarding (keitaro_source provided)

Batch import campaigns from Keitaro for a buyer.

### CreativeRegistrationWorkflow

**Queue:** `telegram`
**Trigger:** Video URL from Telegram

Quick registration of creative from video URL.

### HistoricalVideoHandlerWorkflow

**Queue:** `telegram`
**Trigger:** API `/api/historical/submit-video`

Обработка video_url для historical import:
1. Find queue record by campaign_id
2. Update queue with video_url (status → ready)
3. Load buyer geos/verticals
4. Create creative with source_type='historical'
5. Emit HistoricalCreativeRegistered event
6. Execute CreativePipelineWorkflow (child)
7. Update queue status → completed

**Input:**
- `campaign_id`: Keitaro campaign ID
- `video_url`: Video URL to process
- `buyer_id`: Buyer UUID

### AgentSupervisorWorkflow

**Queue:** `agent-supervisor`
**Schedule:** Every 5 minutes

Multi-agent task distribution supervisor:
1. Poll GitHub for pending issues (optional)
2. Add new issues to task queue
3. Get available agents from registry
4. Assign tasks using smart assignment (specialization matching)
5. Release orphaned agents (no heartbeat for 10+ min)

**Input:**
- `poll_github`: Whether to poll GitHub (default: true)
- `github_labels`: Labels to filter (default: ["enhancement"])
- `github_limit`: Max issues to fetch (default: 10)
- `process_queue`: Whether to process queue (default: true)
- `max_assignments`: Max tasks to assign per run (default: 5)
- `run_orphan_detection`: Check for orphaned agents (default: true)
- `orphan_timeout_minutes`: Heartbeat timeout (default: 10)

**Smart Assignment Logic:**
1. Find agents with matching specialization first
2. If no match, use any available agent
3. Priority by most recent heartbeat
4. Atomic claim using `FOR UPDATE SKIP LOCKED`

**Related Tables:**
- `genomai.agents` - Agent registry
- `genomai.agent_tasks` - Task queue (Phase 2)

## Activities

### Supabase Activities
| Activity | Description |
|----------|-------------|
| `create_creative` | Create new creative |
| `create_historical_creative` | Create creative with tracker_id for historical import |
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

### Buyer Activities
| Activity | Description |
|----------|-------------|
| `create_buyer` | Create new buyer record |
| `load_buyer_by_telegram_id` | Load buyer by Telegram ID |
| `load_buyer_by_id` | Load buyer by UUID |
| `update_buyer` | Update buyer fields |
| `send_telegram_message` | Send message to Telegram |
| `queue_historical_import` | Queue campaign for import |
| `get_pending_imports` | Get pending imports for buyer |
| `update_import_status` | Update import queue status |
| `get_import_by_campaign_id` | Get import by campaign ID |
| `update_import_with_video` | Update import with video URL |

### Agent Supervisor Activities
| Activity | Description |
|----------|-------------|
| `get_pending_github_issues` | Poll GitHub for open issues |
| `get_pending_tasks_from_queue` | Get pending tasks from queue |
| `get_available_agents` | Get available agents (online, not busy) |
| `add_task_to_queue` | Add task to agent queue |
| `assign_task_to_agent` | Smart assignment with specialization matching |
| `release_orphaned_agents` | Mark orphaned agents as offline |
| `get_supervisor_stats` | Get agent/task counts |

## Schedules

| Schedule ID | Workflow | Interval | Description |
|-------------|----------|----------|-------------|
| `keitaro-poller` | KeitaroPollerWorkflow | 10 min | Collect Keitaro metrics |
| `metrics-processor` | MetricsProcessingWorkflow | 30 min | Process metrics into outcomes |
| `learning-loop` | LearningLoopWorkflow | 1 hour | Update component scores |
| `daily-recommendations` | DailyRecommendationWorkflow | 09:00 UTC | Generate daily recommendations |
| `maintenance` | MaintenanceWorkflow | 6 hours | Cleanup and integrity checks |
| `health-check` | HealthCheckWorkflow | 3 hours | Health monitoring + alerts |
| `agent-supervisor` | AgentSupervisorWorkflow | 2 hours | Multi-agent task distribution |

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
| `telegram` | 1+ | Buyer onboarding, historical import |

## See Also

- [TEMPORAL_RUNBOOK.md](./TEMPORAL_RUNBOOK.md) — Operational runbook
