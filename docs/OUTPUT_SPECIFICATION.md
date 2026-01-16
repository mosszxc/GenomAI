# OUTPUT SPECIFICATION DOCUMENT
## GenomAI — Expected Results Reference

**Версия:** v1.0
**Дата:** 2026-01-13
**Назначение:** Reference для разработки — что система должна делать на выходе каждого процесса

---

## Как читать этот документ

Для каждого процесса указано:
- **Input** — что на входе
- **Expected Output** — что должно получиться
- **State Changes** — какие данные меняются в DB
- **Success Criteria** — как понять что процесс отработал правильно
- **Failure Modes** — ожидаемые ошибки

---

# ЧАСТЬ 1: WORKFLOWS (Temporal)

---

## 1.1 CreativePipelineWorkflow

**Триггер:** Webhook (новый креатив)
**Task Queue:** `creative-pipeline`

### Input
```python
CreativePipelineInput(
    creative_id: UUID,     # ID креатива в DB
    video_url: str,        # URL видео для транскрипции
    buyer_id: Optional[UUID]  # Optional buyer
)
```

### Expected Output
```python
CreativePipelineResult(
    success: bool,
    creative_id: UUID,
    idea_id: Optional[UUID],      # Created/found idea
    decision: Optional[str],       # APPROVE|REJECT|DEFER
    hypothesis_ids: List[UUID],    # Generated hypotheses
    delivered: bool,               # Telegram delivery status
    error: Optional[str]
)
```

### State Changes (DB)

| Таблица | Операция | Данные |
|---------|----------|--------|
| `creatives` | UPDATE | status → `transcribing` → `decomposed` → `completed` |
| `transcripts` | INSERT | transcript_id, content, created_at |
| `decomposed_creatives` | INSERT | Structured LLM output (14 fields) |
| `ideas` | INSERT/SELECT | canonical idea (dedupe by hash) |
| `decisions` | INSERT | decision_type, decision_epoch, passed/failed checks |
| `decision_traces` | INSERT | Full audit trail |
| `hypotheses` | INSERT (если APPROVE) | 3 hypotheses с status=null |
| `deliveries` | INSERT (если Telegram) | delivery status |

### Success Criteria

**Полный успех:**
```
✅ Транскрипт создан
✅ Декомпозиция валидна (14 required fields)
✅ Idea создана или найдена по hash
✅ Decision записан с trace
✅ Если APPROVE → hypotheses созданы
✅ Если buyer есть → Telegram delivery attempted
✅ creative.status = 'completed'
```

**Частичный успех (REJECT):**
```
✅ Decision = REJECT
✅ decision_trace содержит failed_check
✅ hypotheses НЕ созданы
✅ creative.status = 'rejected'
```

### Failure Modes

| Ошибка | Причина | Результат |
|--------|---------|-----------|
| `TRANSCRIPTION_FAILED` | AssemblyAI timeout/error | creative.status → `failed` |
| `DECOMPOSITION_INVALID` | LLM output не прошёл schema validation | creative.status → `decomposition_failed` |
| `IDEA_CREATION_FAILED` | DB error | creative.status → `failed` |

---

## 1.2 KeitaroPollerWorkflow

**Триггер:** Schedule (каждый 1 час)
**Task Queue:** `metrics`

### Input
```python
KeitaroPollerInput(
    batch_size: int = 50,           # Trackers per batch
    trigger_downstream: bool = True  # Chain to MetricsProcessing
)
```

### Expected Output
```python
KeitaroPollerResult(
    success: bool,
    trackers_polled: int,       # Total trackers checked
    metrics_updated: int,       # raw_metrics upserted
    snapshots_created: int,     # daily_metrics_snapshot created
    is_degraded: bool,          # Circuit breaker triggered
    errors: List[str]
)
```

### State Changes (DB)

| Таблица | Операция | Данные |
|---------|----------|--------|
| `raw_metrics_current` | UPSERT | tracker_id, date, metrics JSONB |
| `daily_metrics_snapshot` | INSERT | One per tracker per day |

### Success Criteria

```
✅ Все active trackers опрошены
✅ raw_metrics_current обновлены для каждого tracker
✅ daily_metrics_snapshot создан (если новый день)
✅ MetricsProcessingWorkflow запущен (если trigger_downstream=true)
✅ is_degraded = false
```

### Failure Modes

