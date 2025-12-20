# Data Flow Specification
## GenomAI — Canonical Data Flow & Object Lifecycle

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 1  
**Приоритет:** Высокий  
**Основан на:** Layer 0 (Doctrine), Canonical Schema, Data Contracts, Decision Engine

---

## 1. Purpose

Данный документ описывает логический путь данных внутри системы GenomAI:
- как данные входят в систему,
- в каком порядке они обрабатываются,
- где и когда создаются ключевые сущности,
- какие проверки являются обязательными,
- где система принимает решения,
- где начинается и заканчивается обучение.

Документ:
- не описывает UI, Telegram или API,
- не описывает реализацию или инфраструктуру,
- фиксирует причинно-следственную логику системы.

---

## 2. High-Level Flow Overview

Система обрабатывает данные в следующем каноническом порядке:

```
Input
 → Validation
   → Decomposition
     → Idea Registration
       → Decision Engine
         → Hypothesis Generation
           → Execution (external)
             → Outcome Ingestion
               → Temporal Aggregation
                 → Outcome Creation
                   → Learning Loop
```

**Ни один шаг не может быть пропущен или переставлен.**

---

## 3. Input Entry Points

### 3.1 Types of Inputs

Система принимает только следующие типы входов:

1. **Creative Transcript Input** (internal)
   - транскрипт видео-креатива (только текст речи)
   - привязан к hypothesis_id
   - source_type: `creative_internal`

2. **Performance Outcome Input**
   - фактические метрики запуска
   - spend, primary_metric, контекст
   - source_type: `performance`

3. **Spy / External Transcript Input**
   - транскрипт внешнего видео-креатива (только текст речи)
   - наблюдение рынка
   - source_type: `creative_spy`

4. **Human Override Input**
   - редкое вмешательство человека
   - Regime Declaration, Cultural Shift, Strategic Bet, External Constraint
   - source_type: `human_override`

**Любой другой тип входных данных считается архитектурно недопустимым.**

### 3.2 Input Preconditions

Перед входом в систему любые данные считаются **недоверенными**.

**Обязательные условия:**
- вход должен соответствовать Data Contracts,
- тип источника (source_type) должен быть объявлен,
- **нарушение контракта → немедленный REJECT.**

---

## 4. Validation Layer

### 4.1 Contract Validation

Каждый вход:
- валидируется против соответствующего Data Contract,
- проверяется на полноту,
- проверяется на допустимый формат.

**Правило:**  
Если данные не прошли валидацию — они **не существуют для системы**.

### 4.2 Rejection Semantics

При отклонении:
- данные логируются,
- состояние системы не изменяется,
- обучение не происходит.

---

## 5. Decomposition Layer (LLM-Assisted)

**Критическое правило терминологии (явное закрепление):**
- **Creative = raw video transcript (immutable input)** — сырой транскрипт видео, полученный из внешнего источника
- **DecomposedCreative = schema-structured representation (LLM output)** — структурированное представление по Canonical Schema, результат работы Decomposition Layer
- **Никогда не называть DecomposedCreative просто "Creative"**
- Creative — это входной артефакт, а не результат decomposition

### 5.1 Purpose

Decomposition преобразует Creative (raw video transcript — входной артефакт) в DecomposedCreative (schema-structured representation — результат LLM output), соответствующее Canonical Schema.

**Критическое ограничение:**  
LLM обрабатывает **ТОЛЬКО транскрипт видео** — текст того, что говорит лицо в ролике.  
**НЕ обрабатываются:** визуалы, изображения, primary/description в Facebook Ads.

### 5.2 Allowed Operations

- классификация полей Canonical Schema,
- нормализация значений enum,
- извлечение state_before / state_after,
- определение context_frame,
- определение emotion и message structure.

### 5.3 Critical Constraints

- LLM работает только с транскриптом видео,
- результат обязан строго соответствовать Canonical Schema,
- любые свободные тексты → invalid.

### 5.4 Post-Decomposition Validation

Результат decomposition:
- повторно валидируется по Canonical Schema,
- при ошибке → REJECT и логирование.

---

## 6. Idea Registration

### 6.1 Idea Creation

После успешной decomposition создаётся сущность Idea, если:
- комбинация полей ранее не существовала,
- либо существующая Idea требует обновления active_cluster.

### 6.2 Identity Rules

Idea считается одинаковой, если совпадают:
- angle_type
- core_belief
- promise_type
- state_before → state_after
- context_frame

**Различия в тексте не создают новую Idea.**

### 6.3 Cluster Assignment

