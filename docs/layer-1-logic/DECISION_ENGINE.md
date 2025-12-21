# Decision Engine Specification
## GenomAI — Deterministic Decision Core

**Version:** v1.1  
**Status:** CANONICAL / CORE SYSTEM  
**Priority:** Highest

---

## 1. Purpose

This document specifies the **Decision Engine** — the deterministic core of the GenomAI system.

The Decision Engine:
- decides which Ideas are allowed for execution
- enforces architectural constraints
- protects the system from repetition, fatigue, and false novelty
- ensures reproducibility and auditability of decisions

The Decision Engine **does not generate ideas**, texts, or creatives.

**The Decision Engine uses only field values, never interpretations, reasons, or explanations.**

---

## 2. Scope and Authority

The Decision Engine is the **only component** allowed to:
- APPROVE ideas
- REJECT ideas
- DEFER ideas
- APPROVE ideas with constraints

Any bypass of the Decision Engine is considered an **architectural violation**.

---

## 3. Determinism Requirement

Given:
- identical Idea (schema-valid)
- identical system state
- identical historical memory

The Decision Engine **must always produce the same decision**.

Non-deterministic behavior is forbidden.

---

## 4. Inputs

### 4.1 Mandatory Inputs

- Idea (canonical schema, validated)
- System State
- Fatigue State
- Death Memory
- Historical Outcomes (aggregated)
- Risk Budget
- Current Horizon Context

If any mandatory input is missing — decision is **REJECTED**.

### 4.2 ML Signal Discretization (Critical)

**Decision Engine works ONLY with bucket values, NOT raw float scores.**

ML provides raw signals (similarity_score, novelty_score, confidence_weight as floats), but Decision Engine receives only discretized buckets:

- `novelty_bucket`: `low` | `medium` | `high`
- `similarity_bucket`: `low` | `medium` | `high`
- `confidence_bucket`: `weak` | `normal` | `strong`

**Why:**
- Keeps Decision Engine deterministic and explainable
- Prevents hidden logic from migrating into ML layer
- ML remains fully advisory without hidden influence
- Decision rules operate on discrete categories, not continuous values

**Conversion rules:**
- ML → Bucket conversion is explicit and versioned
- Thresholds for bucket assignment are fixed and documented
- Bucket assignment must be reproducible (same float → same bucket)

**Forbidden:**
- Using raw float scores directly in Decision Engine checks
- Dynamic threshold adjustment based on ML performance
- Any logic that depends on exact float values

---

## 5. Outputs

Each decision produces:

- decision_type
- decision_reason
- passed_checks
- failed_checks
- constraints (if any)
- timestamp
- system_state_snapshot

All outputs are logged as a **Decision entity**.

---

## 6. Decision Types

```text
APPROVE
REJECT
ALLOW_WITH_CONSTRAINTS
DEFER
```

---

## 7. Evaluation Pipeline (Fixed Order)

The Decision Engine evaluates Ideas using a strict, fixed-order pipeline.
No check may be skipped or reordered.

### CHECK 1 — Schema Validity

**Purpose:**  
Ensure Idea is structurally valid.

**Rule:**  
If Idea does not fully conform to canonical schema → REJECT.

---

### CHECK 2 — Death Memory

**Purpose:**  
Prevent repetition of dead ideas.

**Rule:**  
If Idea or its cluster is marked as DEAD → REJECT.

**Exception:**  
Allowed only via Human Override.

---

### CHECK 3 — Fatigue Constraint

**Purpose:**  
Prevent audience burnout.

**Rule:**  
If `fatigue_level ≥ angle` AND `novelty_bucket = low` → REJECT.

**Notes:**
- Skin fatigue may allow message mutation (форма подачи, тон, стиль речи в транскрипте).
- Angle fatigue forbids all variants within cluster.
- Fatigue levels: skin, message, angle, transition, tension, context, exhausted
- Tension fatigue ≠ idea death (tension can mutate without killing idea)
- **Система работает только с транскриптом видео** — визуалы, изображения, primary/description не учитываются.

