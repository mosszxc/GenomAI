# System Architecture Specification
## GenomAI — Logical System Architecture

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 1  
**Приоритет:** Высокий  
**Основан на:** Architecture Lock, DATA_FLOW, ENTITY_LIFECYCLE, Canonical Schema, Decision Engine

---

## 1. Purpose

Данный документ фиксирует логическую архитектуру системы GenomAI:
- какие компоненты существуют,
- за что каждый компонент отвечает,
- какие взаимодействия разрешены,
- какие взаимодействия запрещены.

Документ:
- не описывает инфраструктуру, технологии, сервисы или деплой,
- не описывает Telegram, UI или API,
- определяет границы ответственности и причинно-следственные связи.

---

## 2. Architectural Principle

**Каждый компонент решает ровно одну логическую задачу и не знает больше, чем ему архитектурно разрешено.**

Ни один компонент:
- не принимает решений вне своей зоны ответственности,
- не модифицирует сущности, которыми не владеет,
- не обходит Decision Engine.

---

## 3. High-Level Component Map

```
External World
   ↓
Ingestion
   ↓
Validation
   ↓
Decomposition
   ↓
Idea Registry
   ↓
Decision Engine
   ↓
Hypothesis Factory
   ↓
External Execution
   ↓
Outcome Ingestion
   ↓
Learning Loop
   ↓
Memory Stores
```

**Компоненты взаимодействуют строго сверху вниз, обратные связи возможны только через Learning Loop.**

---

## 4. Component Responsibilities

### 4.1 Ingestion

**Назначение:**  
Приём внешних данных в систему.

**Отвечает за:**
- приём Creative (транскрипт видео) и Outcome,
- первичную маркировку источника (source_type),
- передачу данных в Validation.

**Не имеет права:**
- интерпретировать данные,
- модифицировать содержимое,
- принимать решения.

**Критическое ограничение:**  
Принимает только транскрипты видео, не визуалы/primary/description.

---

### 4.2 Validation

**Назначение:**  
Проверка соответствия входных данных контрактам.

**Отвечает за:**
- Data Contract validation,
- Canonical Schema validation,
- отклонение невалидных данных.

**Правило:**  
**Невалидные данные не существуют для системы.**

**При отклонении:**
- данные логируются,
- состояние системы не изменяется,
- обучение не происходит.

---

### 4.3 Decomposition (LLM-assisted)

**Назначение:**  
Преобразование сырого транскрипта в структурированное представление.

**Отвечает за:**
- классификацию переменных Canonical Schema,
- извлечение state_before / state_after,
- определение context_frame,
- нормализацию значений enum.

**Ограничения:**
- работает **только с транскриптом видео** (текст того, что говорит лицо в ролике),
- не обрабатывает визуалы, изображения, primary/description,
- не принимает решений,
- не обучается,
- не видит performance,
- результат обязан строго соответствовать Canonical Schema.

**Выход:**  
DecomposedCreative (структурированное представление)

---

### 4.4 Idea Registry

**Назначение:**  
Управление каноническими Idea.

**Отвечает за:**
- создание Idea при успешной decomposition,
- проверку identity (angle_type, core_belief, promise_type, state_transition, context_frame),
- управление `active_cluster_id`,
- предотвращение дубликатов.

**Не имеет права:**
- удалять Idea,
- принимать решения,
- создавать Hypothesis,
- изменять смысл Idea (immutable по смыслу).

**Выход:**  
Idea (каноническая смысловая единица)

---

### 4.5 Decision Engine

**Назначение:**  
Детерминированное принятие решений.

**Отвечает за:**
- approve / reject / defer / allow_with_constraints,
- формирование constraints,
- генерацию Decision Trace (обязательные поля: decision_type, failed_check, dominant_constraint, cluster_at_decision, horizon, system_state, policy_version),
- использование только bucket-значений ML-сигналов (не raw float),
- использование только значений полей (не интерпретаций/объяснений).

**Ключевое правило:**  
**Decision Engine — единственный источник решений.**

**Входы:**
- Idea (schema-valid),
- System State,
- Fatigue Memory,
- Death Memory,
- Discretized ML signals (buckets),
- Risk Budget,
- Horizon context.

**Выход:**  
Decision (факт решения системы)

---

### 4.6 Hypothesis Factory

**Назначение:**  
Создание исполнимых реализаций разрешённых идей.

**Отвечает за:**
- генерацию транскриптов (только текст, не визуалы/primary/description),
- соблюдение mutation_scope (ограничений от Decision Engine),
- создание Hypothesis только после APPROVE / ALLOW_WITH_CONSTRAINTS.

**Ограничения:**
- не изменяет Idea,
- не расширяет scope,
- не знает о performance,
- Hypothesis всегда принадлежит ровно одной Idea.

**Выход:**  
Hypothesis (исполнение разрешённой идеи)

---

### 4.7 External Execution (Boundary)

**Назначение:**  
Факт запуска гипотезы во внешнем мире.

**Важно:**  
**Execution не является частью системы GenomAI.**  
Система фиксирует только факт запуска.

**GenomAI:**
- не управляет закупкой,
- не интерпретирует execution,
- не контролирует запуск.

---

### 4.8 Outcome Ingestion

**Назначение:**  
Приём реакции рынка.

**Отвечает за:**
- создание Outcome при поступлении performance-фактов,
- проверку trust conditions (минимальный spend, временной горизонт),
- фиксацию исторического `cluster_id_at_outcome`.