| Ошибка | Причина | Результат |
|--------|---------|-----------|
| `CIRCUIT_BREAKER_OPEN` | Keitaro API недоступен | is_degraded=true, downstream НЕ запускается |
| `PARTIAL_FAILURE` | Часть trackers failed | success=true, errors содержит failed tracker IDs |

### Invariants

```
• Каждый tracker имеет максимум 1 raw_metrics_current row (upsert)
• Каждый (tracker_id, date) имеет максимум 1 snapshot (idempotent)
• Circuit breaker check ПЕРЕД API calls
```

---

## 1.3 MetricsProcessingWorkflow

**Триггер:** Schedule (1 час) + Child от KeitaroPoller
**Task Queue:** `metrics`

### Input
```python
MetricsProcessingInput(
    batch_limit: int = 50,
    trigger_learning: bool = True
)
```

### Expected Output
```python
MetricsProcessingResult(
    success: bool,
    snapshots_processed: int,
    outcomes_created: int,
    outcomes_failed: int,
    learning_triggered: bool
)
```

### State Changes (DB)

| Таблица | Операция | Условие |
|---------|----------|---------|
| `daily_metrics_snapshot` | UPDATE | processed = true |
| `outcome_aggregates` | INSERT | window_id (D1/D3/D7/D7+), learning_applied=false |

### Success Criteria

```
✅ Все unprocessed snapshots обработаны (до batch_limit)
✅ outcome_aggregates созданы для каждого (decision_id, window_id)
✅ LearningLoopWorkflow запущен (если trigger_learning=true)
```

### Outcome Window Logic

```
days_since_decision = snapshot_date - decision_date

window_id = {
    0-1 days  → "D1"   (Early signal)
    2-3 days  → "D3"   (Short-term)
    4-7 days  → "D7"   (Week)
    8+ days   → "D7+"  (Long-term)
}
```

### Expected Outcome Structure

```python
OutcomeAggregate(
    id: UUID,
    creative_id: UUID,
    decision_id: UUID,
    window_id: str,           # D1|D3|D7|D7+
    window_start: date,
    window_end: date,
    impressions: int,
    clicks: int,
    conversions: int,
    spend: Decimal,
    revenue: Decimal,
    cpa: Optional[Decimal],   # spend/conversions (null if 0)
    origin_type: str,         # 'system'|'historical'
    learning_applied: bool,   # false initially
)
```

---

## 1.4 LearningLoopWorkflow

**Триггер:** Schedule (1 час) + Child от MetricsProcessing
**Task Queue:** `metrics`

### Input
```python
LearningLoopInput(
    batch_limit: int = 100,
    run_feature_monitoring: bool = True,
    run_module_learning: bool = True
)
```

### Expected Output
```python
LearningLoopResult(
    success: bool,
    outcomes_processed: int,
    confidence_updates: int,
    fatigue_updates: int,
    death_marks: int,
    component_learnings_updated: int,
    module_learnings_updated: int
)
```

### State Changes (DB)

| Таблица | Операция | Данные |
|---------|----------|--------|
| `outcome_aggregates` | UPDATE | learning_applied = true |
| `idea_confidence_versions` | INSERT | new version with updated confidence |
| `fatigue_state_versions` | INSERT | new version with updated fatigue |
| `ideas` | UPDATE | death_state (если условие) |
| `component_learnings` | UPSERT | win_count/loss_count/win_rate |
| `module_bank` | UPDATE | win_rate, avg_cpa, status |

### Success Criteria

```
✅ Все outcomes с learning_applied=false обработаны
✅ confidence_versions обновлены для каждой idea
✅ fatigue_versions обновлены
✅ Death conditions проверены
✅ Component learnings upserted
✅ Module bank stats updated
```

### Confidence Update Logic

```python
# Input
TARGET_CPA = 20.0
outcome = OutcomeAggregate(cpa=15.0)  # Good outcome

# Calculation
is_good = outcome.cpa < TARGET_CPA
delta = +0.1 if is_good else -0.15

# Time decay
days_old = (now - outcome.window_end).days
decay_factor = math.exp(-0.1 * days_old)

# New confidence
new_confidence = old_confidence + (delta * decay_factor)
new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp 0-1
```

### Death Condition Logic

```python
consecutive_failures = count_bad_outcomes(idea_id)

if consecutive_failures >= 3:
    mark_death(idea_id, death_type="soft_dead")

if consecutive_failures >= 5:
    mark_death(idea_id, death_type="hard_dead")
```