---

### CHECK 4 — Pseudo-Novelty Detection

**Purpose:**  
Reject fake innovation.

**Rule:**  
If `novelty_bucket = low` AND `similarity_bucket = high` → REJECT.

**Note:**  
State Transition (state_before → state_after) is used for pseudo-novelty detection:
- Different angle/emotion with same transition → considered repetition
- Transition is checked against historical transitions, not just similarity scores

---

### CHECK 5 — Context Validity

**Purpose:**  
Ensure idea fits current context.

**Rule:**  
If Idea context mismatches active system context → DEFER (NOT REJECT).

**Note:**  
Cultural Context (context_frame) is used here:
- context_frame mismatch → DEFER (allows future transfer when context changes)
- This is about trust frame and legitimacy, not audience/segment/style

**Examples:**
- wrong geo
- wrong placement
- wrong vertical
- incompatible context_frame (institutional vs anti_authority)

---

### CHECK 6 — Risk Budget

**Purpose:**  
Control exposure.

**Rule:**  
If `risk_level` exceeds available risk budget → DEFER or REJECT.

**High-risk ideas require:**
- explicit allocation
- capped budget
- short horizon

---

### CHECK 7 — Horizon Compatibility

**Purpose:**  
Prevent premature conclusions.

**Rule:**  
If Idea horizon conflicts with current evaluation window → DEFER.

---

### CHECK 8 — Diversity / Saturation Control

**Purpose:**  
Avoid over-concentration on one cluster.

**Rule:**  
If cluster exposure exceeds diversity limit → DEFER.

---

### CHECK 9 — Epistemic Shock Trigger

**Purpose:**  
Prevent confirmation lock-in.

**Rule:**  
If `confidence_bucket = strong` AND shock cooldown expired AND shock budget available → FORCE SHOCK SLOT.

**Rate Limiting:**
- Maximum frequency: not more than 1 shock per N decisions (e.g., 1 per 50–100 decisions)
- Minimum cooldown: mandatory interval between shock decisions (e.g., 24 hours)
- Budget cap: dedicated shock budget (e.g., max 5–10% of total budget)

**Shock ideas bypass CHECK 4 but remain subject to:**
- Death Memory
- Risk caps
- Budget caps
- Rate limiting rules above

---

## 8. Decision Resolution Logic

After all checks:

- If all checks PASSED → APPROVE
- If any HARD check FAILED → REJECT
- If SOFT constraints violated → DEFER
- If constraints required → ALLOW_WITH_CONSTRAINTS

---

## 9. Constraints Model

Constraints may include:
- max_budget
- max_duration
- limited variants
- isolated execution pool

Constraints are mandatory and enforced downstream.

---

## 10. Decision Trace (Mandatory)

Each decision must record:
- ordered list of checks
- pass/fail result per check
- decision outcome
- system state snapshot
- state transition (state_before → state_after) for analysis
- context_frame for diagnostic purposes
- tension_type (if available) for failure analysis

No decision is valid without trace.

### 10.1 Minimum Explainability Contract

Every decision trace MUST include these fields for explainability:

- `decision_type` — APPROVE/REJECT/DEFER/ALLOW_WITH_CONSTRAINTS
- `failed_check` — first check that failed (if any)
- `dominant_constraint` — primary constraint that limited the decision
- `cluster_at_decision` — active_cluster_id at time of decision
- `horizon` — evaluation horizon (T1/T2/T3)
- `system_state` — current system state (Exploit/Explore/Shock/etc.)

**Result:** Any decision can be explained in 6–7 lines. Debugging is possible without ML.

---

## 11. Use of State Transition, Narrative Tension, and Cultural Context

### 11.1 State Transition Usage

