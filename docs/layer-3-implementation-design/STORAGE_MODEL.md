# Storage Model Specification
## GenomAI — Canonical Storage Model (Layer 3)

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 3  
**Приоритет:** Критический  
**Основан на:** SERVICE_BOUNDARIES, ENTITY_LIFECYCLE, LEARNING_MEMORY_POLICY, MVP_SCOPE

---

## 1. Purpose

Данный документ определяет логическую модель хранения данных в системе GenomAI:
- какие сущности существуют,
- где хранится source of truth,
- какие данные immutable / append-only,
- какие данные derived,
- какие данные **НИКОГДА не используются напрямую для обучения**.

Документ:
- не описывает конкретные БД,
- не описывает индексы и оптимизацию,
- фиксирует онтологию хранения, а не реализацию.

---

## 2. Core Storage Principle

**Система никогда не обучается на "сырых" данных.**  
Обучение возможно только на агрегированных, временнó стабилизированных outcome.

Из этого принципа следует вся модель ниже.

---

## 3. Storage Layers Overview

Хранилище системы разделено на 4 логических слоя:

| Layer | Назначение | Mutable |
|-------|------------|---------|
| L1 | Raw Input | ⚠️ Да |
| L2 | Temporal Snapshots | ❌ Нет |
| L3 | Aggregated Outcomes | ❌ Нет |
| L4 | Learning Memory | ❌ Нет |

---

## 4. Layer 1 — Raw Input Storage

### 4.1 Назначение

Хранение сырых, потенциально шумных данных, поступающих извне.

### 4.2 Содержит

- raw metrics (impressions, clicks, spend, conversions)
- данные могут обновляться
- возможны задержки, коррекции, расхождения

### 4.3 Правила

- ❌ **НЕ используется для learning**
- ❌ **НЕ используется для decision**
- ✅ используется только для построения snapshot'ов

### 4.4 Mutable

✅ **Да** (разрешены перезаписи)

---

## 5. Layer 2 — Temporal Snapshot Storage (Daily Scan)

### 5.1 Назначение

Фиксация состояния креатива за дискретный период времени (1 день).  
Это основной механизм "динамики".

### 5.2 DailyMetricsSnapshot

**Единица хранения:**
- `creative_id + date`

**Содержит:**
- `spend_delta_day`
- `impressions_delta_day`
- `clicks_delta_day`
- `conversions_delta_day`
- derived daily metrics (`CPA_day`, `CTR_day`)

**Правила:**
- append-only
- immutable после создания
- ровно один snapshot на день
- отсутствие snapshot = отсутствие данных, не ошибка

**Mutable:**  
❌ **Нет**

### 5.3 Snapshot Guarantees

- snapshot — это факт, а не оценка
- snapshot не интерпретируется
- snapshot не триггерит learning

---

## 6. Layer 3 — Aggregated Outcome Storage

### 6.1 Назначение

Хранение агрегированных окон, которые считаются Outcome в системе.  
👉 **Это единственный вход в Learning Loop.**

### 6.2 OutcomeWindow

**Единица хранения:**
- `creative_id + window_definition`

**Примеры окон:**
- D1–D3
- D1–D7
- D3–D7

### 6.3 OutcomeAggregate

**Содержит:**
- aggregated spend
- aggregated conversions
- `CPA_window`
- trend (up / down / flat)
- slope
- volatility
- saturation signal
- `environment_context` (account_state, platform_state)
- `origin_type` (system | user)
- `decision_id` (nullable, обязателен для `origin_type = system`)

**Правила:**
- immutable
- создаётся только после закрытия окна
- не пересчитывается
- может существовать несколько окон на один creative
- **Критическое правило зависимости:**
  - `origin_type = system` → требует `decision_id` (не nullable)
  - `origin_type = user` → `decision_id` nullable (может быть NULL)

### 6.4 Outcome Semantics

**Outcome:**
- ❌ не равен raw metrics
- ❌ не равен daily snapshot
- ✅ равен стабилизированной динамике

---

## 7. Layer 4 — Learning Memory Storage

### 7.1 Назначение

Хранение обновляемых знаний системы, влияющих на будущие решения.

### 7.2 Memory Entities

- `IdeaConfidence`
- `FatigueState`
- `ClusterStats`
- `PriorDistributions`
- `HistoricalDecisionTraces`

**Правила:**
- append-only (versioned)
- прошлые значения не удаляются
- новое состояние всегда версия

### 7.3 Learning Constraint (Critical)

**Learning Memory может обновляться ТОЛЬКО на основе OutcomeAggregate с `origin_type = system`.**

**System outcomes (`origin_type = system`):**
- требуют `decision_id` (не nullable)
- используются для causal updates (confidence, fatigue, death memory)
- обновляют Learning Memory

**User outcomes (`origin_type = user`):**
- `decision_id` nullable (может быть NULL)
- хранятся отдельно
- используются только для observational memory (discovery, similarity signals)
- **НЕ обновляют** Learning Memory (confidence, fatigue, death memory, cluster priors)

---

## 8. Forbidden Storage Patterns

**Запрещено:**
- Learning на raw metrics
- Learning на daily snapshots
- Decision Engine чтение Raw / Snapshot layers
- Перезапись OutcomeAggregate
- Удаление исторических learning-версий

---

## 9. Storage Ownership Map

| Entity | Owner Service |
|--------|---------------|
| Raw Metrics | Outcome Ingestion |
| Daily Snapshot | Metrics Scanner |
| OutcomeAggregate | Aggregation Engine |
| Learning Memory | Learning Loop |
| Idea | Idea Registry |

---

## 10. Evolution Rule

Любое добавление нового слоя хранения:
- должно быть явно отнесено к одному из 4 уровней
- не может нарушать правило: **learning ≠ raw data**

---

## 11. Final Rule (жёсткое)

**Если данные можно изменить — на них нельзя обучаться.**

---

## 12. Layer Boundary Notice

Этот документ:
- завершает Storage-часть Layer 3,
- не описывает конкретные БД или технологии,
- не описывает индексы и оптимизацию.