### Invariants

```
• outcome.learning_applied = true ТОЛЬКО после полной обработки
• confidence_versions append-only (версионирование)
• death_state immutable после hard_dead
```

---

## 1.5 DailyRecommendationWorkflow

**Триггер:** Schedule (09:00 UTC)
**Task Queue:** `metrics`

### Input
```python
DailyRecommendationInput(
    date: Optional[date] = today,
    dry_run: bool = False
)
```

### Expected Output
```python
DailyRecommendationResult(
    success: bool,
    buyers_processed: int,
    recommendations_generated: int,
    deliveries_attempted: int,
    deliveries_succeeded: int
)
```

### State Changes (DB)

| Таблица | Операция | Данные |
|---------|----------|--------|
| `recommendations` | INSERT | buyer_id, date, content, mode (exploit/explore) |
| `deliveries` | INSERT | recommendation_id, telegram_status |

### Success Criteria

```
✅ Все active buyers обработаны
✅ Recommendation создан для каждого buyer
✅ 90% recommendations в режиме exploitation
✅ 10% recommendations в режиме exploration
✅ Telegram delivery attempted для каждого
```

### Recommendation Structure

```python
Recommendation(
    id: UUID,
    buyer_id: UUID,
    date: date,
    mode: str,                    # 'exploitation'|'exploration'
    content: dict,                # Recommended components
    components: List[dict],       # hook, promise, proof selections
    confidence_score: float,      # Aggregated confidence
    created_at: timestamp
)
```

### Selection Logic

```python
# Exploitation (90%)
top_modules = get_top_performing_modules(
    buyer_geos=buyer.geos,
    buyer_verticals=buyer.verticals,
    order_by=['win_rate DESC', 'avg_cpa ASC'],
    limit=10
)

# Exploration (10%)
unexplored_modules = get_underexplored_modules(
    sample_size_threshold=5,
    limit=3
)
```

---

## 1.6 MaintenanceWorkflow

**Триггер:** Schedule (каждые 6 часов)
**Task Queue:** `metrics`

### Expected Output
```python
MaintenanceResult(
    success: bool,
    buyers_reset: int,              # Stale buyer states reset
    recommendations_expired: int,   # Old recommendations expired
    stuck_transcriptions: int,      # Marked as failed
    archived_creatives: int,        # Old failed archived
    integrity_issues: int,          # Data integrity problems
    hygiene_cleanup_count: int,     # Rows cleaned up
    retried_hypotheses: int         # Failed hypotheses retried
)
```

### State Changes (DB)

| Таблица | Операция | Условие |
|---------|----------|---------|
| `buyers` | UPDATE | state → 'idle' (если stuck > 6h) |
| `recommendations` | UPDATE | status → 'expired' (если > 7 days) |
| `creatives` | UPDATE | status → 'failed' (если stuck transcription > 10 min) |
| `creatives` | UPDATE | status → 'archived' (если failed > 7 days) |
| `hypotheses` | UPDATE | retry_count++ (если failed, < 3 retries) |

### Success Criteria

```
✅ Stale buyers reset
✅ Old recommendations expired
✅ Stuck transcriptions failed
✅ Old failed creatives archived
✅ Data integrity check passed (integrity_issues = 0)
✅ Hygiene cleanup completed
```

---

## 1.7 ModularHypothesisWorkflow

**Триггер:** Programmatic (от CreativePipeline или manual)
**Task Queue:** `creative-pipeline`

### Input
```python
ModularHypothesisInput(
    idea_id: UUID,
    decision_id: UUID,
    count: int = 3,              # Hypotheses to generate
    vertical: Optional[str],
    geo: Optional[str],
    buyer_id: Optional[UUID]
)
```

### Expected Output
```python
ModularHypothesisResult(
    success: bool,
    hypotheses_generated: int,
    hypotheses: List[HypothesisOutput],
    not_ready_reason: Optional[str]  # If prerequisites not met
)
```

### Readiness Check

```python
READINESS_REQUIREMENTS = {
    'hooks': 3,      # min active hooks
    'promises': 3,   # min active promises
    'proofs': 2,     # min active proofs
    'explored': 2    # min modules with sample_size >= 5
}
```

### State Changes (DB)

