# Entity Lifecycle Specification
## GenomAI — Canonical Entity Lifecycle & Ownership Model

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 1  
**Приоритет:** Высокий  
**Основан на:** Domain Model, Canonical Schema, DATA_FLOW, Decision Engine

---

## 1. Purpose

Данный документ определяет жизненный цикл, владение и правила изменения всех ключевых сущностей системы GenomAI.

**Цель документа:**
- зафиксировать кто имеет право создавать, изменять и закрывать сущности,
- предотвратить неявные побочные эффекты,
- обеспечить причинно-следственную целостность системы.

Документ:
- не описывает UI, Telegram, API или хранение,
- не описывает ML или LLM реализацию,
- фиксирует архитектурные законы существования объектов.

---

## 2. Core Principle

**Ни одна сущность не может быть создана, изменена или уничтожена без чёткого архитектурного основания.**

Каждая сущность:
- имеет единственный источник создания,
- имеет строго ограниченные допустимые переходы состояния,
- не может быть изменена произвольно человеком или LLM.

---

## 3. Entity Overview

Система оперирует следующими сущностями Layer 1:

| Entity | Назначение |
|--------|------------|
| Creative | Raw transcript (immutable) — сырой транскрипт видео |
| DecomposedCreative | Schema-structured representation — структурированное представление по Canonical Schema |
| Idea | Каноническая смысловая единица |
| Hypothesis | Исполнение разрешённой идеи |
| Decision | Факт решения системы |
| Outcome | Факт реакции рынка |
| Cluster | Контекстная группировка идей |
| Memory | Агрегированное состояние обучения |

---

## 4. Creative

**Критическое правило терминологии (явное закрепление):**
- **Creative = raw video transcript (immutable input)** — сырой транскрипт видео, полученный из внешнего источника
- **DecomposedCreative = schema-structured representation (LLM output)** — структурированное представление по Canonical Schema, результат работы Decomposition Layer
- **Никогда не называть DecomposedCreative просто "Creative"**
- Creative — это входной артефакт, а не результат decomposition

### 4.1 Creation

- **Источник:** внешний мир (media buyer / spy)
- **Способ создания:** ingestion
- **Критическое ограничение:** Creative содержит **ТОЛЬКО транскрипт видео** (текст того, что говорит лицо в ролике)
- Creative никогда не создаётся внутри системы

### 4.2 Mutability

- Creative является **immutable**
- Оригинальный текст не изменяется
- Метаданные (source_type, timestamp) фиксируются при создании

### 4.3 Termination

- Creative **не удаляется**
- Может быть помечен как `invalid` (soft-reject)
- Invalid Creative не используется для decomposition

---

## 5. DecomposedCreative

**Критическое правило терминологии (явное закрепление):**
- **Creative = raw video transcript (immutable input)** — сырой транскрипт видео, полученный из внешнего источника
- **DecomposedCreative = schema-structured representation (LLM output)** — структурированное представление по Canonical Schema, результат работы Decomposition Layer
- **Никогда не называть DecomposedCreative просто "Creative"**
- DecomposedCreative — это результат decomposition, а не входной артефакт

### 5.1 Creation

- Создаётся только **Decomposition Layer** (LLM-assisted)
- Основан строго на одном Creative (raw transcript)
- **Критическое ограничение:** LLM обрабатывает только транскрипт, не визуалы/primary/description

### 5.2 Mutability

- Может быть пересобран при обновлении схемы
- Версионируется (schema_version)
- При пересборе старая версия архивируется

### 5.3 Termination

- Устаревшие версии архивируются
- Никогда не используются для обучения
- Актуальная версия используется для Idea Registration

---

## 6. Idea

### 6.1 Creation

- Создаётся системой при успешной decomposition
- Человек и LLM **не могут** создавать Idea напрямую
- Создание происходит в Idea Registration Layer

### 6.2 Identity