**Не имеет права:**
- интерпретировать результаты,
- принимать решения,
- изменять performance-данные.

**Входы:**
- spend,
- primary_metric,
- контекст,
- временные границы.

**Выход:**  
Outcome (факт реакции рынка)

---

### 4.9 Learning Loop

**Назначение:**  
Обновление памяти системы.

**Отвечает за:**
- confidence updates (with time decay),
- fatigue updates (skin, message, angle, transition, tension, context),
- death memory,
- cluster priors,
- transition effectiveness (state_before → state_after),
- tension_type effectiveness,
- context_frame compatibility,
- интерпретацию Outcome в контексте environment (environment_context weighting).

**Критическое правило:**  
- Decision Engine **"слеп" к environment** — не читает environment_context напрямую
- Learning Loop **интерпретирует Outcome относительно environment** для корректного весового смещения
- Environment не является основанием для решений, только для корректной интерпретации результатов

**Origin Type & Data Sources:**
- Decision Engine использует **только causal channel** (system outcome, связанный с Hypothesis)
- Learning Loop читает **два источника**:
  - `system` outcome → causal updates (confidence, fatigue, death memory, cluster priors)
  - `user` outcome → observational memory (расширение пространства идей, без causal updates)
- **Decision Engine никогда не использует user outcome для принятия решений**

**Правило:**  
**Learning никогда не меняет прошлые факты.**

**Ограничения:**
- не обновляет стратегические priors (T3) сигналами из T1 (cross-horizon leakage prevention),
- не ретроактивно переписывает историю,
- не изменяет historical cluster_id в Decision/Outcome.

**Триггеры:**
- по завершении горизонта T1 / T2 / T3,
- при смене состояния системы,
- при накоплении достаточного количества Outcome.

---

### 4.10 Memory Stores

**Назначение:**  
Хранение агрегированного опыта системы.

**Типы памяти:**
- Confidence Memory (confidence_weight с time decay)
- Fatigue Memory (fatigue levels по типам)
- Death Memory (мёртвые идеи)
- Cluster Memory (кластерные priors)
- Outcome Memory (агрегированные результаты)

**Доступ:**
- **read** — Decision Engine, Idea Registry, Hypothesis Factory
- **write** — Learning Loop

**Правило:**  
Memory не создаётся напрямую, является агрегатом Outcome + Decision.

---

## 5. Allowed Interactions Matrix

| From → To | Allowed |
|-----------|---------|
| Ingestion → Validation | ✅ |
| Validation → Decomposition | ✅ |
| Decomposition → Idea Registry | ✅ |
| Idea Registry → Decision Engine | ✅ |
| Decision Engine → Hypothesis Factory | ✅ |
| Hypothesis Factory → Execution | ✅ |
| Outcome Ingestion → Learning Loop | ✅ |
| Learning Loop → Memory | ✅ |
| Memory → Decision Engine (read) | ✅ |
| Memory → Idea Registry (read) | ✅ |

**Любая другая связь — архитектурное нарушение.**

---

## 6. Forbidden Interactions

**Запрещено:**
- Decomposition → Decision Engine (LLM не принимает решений)
- Hypothesis Factory → Memory (Hypothesis не знает о performance)
- LLM → Decision (LLM не создаёт Decision)
- Human → Decision Engine (человек не обходит Decision Engine, только через Human Override)
- Outcome → Hypothesis (Outcome не влияет на Hypothesis напрямую)
- Memory → Decomposition (Memory не влияет на decomposition)
- Decision Engine → Memory (Decision Engine не пишет в Memory, только читает)
- Idea Registry → Hypothesis Factory (Hypothesis создаётся только после Decision)

**Любая попытка — архитектурное нарушение.**

---

## 7. Sync / Async Semantics

**Логически синхронно:**
- Ingestion → Validation → Decomposition → Idea Registry → Decision Engine

**Асинхронно:**
- Execution (внешний мир)
- Outcome Ingestion (после завершения горизонта)
- Learning Loop (отложенное обновление)

**Правило:**  
**Система не ожидает Outcome для продолжения работы.**

Decision Engine может принимать новые решения до получения Outcome по предыдущим.

---

## 8. Failure Isolation

**Отказ одного компонента:**
- не должен повреждать другие,
- не должен создавать частичные сущности,
- приводит к безопасному отказу (no-op).

**Fail-safe стратегия:**  
**Лучше не принять решение, чем принять неверное.**

**Примеры:**
- Invalid input → Reject (Validation)
- Invalid schema → Reject (Decomposition)
- Missing memory → Defer (Decision Engine)
- Inconsistent state → Reject (Idea Registry)
- LLM failure → No action (Decomposition)

---

## 9. Evolution Rule

**Изменения допускаются только если:**
- не нарушают Layer 0 (Doctrine),
- не ломают Decision determinism,
- сохраняют ownership сущностей,
- не создают запрещённых взаимодействий.

**Breaking changes требуют:**
- новой версии документа,
- миграционного плана,
- обновления всех зависимых документов.

---

## 10. Final Rule

**Компоненты не думают.**  
**Думает только система в целом.**  
**Решает только Decision Engine.**

---

## 11. Layer Boundary Notice

Этот документ:
- завершает Layer 1 (Logical Architecture),
- является базой для Layer 2 (Product / Interaction),
- не описывает реализацию (Layer 3).