| Таблица | Операция | Данные |
|---------|----------|--------|
| `hypotheses` | INSERT | modular hypothesis с combination_id |
| `module_combinations_log` | INSERT | hook_id, promise_id, proof_id used |

### Success Criteria

```
✅ Readiness check passed
✅ Module combinations selected (90% top, 10% explore)
✅ LLM synthesis successful
✅ Hypotheses saved with review_status='pending_review'
```

### Hypothesis Structure

```python
ModularHypothesis(
    id: UUID,
    idea_id: UUID,
    decision_id: UUID,
    generation_type: 'modular',
    combination: {
        'hook_id': UUID,
        'hook_text': str,
        'promise_id': UUID,
        'promise_text': str,
        'proof_id': UUID,
        'proof_text': str
    },
    synthesized_text: str,       # LLM combined text
    review_status: str,          # 'pending_review'
    created_at: timestamp
)
```

---

# ЧАСТЬ 2: API ENDPOINTS

---

## 2.1 POST /api/decision/

### Request
```json
{
  "idea_id": "uuid"
}
```

### Expected Response (APPROVE)
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "idea_id": "uuid",
    "decision_type": "APPROVE",
    "decision_reason": "all_checks_passed",
    "passed_checks": ["schema_validity", "death_memory", "fatigue_constraint", "risk_budget"],
    "failed_checks": [],
    "timestamp": "2026-01-13T10:00:00.000000"
  },
  "decision_trace": {
    "id": "uuid",
    "decision_id": "uuid",
    "checks": [
      {"check_name": "schema_validity", "order": 1, "result": "PASSED", "details": {}},
      {"check_name": "death_memory", "order": 2, "result": "PASSED", "details": {}},
      {"check_name": "fatigue_constraint", "order": 3, "result": "PASSED", "details": {}},
      {"check_name": "risk_budget", "order": 4, "result": "PASSED", "details": {}}
    ],
    "result": "APPROVE"
  }
}
```

### Expected Response (REJECT)
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "decision_type": "REJECT",
    "decision_reason": "idea_dead",
    "passed_checks": ["schema_validity"],
    "failed_checks": ["death_memory"]
  },
  "decision_trace": {
    "checks": [
      {"check_name": "schema_validity", "order": 1, "result": "PASSED"},
      {"check_name": "death_memory", "order": 2, "result": "FAILED", "details": {"death_type": "hard_dead"}}
    ],
    "result": "REJECT"
  }
}
```

### Idempotency

```
✅ Повторный вызов для того же idea_id + epoch возвращает cached decision
✅ Новый epoch создаёт новое решение
```

### State Changes

| Таблица | Операция |
|---------|----------|
| `decisions` | INSERT (если новый) |
| `decision_traces` | INSERT |

---

## 2.2 POST /api/outcomes/aggregate

### Request
```json
{
  "snapshot_id": "uuid"
}
```

### Expected Response (Success)
```json
{
  "success": true,
  "outcome": {
    "id": "uuid",
    "creative_id": "uuid",
    "decision_id": "uuid",
    "window_id": "D1",
    "window_start": "2026-01-12",
    "window_end": "2026-01-13",
    "conversions": 10,
    "spend": 50.00,
    "cpa": 5.00,
    "origin_type": "system",
    "learning_applied": false
  },
  "learning_triggered": true
}
```

### Expected Response (No Idea)
```json
{
  "success": false,
  "error": {
    "code": "IDEA_NOT_FOUND",
    "message": "No idea found for tracker abc123"
  }
}
```

### Expected Response (No Approved Decision)
```json
{
  "success": false,
  "error": {
    "code": "NO_APPROVED_DECISION",
    "message": "No APPROVE decision found for idea xyz789"
  }
}
```

---

## 2.3 POST /learning/process

### Request
```json
{
  "idea_id": "uuid",
  "outcome_aggregate_id": "uuid"
}
```

### Expected Response
```json
{
  "success": true,
  "updated_ideas": 1,
  "confidence_delta": 0.1,
  "fatigue_delta": 1,
  "death_triggered": false
}
```

### State Changes

| Таблица | Операция |
|---------|----------|
| `idea_confidence_versions` | INSERT |
| `fatigue_state_versions` | INSERT |
| `outcome_aggregates` | UPDATE (learning_applied=true) |
| `ideas` | UPDATE (если death triggered) |

---

# ЧАСТЬ 3: DECISION ENGINE (4-Check Wall)

