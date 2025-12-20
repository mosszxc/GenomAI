# LLM Usage Policy
## GenomAI — Large Language Model Governance

**Version:** v1.0  
**Status:** CANONICAL / ENFORCED  
**Applies to:** All usages of LLMs in GenomAI

---

## 1. Purpose

This document defines **where, how, and for what purposes LLMs are allowed** to be used in GenomAI.

The goal of this policy is to:
- prevent LLMs from becoming decision-makers,
- preserve determinism and auditability,
- avoid hidden logic and non-reproducible behavior,
- ensure long-term learning stability.

LLMs are treated as **tools**, not agents.

---

## 2. Core Principle

> **LLMs may assist the system,  
> but must never replace system logic.**

Any use of LLMs that influences decisions directly is forbidden.

---

## 3. Allowed Use Cases (Whitelisted)

LLMs are allowed **only** in the following roles.

---

### 3.1 Decomposition & Classification

**Purpose:**  
Transform video transcript (speech text) into structured data.

**Критическое ограничение:**  
LLM обрабатывает **ТОЛЬКО транскрипт видео** — текст того, что говорит лицо в ролике.  
**НЕ обрабатываются:** визуалы, изображения, primary/description в Facebook Ads, любые другие элементы креатива.

**Allowed actions:**
- classify video transcript strictly into canonical schema fields
- extract values for predefined enums from transcript text only
- normalize transcript text into schema-compliant representation

**Requirements:**
- output must conform exactly to Canonical Schema
- no free-text outside schema
- output must be schema-validated before use

**Notes:**
- LLM output is considered *untrusted* until validated
- validation failure → reject output

---

### 3.2 Hypothesis Generation (Bounded)

**Purpose:**  
Generate executable variants within an **already approved Idea**.

**Allowed actions:**
- generate text variants
- generate structural variants
- generate framing variants

**Hard constraints:**
- Idea must be APPROVED by Decision Engine
- generation must stay within:
  - approved angle
  - approved emotion
  - approved promise
- mutation scope must be explicit

LLM must never decide:
- which Idea to test
- whether Idea should be tested

---

### 3.3 Analytical Summaries (Read-Only)

**Purpose:**  
Produce human-readable summaries for debugging, analysis, or reporting.

**Allowed actions:**
- summarize outcomes
- explain historical patterns
- generate descriptive reports

**Restrictions:**
- summaries have no effect on system logic
- summaries are not inputs to Decision Engine

---

## 4. Explicitly Forbidden Use Cases (Blacklist)

LLMs must **never** be used for:

1. Decision approval or rejection  
2. Risk assessment  
3. Budget allocation  
4. Fatigue or death determination  
5. Learning weight updates  
6. Schema modification  
7. Enum extension  
8. Rule interpretation or bypass  
9. End-to-end optimization on profit  
10. Acting as autonomous agent

Any implementation violating this list is an **architectural defect**.

---

## 5. Output Validation Rules

All LLM outputs must satisfy:

- strict schema validation
- no additional fields
- no missing required fields
- enum values only from canonical lists

Invalid output:
- is rejected
- is logged
- does not affect system state

Silent correction or guessing is forbidden.

---

## 6. Determinism & Reproducibility

LLM usage must be **isolated from decision logic**.

Requirements:
- LLM outputs must not affect deterministic decisions
- system behavior must be reproducible without LLM replay
- Decision Engine behavior must remain identical with or without LLM

---

## 7. Prompt Governance

All prompts must be:

- versioned
- stored in repository
- reviewed like code
- tied to a specific schema version

Prompt changes require:
- version bump
- review
- compatibility check

---

## 8. Failure Handling

If LLM:
- times out
- returns invalid schema
- returns ambiguous output
- returns hallucinated fields

Then:
- output is rejected
- fallback is **no action**, not guessing
- system continues without LLM contribution

**Операционные ограничения:**
- **LLM retries ограничены N попытками** (конкретное значение определяется на этапе реализации)
- **Timeout → no-op, не деградация системы**
- Система не должна зависеть от доступности LLM для критических операций
- Превышение timeout или исчерпание retries не должно блокировать работу системы
- LLM failure не должна приводить к деградации или нестабильности системы

---

## 9. Security & Isolation

- LLMs must not have access to:
  - Decision Engine internals
  - memory mutation endpoints
  - budget controls
- LLM access is read-only where possible

---

## 10. Auditing & Logging

All LLM interactions must be logged:

- input hash
- model version
- prompt version
- timestamp
- validation result

Logs are retained for audit and debugging.

---

## 11. Change Management

Any change to:
- allowed use cases
- forbidden use cases
- validation rules

Requires:
- version increment
- architecture review
- explicit approval

---

## 12. Final Rule

> **LLMs are accelerators, not authorities.**

If an LLM output changes a system decision,  
the architecture is already broken.

