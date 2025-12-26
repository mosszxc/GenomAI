# Dependency Graph

Визуализация зависимостей между workflows, API и таблицами БД.

**Auto-generated from:** `infrastructure/schemas/dependency_manifest.json`
**Last updated:** 2025-12-26

---

## Workflow Call Graph

```mermaid
flowchart TD
    subgraph Telegram["Telegram Entry Points"]
        TR[telegram_router]
        BCR[buyer_creative_registration]
        BO[buyer_onboarding]
        BS[buyer_stats_command]
        BHUH[buyer_historical_url_handler]
        HIVH[historical_import_video_handler]
    end

    subgraph Creative["Creative Pipeline"]
        CIW[creative_ingestion_webhook]
        CDL[creative_decomposition_llm]
        CT[creative_transcription]
        IRC[idea_registry_create]
    end

    subgraph Decision["Decision Pipeline"]
        DEM[decision_engine_mvp]
        DE_API[Decision Engine API]
        HFG[hypothesis_factory_generate]
        THD[telegram_hypothesis_delivery]
    end

    subgraph Metrics["Metrics Pipeline"]
        KP[keitaro_poller]
        SC[snapshot_creator]
        OP[outcome_processor]
        OA[outcome_aggregator]
    end

    subgraph Learning["Learning Pipeline"]
        LLV2[learning_loop_v2]
        LL_API[Learning Loop API]
    end

    subgraph Buyer["Buyer Pipeline"]
        BHL[buyer_historical_loader]
        BTCC[buyer_test_conclusion_checker]
        BDD[buyer_daily_digest]
        HCI[historical_creative_import]
    end

    subgraph Maintenance["Maintenance"]
        KADE[keep_alive_decision_engine]
    end

    %% Telegram Router connections
    TR --> BO
    TR --> BS
    TR --> BCR
    TR --> BHUH

    %% Creative Pipeline
    CIW --> CDL
    BCR --> CDL
    CDL --> IRC
    IRC --> DEM
    CT -.-> CDL

    %% Decision Pipeline
    DEM --> DE_API
    DEM --> HFG
    HFG --> THD

    %% Metrics Pipeline
    KP --> SC
    KP --> BTCC
    SC --> OP
    SC --> OA
    OP --> DEM

    %% Learning Pipeline
    OA --> LLV2
    LLV2 --> LL_API

    %% Buyer Pipeline
    BO --> BHL
    BHUH --> HCI
    HIVH --> HCI
    HCI --> CT
    HCI --> LLV2

    %% Keep-alive
    KADE -.-> DE_API

    %% Styling
    classDef telegram fill:#0088cc,color:white
    classDef api fill:#ff6b6b,color:white
    classDef schedule fill:#ffd93d,color:black
    classDef inactive fill:#gray,color:white

    class TR,BCR,BO,BS,BHUH,HIVH telegram
    class DE_API,LL_API api
    class KP,KADE,BDD schedule
    class CIW inactive
```

---

## Critical Chains

### 1. Creative → Hypothesis Chain

```mermaid
sequenceDiagram
    participant TG as Telegram
    participant BCR as buyer_creative_registration
    participant CDL as creative_decomposition
    participant IRC as idea_registry
    participant DEM as decision_engine_mvp
    participant DE as Decision Engine API
    participant HFG as hypothesis_factory
    participant THD as telegram_delivery

    TG->>BCR: video_url + tracker_id
    BCR->>BCR: Insert creative
    BCR->>CDL: Call decomposition
    CDL->>CDL: LLM decompose
    CDL->>IRC: Call idea_registry
    IRC->>IRC: Create/find idea
    IRC->>DEM: Call decision_engine
    DEM->>DE: POST /api/decision
    DE-->>DEM: APPROVE/REJECT
    alt APPROVE
        DEM->>HFG: Call hypothesis_factory
        HFG->>HFG: LLM generate
        HFG->>THD: Call delivery
        THD->>TG: Send hypothesis
    end
```

### 2. Metrics → Learning Chain

```mermaid
sequenceDiagram
    participant KP as keitaro_poller
    participant SC as snapshot_creator
    participant OA as outcome_aggregator
    participant LLV2 as learning_loop_v2
    participant LL as Learning Loop API
    participant DB as Database

    KP->>KP: Get campaigns from Keitaro
    KP->>DB: Upsert raw_metrics
    KP->>SC: Call snapshot_creator
    SC->>DB: Create daily_snapshot
    SC->>OA: Call outcome_aggregator
    OA->>DB: Check idea + decision exists
    OA->>DB: Insert outcome_aggregate
    OA->>LLV2: Call learning_loop
    LLV2->>LL: POST /learning/process
    LL->>DB: Update idea confidence
    LL->>DB: Update idea death_state
```

