# Modular Creative System - Architecture Plan

**Status:** Ready for Implementation
**Created:** 2026-01-11
**Problem:** Exploitation without Exploration

## Problem Statement

Текущая система имеет проблему **Exploitation without Exploration**:

```
Креатив A → Decompose → Idea (hash = A) → DE → 3 "вариации" A', A'', A'''
```

Система только переформулирует входящие креативы, не генерирует новые комбинации модулей.

## Solution Overview

```
                    ┌─────────────────┐
                    │   Hook Bank     │ ← win_rate сортировка
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Promise A│       │ Promise B│       │ Promise C│
   └────┬─────┘       └────┬─────┘       └────┬─────┘
        │                  │                  │
        ▼                  ▼                  ▼
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Proof 1  │       │ Proof 2  │       │ Proof 3  │
   └──────────┘       └──────────┘       └──────────┘
```

**Результат:** Комбинаторная генерация гипотез из модулей разных креативов.

---

## Module Types

| Module | Задача | Canonical Schema v2 Fields |
|--------|--------|---------------------------|
| **Hook** | Остановить скролл (3 сек) | `hooks[]`, `hook_mechanism`, `hook_stopping_power`, `opening_type` |
| **Promise** | Что человек получит | `promise_type`, `core_belief`, `state_before`, `state_after`, `ump_type`, `ums_type` |
| **Proof** | Почему верить | `proof_type`, `proof_source`, `social_proof_pattern`, `story_type` |

---

## Phase 1: Schema (Migration 037)

### module_bank

```sql
CREATE TABLE IF NOT EXISTS genomai.module_bank (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Module identity
    module_type TEXT NOT NULL CHECK (module_type IN ('hook', 'promise', 'proof')),
    module_key TEXT NOT NULL,  -- SHA256 hash for deduplication

    -- Content
    content JSONB NOT NULL,    -- Extracted fields from decomposed payload
    text_content TEXT,         -- Human-readable text (for hooks)

    -- Source tracking
    source_creative_id UUID REFERENCES genomai.creatives(id),
    source_decomposed_id UUID REFERENCES genomai.decomposed_creatives(id),

    -- Context
    vertical TEXT,
    geo TEXT,
    avatar_id UUID REFERENCES genomai.avatars(id),

    -- Metrics (same pattern as component_learnings)
    sample_size INT DEFAULT 0,
    win_count INT DEFAULT 0,
    loss_count INT DEFAULT 0,
    total_spend NUMERIC DEFAULT 0,
    total_revenue NUMERIC DEFAULT 0,

    -- Generated columns
    win_rate NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0 END
    ) STORED,
    avg_roi NUMERIC GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    ) STORED,

    -- State
    status TEXT DEFAULT 'emerging' CHECK (status IN ('active', 'emerging', 'fatigued', 'dead')),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (module_type, module_key)
);

CREATE INDEX idx_module_bank_type_win_rate
ON genomai.module_bank(module_type, win_rate DESC)
WHERE status = 'active';
```

### module_compatibility

```sql
CREATE TABLE IF NOT EXISTS genomai.module_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    module_a_id UUID NOT NULL REFERENCES genomai.module_bank(id),
    module_b_id UUID NOT NULL REFERENCES genomai.module_bank(id),

    sample_size INT DEFAULT 0,
    win_count INT DEFAULT 0,

    compatibility_score NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0.5 END
    ) STORED,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (module_a_id, module_b_id),
    CHECK (module_a_id < module_b_id)
);
```

### hypotheses extension

```sql
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS hook_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS promise_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS proof_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS generation_mode TEXT DEFAULT 'reformulation'
    CHECK (generation_mode IN ('reformulation', 'modular'));
```

---

## Phase 2: Module Extraction

### Cold Start Strategy

Новые модули решают проблему "холодного старта" двумя способами:

**1. Наследование от родителя**
При создании модуль получает метрики от креатива-источника.

**2. Exploration квота (10%)**
При генерации гипотез:
- 90% — модули с лучшим win_rate
- 10% — модули с sample_size < 5

### New Activity

```python
# temporal/activities/module_extraction.py

MODULE_FIELDS = {
    'hook': {
        'fields': ['hooks', 'hook_mechanism', 'hook_stopping_power', 'opening_type'],
        'key_fields': ['hook_mechanism', 'opening_type'],
    },
    'promise': {
        'fields': ['promise_type', 'core_belief', 'state_before', 'state_after', 'ump_type', 'ums_type'],
        'key_fields': ['promise_type', 'core_belief', 'state_before', 'state_after'],
    },
    'proof': {
        'fields': ['proof_type', 'proof_source', 'social_proof_pattern', 'story_type'],
        'key_fields': ['proof_type', 'proof_source'],
    },
}

@activity.defn
async def extract_modules_from_decomposition(
    creative_id: str,
    decomposed_id: str,
    payload: dict,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> dict:
    """
    Extract Hook, Promise, Proof modules from decomposed payload.
    Upsert into module_bank with deduplication by module_key hash.

    Cold Start: New modules inherit metrics from source creative.

    Returns: {"hook_id": uuid, "promise_id": uuid, "proof_id": uuid}
    """
    # 1. Get parent creative metrics
    creative_metrics = await get_creative_metrics(creative_id)

    # 2. Extract modules with inherited metrics
    for module_type in ['hook', 'promise', 'proof']:
        module = extract_module(payload, module_type)
        module.sample_size = creative_metrics.sample_size
        module.win_count = creative_metrics.win_count
        module.total_spend = creative_metrics.total_spend
        module.total_revenue = creative_metrics.total_revenue
        await upsert_module(module)
```

