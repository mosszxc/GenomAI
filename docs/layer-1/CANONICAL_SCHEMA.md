# Canonical Schema Specification
## GenomAI — Canonical Data Model

**Version:** v1.2  
**Status:** CANONICAL / SINGLE SOURCE OF TRUTH

---

## 1. Purpose

This document defines the **canonical data schema** for the GenomAI system.

The schema:
- defines what data exists in the system
- defines what data is valid
- is mandatory for:
  - Decision Engine
  - ML / Similarity / Fatigue
  - LLM Decomposition
  - Storage
  - Learning Loop

**If a field is not defined in this schema — it does not exist.**

---

## 2. Global Schema Rules

1. Schema-first architecture
2. All fields must be strictly typed
3. Prefer enums over free text
4. No temporary or experimental fields
5. LLM output must strictly conform to schema
6. Any schema violation results in rejection
7. Silent coercion is forbidden

---

## 3. Core Entity — Idea

### 3.1 Definition

An **Idea** represents a semantic hypothesis tested against the market.

An Idea:
- is the primary decision object
- is tracked over time
- participates in fatigue and death logic
- is independent from execution format

An Idea is **not** a text, creative, or hypothesis.

---

### 3.2 Idea Schema

```json
{
  "idea_id": "uuid",
  "active_cluster_id": "uuid",
  
  // Note: active_cluster_id is current state (may change over time)
  // Historical cluster_id is stored in Decision.cluster_at_decision and Outcome.cluster_id_at_outcome

  "angle_type": "enum",
  "core_belief": "enum",
  "promise_type": "enum",

  "emotion_primary": "enum",
  "emotion_intensity": "enum",

  "message_structure": "enum",
  "opening_type": "enum",

  "state_before": "enum",
  "state_after": "enum",
  "context_frame": "enum",

  "source_type": "enum",
  "risk_level": "enum",
  "horizon": "enum",

  "created_at": "timestamp",
  "schema_version": "string"
}
```

---

## 4. Enum Definitions

### 4.1 angle_type

- `pain`
- `fear`
- `hope`
- `curiosity`
- `authority`
- `social_proof`
- `urgency`
- `identity`

### 4.2 core_belief

- `problem_is_serious`
- `problem_is_hidden`
- `solution_is_simple`
- `solution_is_safe`
- `solution_is_scientific`
- `solution_is_unknown`
- `others_have_this_problem`
- `doctors_are_wrong`
- `time_is_running_out`

### 4.3 promise_type

- `instant`
- `gradual`
- `effortless`
- `hidden`
- `scientific`
- `guaranteed`
- `preventive`

### 4.4 emotion_primary

- `fear`
- `relief`
- `anger`
- `hope`
- `curiosity`
- `shame`
- `trust`

### 4.5 emotion_intensity

- `low`
- `medium`
- `high`

### 4.6 message_structure

- `problem_solution`
- `story_reveal`
- `myth_debunk`
- `authority_proof`
- `question_answer`
- `before_after`
- `confession`

### 4.7 opening_type

- `shock_statement`
- `direct_question`
- `personal_story`
- `authority_claim`
- `visual_pattern_break`

### 4.8 source_type

- `internal`
- `spy`
- `human_override`
- `epistemic_shock`

### 4.9 risk_level

- `low`
- `medium`
- `high`

### 4.10 state_before

- `unsafe`
- `uncertain`
- `powerless`
- `ignorant`
- `overwhelmed`
- `excluded`
- `dissatisfied`

### 4.11 state_after

- `safe`
- `confident`
- `in_control`
- `informed`
- `calm`
- `included`
- `satisfied`

### 4.12 context_frame

- `institutional`
- `anti_authority`
- `peer_based`
- `expert_led`
- `personal_confession`
- `ironic`

### 4.13 horizon

- `T1`
- `T2`
- `T3`

---

## 5. Derived / Advisory Fields

These fields are signals only and must not directly trigger decisions.

```json
{
  "similarity_score": "float (0.0 - 1.0)",
  "novelty_score": "float (0.0 - 1.0)",
  "confidence_weight": "float",

  "similarity_bucket": "enum",
  "novelty_bucket": "enum",
  "confidence_bucket": "enum",

  "tension_type": "enum",
  "fatigue_level": "enum",

  "historical_winrate": "float",
  "historical_failure_rate": "float"
}
```

### similarity_bucket

- `low`
- `medium`
- `high`

### novelty_bucket

- `low`
- `medium`
- `high`

### confidence_bucket

- `weak`
- `normal`
- `strong`

### tension_type

- `cognitive_dissonance`
- `time_pressure`
- `authority_conflict`
- `social_comparison`
- `loss_aversion`
- `none`

### fatigue_level

- `none`
- `skin`
- `message`
- `angle`
- `transition`
- `tension`
- `context`
- `exhausted`

---

## 6. Entity — Hypothesis

### 6.1 Definition

A Hypothesis is a concrete executable realization of an Idea.

Each Hypothesis:
- belongs to exactly one Idea
- can be launched
- produces an Outcome

### 6.2 Hypothesis Schema

```json
{
  "hypothesis_id": "uuid",
  "idea_id": "uuid",

  "variant_type": "enum",
  "mutation_scope": "enum",

  "created_at": "timestamp"
}
```

### variant_type

- `text_variant`
- `structure_variant`
- `delivery_variant`

### mutation_scope

- `copy_only`
- `structure_only`
- `emotion_shift`
- `framing_shift`

---

## 7. Entity — Outcome

### 7.1 Definition

An Outcome represents the factual market response to a Hypothesis.

Outcome is a fact, not an interpretation.

### 7.2 Outcome Schema

```json
{
  "outcome_id": "uuid",
  "hypothesis_id": "uuid",
  "idea_id": "uuid",

  "spend": "float",
  "primary_metric": "float",
  "secondary_metrics": "object",

  "context": {
    "geo": "string",
    "placement": "string",
    "vertical": "string"
  },

  "cluster_id_at_outcome": "uuid",

  "timestamp_start": "timestamp",
  "timestamp_end": "timestamp",

  "horizon": "enum",
  "trusted": "boolean"
}
```

---

## 8. Entity — Decision (Decision Trace)

### 8.1 Definition

A Decision records the deterministic outcome of the Decision Engine.

### 8.2 Decision Schema

```json
{
  "decision_id": "uuid",
  "idea_id": "uuid",

  "decision_type": "enum",
  "decision_reason": "string",

  "passed_checks": "array",
  "failed_checks": "array",
  "failed_check": "string",
  "dominant_constraint": "string",

  "cluster_at_decision": "uuid",
  "horizon": "enum",
  "system_state": "enum",
  "policy_version": "string",
  "timestamp": "timestamp"
}
```

### decision_type

- `APPROVE`
- `REJECT`
- `ALLOW_WITH_CONSTRAINTS`
- `DEFER`

---

## 9. Schema Versioning

- Every entity must include `schema_version`
- Schema changes:
  - must be backward compatible
  - require explicit migration
  - Decision Engine must be schema-version aware

---

## 10. Validation Rules

- All inputs must be validated against schema
- All LLM outputs must be schema-validated
- Invalid schema input must be rejected
- No silent fallback or coercion is allowed

---

## 11. Final Rule

> **Schema is the language of system reasoning.**  
> **Violating schema is a logic error, not an edge case.**