---

## 3.1 Check Order (FIXED)

```
1. schema_validity
2. death_memory
3. fatigue_constraint
4. risk_budget
```

**Invariant:** Порядок НЕ меняется. Первый failed check → REJECT/DEFER.

---

## 3.2 Check: schema_validity

### Input
```python
idea: dict  # Canonical idea payload
```

### Expected Output
```python
CheckResult(
    check_name: "schema_validity",
    result: "PASSED" | "FAILED",
    details: {
        "schema_version": "v1",
        "missing_fields": [],      # If failed
        "invalid_fields": []       # If failed
    }
)
```

### Logic
```python
def check_schema_validity(idea: dict) -> CheckResult:
    required_fields = [
        "angle_type", "core_belief", "promise_type", "emotion_primary",
        "emotion_intensity", "message_structure", "opening_type",
        "state_before", "state_after", "context_frame", "source_type",
        "risk_level", "horizon", "schema_version"
    ]

    missing = [f for f in required_fields if f not in idea]
    if missing:
        return CheckResult("FAILED", {"missing_fields": missing})

    # Enum validation
    invalid = validate_enums(idea)
    if invalid:
        return CheckResult("FAILED", {"invalid_fields": invalid})

    return CheckResult("PASSED")
```

---

## 3.3 Check: death_memory

### Input
```python
idea_id: UUID
```

### Expected Output
```python
CheckResult(
    check_name: "death_memory",
    result: "PASSED" | "FAILED",
    details: {
        "death_state": null | "soft_dead" | "hard_dead",
        "death_reason": str
    }
)
```

### Logic
```python
def check_death_memory(idea_id: UUID) -> CheckResult:
    idea = get_idea(idea_id)

    if idea.death_state is not None:
        return CheckResult("FAILED", {
            "death_state": idea.death_state,
            "death_reason": idea.death_reason
        })

    return CheckResult("PASSED")
```

---

## 3.4 Check: fatigue_constraint

### Input
```python
idea_id: UUID
fatigue_state: FatigueState
```

### Expected Output
```python
CheckResult(
    check_name: "fatigue_constraint",
    result: "PASSED" | "FAILED",
    details: {
        "fatigue_level": float,
        "threshold": float,
        "exceeded": bool
    }
)
```

### Logic
```python
FATIGUE_THRESHOLD = 0.8

def check_fatigue_constraint(idea_id: UUID) -> CheckResult:
    fatigue = get_latest_fatigue(idea_id)

    if fatigue.level >= FATIGUE_THRESHOLD:
        return CheckResult("FAILED", {
            "fatigue_level": fatigue.level,
            "threshold": FATIGUE_THRESHOLD,
            "exceeded": True
        })

    return CheckResult("PASSED")
```

---

## 3.5 Check: risk_budget

### Input
```python
idea: dict
system_state: SystemState
```

### Expected Output
```python
CheckResult(
    check_name: "risk_budget",
    result: "PASSED" | "FAILED" | "DEFER",
    details: {
        "risk_level": "low" | "medium" | "high",
        "available_budget": float,
        "required_budget": float
    }
)
```

### Logic
```python
RISK_BUDGETS = {"low": 100, "medium": 50, "high": 20}

def check_risk_budget(idea: dict, system_state: SystemState) -> CheckResult:
    risk_level = idea["risk_level"]
    required = RISK_BUDGETS[risk_level]
    available = system_state.available_risk_budget

    if available < required:
        return CheckResult("DEFER", {  # DEFER, not REJECT
            "risk_level": risk_level,
            "available_budget": available,
            "required_budget": required
        })

    return CheckResult("PASSED")
```

---

# ЧАСТЬ 4: LEARNING LOOP MECHANICS

---

## 4.1 Confidence Update

### Input
```python
outcome: OutcomeAggregate
idea: Idea
```

### Expected Output
```python
ConfidenceUpdate(
    idea_id: UUID,
    old_confidence: float,
    new_confidence: float,
    delta: float,
    decay_factor: float,
    version: int
)
```

### Formula
```python
TARGET_CPA = 20.0
DELTA_GOOD = +0.1
DELTA_BAD = -0.15

is_good = outcome.cpa < TARGET_CPA
base_delta = DELTA_GOOD if is_good else DELTA_BAD

# Time decay (exponential)
days_old = (now - outcome.window_end).days
decay_factor = math.exp(-0.1 * days_old)

# Final delta
delta = base_delta * decay_factor

# New confidence (clamped 0-1)
new_confidence = max(0.0, min(1.0, old_confidence + delta))
```