### Integration Point

Add to `CreativePipelineWorkflow` after Step 3 (decomposition):

```python
# Step 3.5: Extract modules
module_result = await workflow.execute_activity(
    extract_modules_from_decomposition,
    input.creative_id,
    decomposed["id"],
    decomposition_payload,
    creative.get("target_vertical"),
    creative.get("target_geo"),
)
```

---

## Phase 3: Prioritized Generator

### Compatibility Bootstrap

Все пары модулей стартуют с `compatibility_score = 0.5` (нейтрально).
Score обновляется только по реальным результатам тестов.

### Algorithm

```
1. SELECT hooks:
   - 90%: WHERE status='active' ORDER BY win_rate DESC
   - 10%: WHERE sample_size < 5 (exploration)
   ↓
2. For each hook: SELECT promises WHERE compatible(hook)
   - Same 90/10 split
   ↓
3. For each (hook, promise): SELECT proofs WHERE compatible(both)
   - Same 90/10 split
   ↓
4. Generate top 3 combinations by combined score
   ↓
5. LLM synthesizes coherent ad text from modules
```

### New Workflow

```python
# temporal/workflows/modular_hypothesis.py

@workflow.defn
class ModularHypothesisWorkflow:
    """
    Generate hypotheses by combining top-performing modules.
    Triggered when module_bank has enough data (sample_size >= 5).
    """

    async def run(self, input: ModularHypothesisInput) -> dict:
        # 1. Check if enough modules exist
        # 2. Select top hooks
        # 3. For each hook, select compatible promises
        # 4. For each pair, select compatible proofs
        # 5. Generate combinations
        # 6. LLM synthesis
        # 7. Save hypotheses with module references
```

### Decision Logic

```python
def should_use_modular_generation(geo: str, vertical: str) -> bool:
    """
    Use modular generation when:
    - At least 3 active hooks exist
    - At least 3 active promises exist
    - At least 2 modules have sample_size >= 5
    """
```

---

## Phase 4: Learning Integration

### Update module_bank on Outcome

Add to `LearningLoopWorkflow`:

```python
await workflow.execute_activity(
    update_module_learnings,
    creative_id=creative_id,
    hypothesis_id=hypothesis_id,
    cpa=cpa,
    spend=spend,
    revenue=revenue,
    was_win=was_win,
)
```

### Update Compatibility on Test

```python
@activity.defn
async def update_module_compatibility(
    hook_id: str,
    promise_id: str,
    proof_id: str,
    was_win: bool,
) -> None:
    """
    Update compatibility scores for module pairs used together.
    """
```

---

## Phase 5: Human Review

Modular-гипотезы проходят проверку человеком перед запуском.

### Workflow

```
1. LLM синтезирует текст из модулей
   ↓
2. Гипотеза сохраняется: status = 'pending_review'
   ↓
3. Человек видит в Telegram/UI
   ↓
4a. Апрув → status = 'approved' → DE проверяет → запуск
4b. Реджект → status = 'rejected' → не запускается
```

### Schema (добавить в migration 037)

```sql
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'auto_approved'
    CHECK (review_status IN ('pending_review', 'approved', 'rejected', 'auto_approved'));

-- Modular гипотезы: pending_review (требуют проверки)
-- Reformulation гипотезы: auto_approved (как сейчас)
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/migrations/037_module_bank.sql` | Schema |
| `temporal/activities/module_extraction.py` | Extract modules |
| `temporal/activities/module_learning.py` | Update learnings |
| `temporal/activities/modular_generation.py` | Generate from modules |
| `temporal/workflows/modular_hypothesis.py` | Orchestration |
| `src/services/module_selector.py` | Prioritized selection |

## Files to Modify

| File | Change |
|------|--------|
| `temporal/workflows/creative_pipeline.py` | Add extraction step |
| `temporal/activities/learning.py` | Add module learning |
| `temporal/worker.py` | Register new workflows |
| `docs/TEMPORAL_WORKFLOWS.md` | Document |
| `docs/SCHEMA_REFERENCE.md` | Add tables |

---

## Implementation Order

1. **Migration 037** — создать таблицы (включая review_status)
2. **module_extraction.py** — извлечение модулей с наследованием метрик
3. **Интеграция в CreativePipeline** — автоматическое извлечение
4. **module_learning.py** — обновление метрик
5. **modular_generation.py** — генерация гипотез (90/10 split)
6. **ModularHypothesisWorkflow** — оркестрация
7. **Human Review UI** — Telegram команды для approve/reject
8. **Интеграция в LearningLoop** — обновление compatibility

---

## Verification

### Unit Tests
- Module extraction from payload
- Module key hashing
- Prioritized selection
- Compatibility calculation

### Integration Test
```bash
# 1. Create test creative
python -m temporal.schedules trigger creative-pipeline --input '{"creative_id": "test"}'

# 2. Verify modules extracted
SELECT * FROM genomai.module_bank ORDER BY created_at DESC LIMIT 5;

# 3. Trigger modular generation
SELECT * FROM genomai.hypotheses WHERE generation_mode = 'modular';
```

### E2E Check
```sql
-- Modules with win_rate
SELECT module_type, COUNT(*), AVG(win_rate)
FROM genomai.module_bank
WHERE status = 'active'
GROUP BY module_type;

-- Compatibility scores
SELECT COUNT(*), AVG(compatibility_score)
FROM genomai.module_compatibility
WHERE sample_size >= 3;
```
