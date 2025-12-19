# Data Contracts Specification
## GenomAI — Input & Data Integrity Contracts

**Version:** v1.0  
**Status:** CANONICAL / ENFORCED  
**Applies to:** All data entering GenomAI

---

## 1. Purpose

This document defines **data contracts** for all inputs consumed by GenomAI.

A data contract specifies:
- what data is allowed to enter the system
- in what format
- with which guarantees
- and how invalid data is handled

**Any data that violates its contract must be rejected.**

Silent correction, guessing, or coercion is forbidden.

---

## 2. Core Principles

1. No implicit data assumptions
2. No silent fallbacks
3. No schema drift
4. All inputs are hostile until validated
5. Contracts override convenience
6. Invalid data is worse than no data

---

## 3. Input Source Classification

All inputs must declare a `source_type`.

### source_type enum

```text
performance
creative_internal
creative_spy
llm_output
human_override
system_internal
```

Each source type has its own contract.

---

## 4. Contract: Performance Data

### 4.1 Description

Performance data represents market feedback from executed hypotheses.

This data is treated as:
- high importance
- potentially noisy
- never authoritative without context

### 4.2 Required Fields

```json
{
  "hypothesis_id": "uuid",
  "idea_id": "uuid",

  "spend": "float >= 0",
  "primary_metric": "float",
  "secondary_metrics": "object",

  "geo": "string",
  "placement": "string",
  "vertical": "string",

  "timestamp_start": "timestamp",
  "timestamp_end": "timestamp"
}
```

### 4.3 Validation Rules

- `spend` must be >= 0
- `timestamp_end > timestamp_start`
- `hypothesis_id` must exist
- `idea_id` must exist
- Missing metrics → invalid
- Negative or NaN values → invalid

### 4.4 Trust Rules

Performance data:
- is not trusted by default
- becomes trusted only after:
  - minimum spend threshold
  - minimum runtime
  - horizon alignment

---

## 5. Contract: Internal Creative Input

### 5.1 Description

Internal creatives originate from:
- in-house production
- approved hypothesis factory output

### 5.2 Required Fields

```json
{
  "creative_id": "uuid",
  "hypothesis_id": "uuid",

  "raw_content": "string",
  "format": "enum",

  "created_at": "timestamp"
}
```

### 5.3 Validation Rules

- `hypothesis_id` must be approved by Decision Engine
- `raw_content` must be non-empty
- `format` must be declared
- orphan creatives are forbidden

---

## 6. Contract: Spy / External Creative Data

### 6.1 Description

Spy data represents external market observations.

This data:
- is incomplete by nature
- may be misleading
- must never be treated as truth

### 6.2 Required Fields

```json
{
  "external_id": "string",
  "raw_content": "string",

  "geo": "string",
  "placement": "string",

  "observed_at": "timestamp"
}
```

### 6.3 Validation Rules

- No inferred performance allowed
- No assumed success
- No missing `raw_content`
- Context fields mandatory

### 6.4 Usage Restrictions

Spy data:
- may seed ideas
- may trigger exploration
- must never:
  - mark ideas as winners
  - override death memory
  - influence confidence weights directly

---

## 7. Contract: LLM Output

### 7.1 Description

LLM outputs are used for:
- decomposition
- classification
- generation of hypothesis variants

LLM output is always untrusted until validated.

### 7.2 Required Fields

```json
{
  "schema_version": "string",
  "classified_fields": "object"
}
```

### 7.3 Validation Rules

- Output must strictly conform to canonical schema
- Unknown fields → invalid
- Missing required fields → invalid
- Free-text outside schema → invalid

### 7.4 Forbidden Usage

LLM output must never:
- approve or reject ideas
- bypass Decision Engine
- modify schema
- inject new enums

---

## 8. Contract: Human Override Input

### 8.1 Description

Human overrides represent explicit interrupts, not regular data.

### 8.2 Required Fields

```json
{
  "override_type": "enum",
  "reason": "string",
  "issued_by": "string",
  "timestamp": "timestamp"
}
```

### override_type

- `regime_declaration`
- `cultural_shift`
- `strategic_bet`
- `external_constraint`

### 8.3 Validation Rules

- Override must be explicit
- Reason is mandatory
- Overrides are logged permanently
- Overrides never delete historical data

---

## 9. Contract: System Internal Signals

### 9.1 Description

Signals produced by ML or analytics subsystems.

These are advisory only.

### 9.2 Required Fields

```json
{
  "signal_type": "enum",
  "value": "float",
  "confidence": "float",
  "generated_at": "timestamp"
}
```

### 9.3 Usage Restrictions

- Signals must not directly trigger decisions
- Signals must pass through Decision Engine logic
- Signals may decay over time

---

## 10. Rejection Policy

Any input is rejected if:
- schema validation fails
- required fields are missing
- `source_type` is unknown
- timestamps are inconsistent
- values are NaN or invalid

Rejected data:
- is logged
- does not affect learning
- does not affect memory

---

## 11. Change Management

Any contract change requires:
- version bump
- migration strategy
- backward compatibility review

Contract drift is considered a critical bug.

---

## 12. Final Rule

> **Data contracts are the immune system of GenomAI.**  
> **If data is allowed to drift,  
> the system will learn lies.**