State Transition (state_before → state_after):
- **Core fields** of Idea schema (mandatory part of canonical Idea)
- **Architectural role:**
  - Participates directly in: clustering, fatigue, death memory, learning loop
  - Used in Decision Engine **indirectly** (through fatigue/death/diversity), **NOT as separate if-check**
  - Used in **CHECK 4 (Pseudo-Novelty Detection)** to identify repetition (via similarity/clustering)
- **Why core:**
  - This is the sold transformation itself, not the presentation format
  - Invariant of the idea (doesn't change between implementations)
  - Decisions at transition level: pseudo-novelty, repetition, death, market transfer

### 11.2 Narrative Tension Usage

Narrative Tension (tension_type):
- **Derived/advisory signal** (NOT core field)
- **Why NOT core:**
  - Tension changes between Hypothesis
  - Can be different for the same Idea
  - Doesn't define what is sold, only how attention is held
  - Making it core would violate "Idea ≠ implementation" principle
- **Architectural role:**
  - **NOT used in:** approve/reject, risk budget, novelty checks
  - **Used ONLY for:**
    - Analysis of failure reasons (transition relevant but tension failed → attention problem)
    - Correct fatigue attribution (tension_type exhausted, not angle/transition)
    - Hypothesis Factory mutations (change tension without changing idea)
    - Learning loop (as cause of decay, not as policy)
- **Diagnostic sensor, not a decision lever**

### 11.3 Cultural Context Usage

Cultural Context (context_frame):
- **Core field** of Idea schema (part of Idea identity, not decoration)
- **Why core:**
  - Doesn't change from text/implementation
  - Defines legitimacy of promise
  - Affects scaling and transfer
  - Two ideas with same transition but different context_frame = different ideas from market perspective
- **Important limitation:**
  - context_frame is **NOT** audience
  - context_frame is **NOT** segment
  - context_frame is **NOT** creative style
  - context_frame **IS** trust frame and acceptable language
- **Architectural role:**
  - **NOT used** directly in approve/reject
  - Used in **CHECK 5 (Context Validity)** for DEFER (not REJECT)
  - Used **ONLY for:**
    - Context validity (DEFER, not REJECT)
    - Correct scaling decisions
    - Explaining strange metrics (good CTR, poor conversion → context mismatch)
    - Fatigue at frame level, not idea level

**Important:** These fields enhance analysis and diagnostics but do not add new decision logic.

---

## 12. Forbidden Behaviors

The Decision Engine must never:
- use LLM outputs directly
- generate text or creatives
- modify schema
- learn weights autonomously
- override its own rules
- use tension_type as decision criteria
- reject ideas based solely on context_frame

---

## 13. Error Handling

- Missing inputs → REJECT
- Invalid schema → REJECT
- Inconsistent memory → DEFER
- Unknown state → FAIL SAFE (REJECT)

Fail-safe behavior always favors rejection over risk.

---

## 14. Change Management

Any change to:
- check order
- check logic
- thresholds
- decision types
- use of state transition, tension, or context

Requires:
- version bump
- explicit approval
- migration notes

---

## 15. MVP Success Definition

**❗ КРИТИЧЕСКОЕ ПРАВИЛО — MVP SUCCESS METRIC:**

**В рамках MVP единственной метрикой успешности является CPA_window, рассчитанный по агрегированному временному окну и применимый исключительно к System Outcome.**

**Decision Engine не читает CTR / CVR / ROAS.**

**Decision опирается на:**
- confidence (производная от CPA_window через Learning Loop)
- fatigue (динамика CPA_window через Learning Loop)

**Запрещено:**
- ❌ Использование CTR, CVR, ROAS, Early CPA, Engagement metrics для решений
- ❌ Любые формулировки про "успех" вне CPA_window
- ❌ Real-time показатели как метрика успешности

**Допустимо:**
- ✅ CTR, CVR, ROAS как observability (логирование, ручной просмотр)
- ✅ CPA_window как единственная метрика для learning и decision

---

## 16. Final Rule

**The Decision Engine is the law of the system.**  
**If another component disagrees with the Decision Engine,  
the other component is wrong.**