---

## 4.2 Fatigue Update

### Expected Output
```python
FatigueUpdate(
    idea_id: UUID,
    old_fatigue: float,
    new_fatigue: float,
    delta: float,
    version: int
)
```

### Formula
```python
MAX_FATIGUE = 1000.0

# Fatigue increases with usage
if idea_used_in_hypothesis_today:
    delta = +1.0
else:
    # Natural decay
    delta = -0.1

new_fatigue = max(0.0, min(MAX_FATIGUE, old_fatigue + delta))
```

---

## 4.3 Death Conditions

### Expected Output
```python
DeathCheck(
    idea_id: UUID,
    consecutive_failures: int,
    death_triggered: bool,
    death_type: Optional[str]  # "soft_dead" | "hard_dead"
)
```

### Logic
```python
SOFT_DEAD_THRESHOLD = 3
HARD_DEAD_THRESHOLD = 5

consecutive_failures = count_consecutive_bad_outcomes(idea_id)

if consecutive_failures >= HARD_DEAD_THRESHOLD:
    mark_dead(idea_id, "hard_dead")
elif consecutive_failures >= SOFT_DEAD_THRESHOLD:
    mark_dead(idea_id, "soft_dead")
```

---

## 4.4 Component Learning

### Expected Output
```python
ComponentLearningUpdate(
    component_type: str,      # "hook_mechanism", "angle_type", etc.
    component_value: str,     # "confession", "pain", etc.
    old_win_rate: float,
    new_win_rate: float,
    win_count: int,
    loss_count: int
)
```

### Logic
```python
def update_component_learning(outcome: OutcomeAggregate, idea: Idea):
    is_win = outcome.cpa < TARGET_CPA

    components = extract_components(idea)
    # e.g., {"hook_mechanism": "confession", "angle_type": "pain", ...}

    for comp_type, comp_value in components.items():
        learning = get_or_create_learning(comp_type, comp_value)

        if is_win:
            learning.win_count += 1
        else:
            learning.loss_count += 1

        learning.win_rate = learning.win_count / (learning.win_count + learning.loss_count)
        learning.updated_at = now()

        upsert(learning)
```

---

# ЧАСТЬ 5: MODULE SYSTEM (Phase 3)

---

## 5.1 Module Bank Structure

### Expected Module
```python
Module(
    id: UUID,
    module_type: str,        # 7 types
    module_text: str,        # Actual content
    module_key: str,         # SHA256 hash (dedup)

    # Performance metrics
    win_rate: float,         # wins / (wins + losses)
    avg_cpa: float,          # Average CPA when used
    sample_size: int,        # Total usages
    total_conversions: int,  # Total conversions

    # Status lifecycle
    status: str,             # 'emerging' → 'active' → 'fatigued' → 'dead'

    created_at: timestamp,
    updated_at: timestamp
)
```

### Module Types
```python
MODULE_TYPES = [
    "hook_mechanism",      # How to capture attention
    "angle_type",          # Approach/perspective
    "message_structure",   # Message organization
    "ump_type",            # Unique mechanism of promise
    "promise_type",        # Type of promise
    "proof_type",          # Evidence type
    "cta_style"            # Call-to-action style
]
```

---

## 5.2 Module Selection

### Input
```python
SelectionInput(
    buyer_geos: List[str],
    buyer_verticals: List[str],
    count: int = 10
)
```

### Expected Output
```python
SelectionOutput(
    exploitation_modules: List[Module],   # 90% of count
    exploration_modules: List[Module],    # 10% of count
)
```

### Selection Logic
```python
# Exploitation (90%)
exploitation = query("""
    SELECT * FROM module_bank
    WHERE status = 'active'
    ORDER BY win_rate DESC, avg_cpa ASC
    LIMIT {count * 0.9}
""")

# Exploration (10%)
exploration = query("""
    SELECT * FROM module_bank
    WHERE sample_size < 5
    ORDER BY RANDOM()
    LIMIT {count * 0.1}
""")
```

---

## 5.3 Module Status Lifecycle