---

## Table Dependencies

### Writers by Table

```mermaid
flowchart LR
    subgraph Workflows
        IRC[idea_registry]
        BCR[buyer_creative]
        CDL[decomposition]
        CT[transcription]
        OA[outcome_aggregator]
        HCI[historical_import]
        KP[keitaro_poller]
        SC[snapshot_creator]
        BO[buyer_onboarding]
    end

    subgraph API
        DE[Decision Engine]
        LL[Learning Loop]
    end

    subgraph Tables
        ideas[(ideas)]
        creatives[(creatives)]
        decomposed[(decomposed_creatives)]
        transcripts[(transcripts)]
        decisions[(decisions)]
        outcomes[(outcome_aggregates)]
        confidence[(idea_confidence)]
        raw[(raw_metrics)]
        snapshots[(daily_snapshots)]
        buyers[(buyers)]
    end

    IRC --> ideas
    IRC --> decomposed
    CDL --> decomposed
    BCR --> creatives
    CT --> creatives
    CT --> transcripts
    HCI --> creatives
    HCI --> outcomes
    OA --> outcomes
    KP --> raw
    SC --> snapshots
    BO --> buyers

    DE --> decisions
    DE --> ideas
    LL --> ideas
    LL --> confidence
    LL --> outcomes
```

### Read/Write Matrix

| Table | Writers | Readers |
|-------|---------|---------|
| `ideas` | idea_registry, DE API, LL API | decision_engine, outcome_aggregator, hypothesis_factory |
| `creatives` | buyer_creative, transcription, historical_import | decomposition, transcription, test_checker |
| `decisions` | DE API | outcome_aggregator, hypothesis_factory |
| `outcome_aggregates` | outcome_aggregator, historical_import, LL API | LL API |
| `raw_metrics` | keitaro_poller | snapshot_creator, test_checker, daily_digest |
| `daily_metrics_snapshot` | snapshot_creator | outcome_aggregator |
| `idea_confidence_versions` | LL API | LL API |
| `buyers` | buyer_onboarding | all buyer workflows |

---

## External Dependencies

```mermaid
flowchart TD
    subgraph n8n["n8n Workflows"]
        WF[Workflows]
    end

    subgraph External["External Services"]
        Render["Decision Engine<br/>(Render)"]
        OpenAI["OpenAI<br/>(LLM)"]
        AssemblyAI["AssemblyAI<br/>(Transcription)"]
        Keitaro["Keitaro<br/>(Tracking)"]
        GDrive["Google Drive<br/>(Video Storage)"]
        TG["Telegram<br/>(Bot API)"]
    end

    subgraph Supabase["Supabase"]
        DB[(genomai schema)]
    end

    WF --> Render
    WF --> OpenAI
    WF --> AssemblyAI
    WF --> Keitaro
    WF --> GDrive
    WF --> TG
    WF --> DB
    Render --> DB

    classDef external fill:#e0e0e0,stroke:#333
    class Render,OpenAI,AssemblyAI,Keitaro,GDrive,TG external
```

---

## Impact Analysis

### If you change...

| Component | Immediate Impact | Cascade Impact |
|-----------|-----------------|----------------|
| `idea_registry_create` | ideas table | decision_engine, hypothesis_factory, learning_loop |
| `decision_engine_mvp` | decisions table | hypothesis_factory, outcome_processor |
| `keitaro_poller` | raw_metrics | snapshot_creator → outcome_aggregator → learning_loop |
| `learning_loop_v2` | idea confidence, death_state | All future decisions for affected ideas |
| Decision Engine API | decisions, traces | All workflows calling /api/decision |
| Learning Loop API | ideas, confidence | Future decisions (death_state check) |

### Danger Zones

```
⚠️  HIGH RISK CHANGES:
├─ ideas.death_state → affects all future decisions
├─ outcome_aggregates.learning_applied → learning loop idempotency
├─ decomposed_creatives.idea_id → learning loop resolution
└─ decisions.decision_id → outcome_aggregates linkage
```

---

## Regenerating This Graph

```bash
# From dependency manifest
python scripts/sync_dependencies.py

# Validates manifest and generates Mermaid
```

See: `infrastructure/schemas/dependency_manifest.json` for source data.
