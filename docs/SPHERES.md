# GenomAI Spheres

Система разбита на независимые сферы для модульного патчинга.

## Сферы

| # | Сфера | Label | Описание |
|---|-------|-------|----------|
| 1 | **Ingestion** | `sphere:ingestion` | Приём видео, транскрипция |
| 2 | **Decomposition** | `sphere:decomposition` | LLM-разбор на переменные (Canonical Schema) |
| 3 | **Idea Registry** | `sphere:idea-registry` | Управление идеями, дедупликация, кластеры |
| 4 | **Decision Engine** | `sphere:decision-engine` | 4 проверки → APPROVE/REJECT/DEFER |
| 5 | **Hypothesis Factory** | `sphere:hypothesis-factory` | Генерация исполнимых транскриптов |
| 6 | **Delivery** | `sphere:delivery` | Отправка в Telegram |
| 7 | **Metrics Collection** | `sphere:metrics` | Keitaro polling, snapshots |
| 8 | **Outcome Processing** | `sphere:outcomes` | Агрегация, обогащение контекстом |
| 9 | **Learning Loop** | `sphere:learning` | Обновление confidence/fatigue |
| 10 | **Buyer System** | `sphere:buyer` | Баеры, их креативы, отчёты |

## Компоненты по сферам

### 1. Ingestion
- **n8n:** `creative_ingestion_webhook` (dvZvUUmhtPzYOK7X)
- **n8n:** `GenomAI - Creative Transcription` (WMnFHqsFh8i7ddjV)
- **Таблицы:** `creatives`
- **Внешние:** Telegram Bot API, Whisper/AssemblyAI

### 2. Decomposition
- **n8n:** `creative_decomposition_llm` (mv6diVtqnuwr7qev)
- **Таблицы:** читает `creatives`
- **Внешние:** OpenAI/Anthropic API
- **Важно:** Только транскрипты, не визуалы

### 3. Idea Registry
- **n8n:** `idea_registry_create` (cGSyJPROrkqLVHZP)
- **Таблицы:** `ideas`
- **Логика:** `canonical_hash` дедупликация, `cluster_id`

### 4. Decision Engine
- **FastAPI:** `decision-engine-service/src/`
- **n8n:** `decision_engine_mvp` (YT2d7z5h9bPy1R4v)
- **Таблицы:** `decisions`, `decision_traces`
- **Checks:**
  - `schema_validity.py` → REJECT
  - `death_memory.py` → REJECT
  - `fatigue_constraint.py` → REJECT
  - `risk_budget.py` → DEFER

### 5. Hypothesis Factory
- **n8n:** `hypothesis_factory_generate` (oxG1DqxtkTGCqLZi)
- **Таблицы:** `hypotheses`
- **Внешние:** LLM API

### 6. Delivery
- **n8n:** `Telegram Hypothesis Delivery` (5q3mshC9HRPpL6C0)
- **Таблицы:** `deliveries`
- **Внешние:** Telegram Bot API

### 7. Metrics Collection
- **n8n:** `Keitaro Poller` (0TrVJOtHiNEEAsTN)
- **n8n:** `Snapshot Creator` (Gii8l2XwnX43Wqr4)
- **Таблицы:** `raw_metrics_current`, `daily_metrics_snapshot`
- **Внешние:** Keitaro API

### 8. Outcome Processing
- **n8n:** `Outcome Aggregator` (243QnGrUSDtXLjqU)
- **n8n:** `Outcome Processor` (bbbQC4Aua5E3SYSK)
- **Таблицы:** `outcome_aggregates`

### 9. Learning Loop
- **n8n:** `Learning Loop v2` (fzXkoG805jQZUR3S)
- **Таблицы:** `idea_confidence_versions`, `fatigue_state_versions`
- **Важно:** Только `system` outcomes → causal updates

### 10. Buyer System
- **n8n:** `Buyer Creative Registration` (d5i9dB2GNqsbfmSD)
- **n8n:** `Buyer Test Conclusion Checker` (4uluD04qYHhsetBy)
- **n8n:** `Buyer Daily Digest` (WkS1fPSxZaLmWcYy)
- **n8n:** `Buyer Stats Command` (rHuT8dYyIXoiHMAV)
- **Таблицы:** `buyers`, `buyer_states`, `component_learnings`

## Граф зависимостей

```
[1] Ingestion
      ↓
[2] Decomposition
      ↓
[3] Idea Registry
      ↓
[4] Decision Engine ←──────────────────┐
      ↓                                │
[5] Hypothesis Factory                 │
      ↓                                │
[6] Delivery                           │
      ↓                                │
   (Execution in Keitaro)              │
      ↓                                │
[7] Metrics Collection                 │
      ↓                                │
[8] Outcome Processing                 │
      ↓                                │
[9] Learning Loop ─────────────────────┘
      │
      └──→ Updates confidence/fatigue → affects [4]

[10] Buyer System — параллельный поток, использует [7], [9]
```

## Branching Convention

```
patch/<sphere>-<short-description>
```

Примеры:
- `patch/ingestion-add-validation`
- `patch/decision-engine-fix-trace`
- `patch/learning-update-formula`