```
emerging → active → fatigued → dead
   ↑         ↑         ↑
   │         │         │
   │         │         └── fatigue_score > 0.8
   │         │
   │         └── sample_size >= 10 AND win_rate >= 0.3
   │
   └── newly created module
```

### Transition Rules
```python
def update_module_status(module: Module):
    if module.status == 'emerging':
        if module.sample_size >= 10 and module.win_rate >= 0.3:
            module.status = 'active'

    elif module.status == 'active':
        if module.fatigue_score > 0.8:
            module.status = 'fatigued'

    elif module.status == 'fatigued':
        consecutive_bad = count_consecutive_bad(module.id)
        if consecutive_bad >= 5:
            module.status = 'dead'
```

---

# ЧАСТЬ 6: INVARIANTS (Неизменяемые правила)

---

## 6.1 Data Invariants

```
1. decisions: UNIQUE(idea_id, decision_epoch)
   → Одно решение на idea + epoch

2. outcome_aggregates: UNIQUE(decision_id, window_id)
   → Одна запись на decision + window

3. idea_confidence_versions: Append-only
   → Версии только добавляются, не изменяются

4. decision_traces: Immutable
   → После создания не меняется

5. module_bank.module_key: UNIQUE
   → Дедупликация по hash
```

---

## 6.2 Process Invariants

```
1. Decision Engine order: schema → death → fatigue → budget
   → Порядок проверок фиксирован

2. Learning applied: outcome.learning_applied = true ТОЛЬКО после processing
   → Атомарность обучения

3. Death state: hard_dead is terminal
   → После hard_dead idea не воскресает

4. Temporal determinism: workflow.now() вместо datetime.utcnow()
   → Детерминированные replays
```

---

## 6.3 Business Invariants

```
1. Market = Truth
   → Все решения основаны на CPA из Keitaro, не на мнениях

2. CPA_window = единственная метрика успеха
   → CTR, CVR, ROAS только для observability

3. 90/10 Split
   → Exploitation 90%, Exploration 10% в recommendations и module selection

4. LLM = Parser only
   → LLM только для parsing видео → structured data, не для решений
```

---

# ЧАСТЬ 7: VERIFICATION CHECKLIST

---

## How to Verify Each Process

### CreativePipelineWorkflow
```bash
# 1. Trigger workflow
curl -X POST localhost:10000/api/creative/register \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"video_url": "https://...", "buyer_id": "uuid"}'

# 2. Check creative status
SELECT status FROM genomai.creatives WHERE id = '<creative_id>';
# Expected: 'completed' или 'rejected'

# 3. Check decision created
SELECT * FROM genomai.decisions WHERE idea_id = '<idea_id>';
# Expected: 1 row with decision_type

# 4. Check trace
SELECT * FROM genomai.decision_traces WHERE decision_id = '<decision_id>';
# Expected: 4 checks with PASSED/FAILED
```

### LearningLoopWorkflow
```bash
# 1. Trigger manually
python -m temporal.schedules trigger learning-loop

# 2. Check outcomes processed
SELECT COUNT(*) FROM genomai.outcome_aggregates
WHERE learning_applied = false;
# Expected: 0 (all processed)

# 3. Check confidence versions
SELECT * FROM genomai.idea_confidence_versions
ORDER BY created_at DESC LIMIT 5;
# Expected: Recent versions with deltas
```

### Module Selection
```bash
# 1. Check module distribution
SELECT status, COUNT(*) FROM genomai.module_bank GROUP BY status;
# Expected: Mix of emerging, active, fatigued

# 2. Verify 90/10 split in recommendations
SELECT mode, COUNT(*) FROM genomai.recommendations
WHERE date = CURRENT_DATE GROUP BY mode;
# Expected: ~90% exploitation, ~10% exploration
```

---

# SUMMARY

Этот документ описывает **что система должна делать на выходе** для каждого процесса:

| Процесс | Ключевой Output |
|---------|-----------------|
| CreativePipeline | idea + decision + hypotheses (если APPROVE) |
| KeitaroPoller | raw_metrics + snapshots + trigger downstream |
| MetricsProcessing | outcome_aggregates с window_id |
| LearningLoop | confidence + fatigue updates + death checks |
| DailyRecommendation | Telegram delivery с 90/10 split |
| ModularHypothesis | 3 hypotheses из module combinations |
| Decision Engine | decision + full trace (4 checks) |

**Использование:** При разработке сверяться с этим документом для понимания expected behavior.