- Idea получает `active_cluster_id`,
- исторические cluster_id фиксируются в Decision и Outcome,
- `active_cluster_id` может меняться со временем.

---

## 7. Decision Engine Invocation

### 7.1 Invocation Moment

Decision Engine вызывается на каждую новую или обновлённую Idea.

**Decision Engine никогда не вызывается напрямую человеком или LLM.**

### 7.2 Inputs to Decision Engine

- Idea (schema-valid),
- System State,
- Fatigue Memory,
- Death Memory,
- Discretized ML signals (buckets only, not raw float),
- Risk Budget,
- Horizon context.

### 7.3 Outputs

Decision Engine возвращает одно из:
- APPROVE
- REJECT
- DEFER
- ALLOW_WITH_CONSTRAINTS

И формирует **Decision Trace** с обязательными полями:
- decision_type
- failed_check
- dominant_constraint
- cluster_at_decision
- horizon
- system_state
- policy_version

---

## 8. Hypothesis Generation

### 8.1 Preconditions

Hypothesis может быть создана только если:
- Decision Engine вернул APPROVE или ALLOW_WITH_CONSTRAINTS.

### 8.2 Hypothesis Creation Rules

- Hypothesis всегда принадлежит ровно одной Idea,
- Hypothesis — это исполнение, не смысл,
- mutation_scope строго ограничен Decision constraints.

### 8.3 Forbidden Behavior

- Hypothesis не может изменить Idea,
- Hypothesis не может расширить scope,
- Hypothesis не может быть создана вручную.

---

## 9. Execution Boundary (External)

**Execution:**
- происходит вне системы GenomAI,
- система не управляет закупкой,
- система не интерпретирует execution.

GenomAI фиксирует только факт запуска.

---

## 10. Outcome Ingestion

### 10.1 Raw Metrics Collection

Система получает raw performance-факты:
- spend
- primary_metric
- контекст
- временные границы

**Raw metrics не являются Outcome.**

### 10.2 Temporal Aggregation

**Raw metrics агрегируются по временному окну:**
- raw metrics → temporal aggregation → outcome
- Outcome создаётся только после стабилизации метрик во времени
- Outcome интерпретируется только после завершения агрегации

**Правило:**  
Outcome **не равен** мгновенному факту.  
Outcome — это стабилизированная реакция рынка за временное окно.

### 10.3 Outcome Creation

Outcome создаётся после temporal aggregation:
- агрегированные метрики
- временное окно
- контекст

**Outcome — факт, не оценка.**

### 10.4 Trust Assignment

Outcome считается trusted только если:
- достигнут минимальный spend,
- соблюдён временной горизонт,
- нет конфликтов контекста.

### 10.5 Historical Snapshot

Outcome сохраняет:
- `cluster_id_at_outcome` — исторический снимок кластера,
- `idea_id` — связь с Idea,
- `hypothesis_id` — связь с Hypothesis.

---

## 11. Learning Loop

### 11.1 Learning Trigger

Learning запускается:
- по завершении горизонта T1 / T2 / T3,
- при смене состояния системы,
- при накоплении достаточного количества Outcome.

### 11.2 What Gets Updated

- confidence_weight (with time decay),
- fatigue levels (skin, message, angle, transition, tension, context),
- death memory,
- cluster priors,
- transition effectiveness (state_before → state_after),
- tension_type effectiveness,
- context_frame compatibility.

### 11.3 What Never Happens

- обучение на одном Outcome,
- обучение без Decision Trace,
- ретроактивное переписывание истории,
- обновление стратегических priors (T3) сигналами из T1 (cross-horizon leakage prevention).

---

## 12. Failure & Safe Defaults

| Ситуация | Поведение |
|----------|-----------|
| Invalid input | Reject |
| Invalid schema | Reject |
| Missing memory | Defer |
| Inconsistent state | Reject |
| LLM failure | No action |

**Fail-safe стратегия всегда выбирает отказ, а не риск.**

---

## 13. Temporal Guarantees

- Outcome всегда относится к прошлому решению,
- Decision никогда не опирается на будущие Outcome,
- Learning не изменяет прошлые Decision,
- Historical cluster_id фиксируются и не переписываются.

---

## 14. Final Rule

**Ни один объект в системе не может появиться без причины.**  
**Ни одно обучение не может произойти без решения.**  
**Ни одно решение не может быть принято без схемы.**

---

## 15. Layer Boundary Notice

Этот документ:
- завершает Layer 1 (Logical Architecture),
- не описывает Layer 2 (User Flows),
- не описывает Layer 3 (Implementation).