Idea идентифицируется комбинацией:
- `angle_type`
- `core_belief`
- `promise_type`
- `state_before → state_after` (state_transition)
- `context_frame`

**Текст не участвует в identity.**

### 6.3 Mutability

- Idea **immutable по смыслу**
- Допустимы:
  - смена `active_cluster_id` (при перекластеризации)
  - обновление derived signals (novelty_bucket, similarity_bucket, confidence_bucket)
  - обновление fatigue levels

### 6.4 Termination

- Idea **не удаляется**
- Может быть помечена как `dead` (через Death Memory)
- **Dead ≠ deleted** — мёртвая Idea остаётся в системе для обучения
- Dead Idea исключается из генерации новых Hypothesis

---

## 7. Hypothesis

### 7.1 Creation

- Создаётся только после **APPROVE / ALLOW_WITH_CONSTRAINTS** от Decision Engine
- Всегда связана с одной Idea
- Создаётся Hypothesis Factory
- **Критическое ограничение:** Hypothesis содержит транскрипт, не визуалы/primary/description

### 7.2 Mutability

- Hypothesis **immutable**
- Нельзя:
  - менять Idea
  - расширять scope
  - изменять mutation_scope после создания

### 7.3 Termination

- Закрывается при завершении горизонта (T1/T2/T3)
- Может иметь несколько Outcome (при повторных запусках)
- Закрытая Hypothesis не генерирует новые транскрипты

---

## 8. Decision

### 8.1 Creation

- Создаётся только **Decision Engine**
- Один Decision → одна Idea → один момент времени
- Decision Engine — единственный источник создания Decision

### 8.2 Mutability

- Decision **immutable**
- Trace immutable
- Decision trace содержит обязательные поля:
  - `decision_type`
  - `failed_check`
  - `dominant_constraint`
  - `cluster_at_decision` (исторический снимок)
  - `horizon`
  - `system_state`
  - `policy_version`

### 8.3 Termination

- **Не удаляется**
- Используется для аудита и обучения
- Decision всегда сохраняется для причинно-следственного анализа

---

## 9. Outcome

### 9.1 Creation

- Создаётся при поступлении **performance-фактов**
- Создаётся в Outcome Ingestion Layer
- **Outcome — факт, не оценка**

**Важно:**  
Outcome **агрегирован по временному окну** и не равен raw metrics.  
Outcome интерпретируется только после стабилизации во времени (temporal aggregation).

### 9.1.1 System Outcome

- **Требует Decision:** System Outcome не может существовать без Decision
- **Требует Hypothesis:** System Outcome всегда связан с Hypothesis
- **Origin Type:** `origin_type = system`
- **Использование:** используется для causal updates (обновление confidence, fatigue, death memory)

### 9.1.2 User Outcome

- **Не требует Decision:** User Outcome может существовать без Decision
- **Не требует Hypothesis:** User Outcome не связан с Hypothesis
- **Origin Type:** `origin_type = user`
- **Использование:** используется только для observational memory (расширение пространства идей, обновление similarity signals)

### 9.2 Mutability

- Outcome **immutable**
- Допустима корректировка только метаданных валидации (trust_state)
- Performance-данные (spend, primary_metric) не изменяются

### 9.3 Trust States

- `untrusted` — недостаточно данных для доверия
- `trusted` — достигнут минимальный spend, соблюдён горизонт
- `ignored` — явно помечен как невалидный

### 9.4 Origin Type

**Outcome имеет атрибут `origin_type`:**

- `system` — результат собственного решения системы (требует Decision + Hypothesis)
- `user` — внешний креатив медиабайера (не требует Decision, не связан с Hypothesis)

**Критическое различие:**

**System Outcome (`origin_type = system`):**
- Требует Decision (не может существовать без Decision)
- Требует Hypothesis (всегда связан с Hypothesis)
- Используется для causal updates (обновление confidence, fatigue, death memory)
- Decision Engine использует только system outcome (causal channel)

**User Outcome (`origin_type = user`):**
- Не требует Decision (может существовать без Decision)
- Не требует Hypothesis (не связан с Hypothesis)
- Используется только для observational memory (расширение пространства идей, обновление similarity signals)
- **НЕ обновляет** confidence, fatigue, death memory, cluster priors
- **НЕ используется** Decision Engine для принятия решений

### 9.5 Historical Snapshot

- Outcome сохраняет:
  - `cluster_id_at_outcome` — исторический снимок кластера
  - `idea_id` — связь с Idea
  - `hypothesis_id` — связь с Hypothesis

### 9.6 Environment Context (Metadata)

**Outcome может содержать опциональные метаданные о среде исполнения:**

- `environment_context` (опционально):
  - `account_state`: unknown | stable | degraded
  - `platform_state`: normal | volatile
  - `auction_pressure`: low | normal | high

**Важно:**
- Это **metadata**, не обязательные поля
- Outcome **валиден без environment_context**
- Environment context используется только Learning Loop для корректной интерпретации Outcome
- Decision Engine **не читает environment_context** напрямую

---

## 10. Cluster

### 10.1 Creation

- Создаётся системой (ML / rule-based)
- Человек **не управляет** кластерами напрямую
- Кластеризация происходит на основе similarity signals

### 10.2 Mutability

- Состав кластера может меняться
- История membership сохраняется
- `active_cluster_id` в Idea может обновляться
- Исторические `cluster_at_decision` и `cluster_id_at_outcome` не изменяются

### 10.3 Termination

- Кластер может быть закрыт (при выгорании или смерти всех идей)
- Идеи сохраняют historical cluster_id
- Закрытый кластер не используется для новых идей

---

## 11. Memory

**Критическое уточнение:**  
Memory не является первичной сущностью хранения.  
Memory — это агрегированное производное состояние (derived state), формируемое Learning Loop на основе Outcome и Decision.

### 11.1 Creation

- Memory **не создаётся напрямую**
- Является агрегатом Outcome + Decision
- Создаётся и обновляется Learning Loop

### 11.2 Mutability

- Обновляется только **Learning Loop**
- Применяется time decay
- Типы памяти:
  - Outcome Memory
  - Decision Memory
  - Death Memory
  - Fatigue Memory
  - Confidence Memory

### 11.3 Termination

- Memory **не удаляется**
- Может обнуляться только через reset regime (Human Override)
- Time decay уменьшает вес, но не удаляет факты

---

## 12. Ownership Matrix

| Entity | Owner |
|--------|-------|
| Creative | External (Media Buyer / Spy) |
| DecomposedCreative | System (Decomposition Layer) |
| Idea | System (Idea Registration) |
| Hypothesis | System (Hypothesis Factory) |
| Decision | Decision Engine |
| Outcome | Market (через Outcome Ingestion) |
| Cluster | System (ML / Clustering) |
| Memory | Learning Loop |

---

## 13. Forbidden Operations

**Запрещено:**
- ручное создание Idea
- редактирование Hypothesis
- удаление Decision
- подмена Outcome
- правка Memory человеком
- изменение Decision Trace
- ретроактивное изменение cluster_id в Decision/Outcome

**Любая попытка — архитектурное нарушение.**

---

## 14. Cross-Entity Guarantees

- System Outcome всегда ссылается на Decision и Hypothesis
- User Outcome не требует Decision и не связан с Hypothesis
- Decision всегда предшествует System Outcome
- Hypothesis всегда ссылается на Idea
- Memory никогда не изменяет прошлые факты
- Historical cluster_id фиксируются и не переписываются
- Decision trace immutable после создания

---

## 15. Final Rule

**Сущности отражают реальность системы, а не желания человека.**  
**Система не переписывает историю.**

---

## 16. Layer Boundary Notice

Этот документ:
- завершает Entity-часть Layer 1,
- не описывает Layer 2 (User Flow),
- не описывает Layer 3 (Implementation).
